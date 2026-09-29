"""Offline audit of the supplied export; no network or production changes.

Run from the repository root with python -m local_validation.validate_weekly_history.
Timezone is explicit; raw local dates provide an independent grouping oracle.
"""

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from src.analytics.weekly_analysis import weekly_analysis_from_activities
from src.strava.activity_mapper import activity_from_strava


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--timezone", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error("Output must not overwrite source")
    source_bytes = args.source.read_bytes()
    raw = json.loads(source_bytes, parse_float=Decimal)
    records = json.loads(source_bytes)["activities"]
    tz = ZoneInfo(args.timezone)
    activities = [activity_from_strava(record) for record in records]
    groups = defaultdict(list)
    local_mismatches = []
    excluded = []
    for record in raw["activities"]:
        # Strava's local field encodes wall time even when suffixed with Z.
        local = datetime.fromisoformat(record["start_date_local"]).replace(tzinfo=None)
        utc = datetime.fromisoformat(record["start_date"])
        if utc.astimezone(tz).replace(tzinfo=None) != local:
            local_mismatches.append(record["id"])
        if record["sport_type"] != "Run":
            excluded.append(record["id"])
            continue
        iso = local.date().isocalendar()
        monday = date.fromisocalendar(iso.year, iso.week, 1)
        groups[monday].append(record)

    metadata_tz = ZoneInfo(raw["date_range"]["timezone"])
    coverage_start = datetime.combine(date.fromisoformat(raw["date_range"]["start"]), time.min, metadata_tz)
    # Conservatively use the start of the declared end date, bounded by export time.
    coverage_end = min(
        datetime.combine(date.fromisoformat(raw["date_range"]["end"]), time.min, metadata_tz),
        datetime.fromisoformat(raw["exported_at"]),
    )
    start_local = coverage_start.astimezone(tz).date()
    iso = start_local.isocalendar()
    monday = date.fromisocalendar(iso.year, iso.week, 1)
    rows = []
    failures = []
    while datetime.combine(monday, time.min, tz) < coverage_end:
        next_monday = monday + timedelta(days=7)
        complete = (datetime.combine(monday, time.min, tz) >= coverage_start
                    and datetime.combine(next_monday, time.min, tz) <= coverage_end)
        reference = datetime.combine(monday + timedelta(days=3), time(hour=12), tz)
        result = weekly_analysis_from_activities(
            activities, reference_datetime=reference, athlete_timezone=tz,
        )
        members = groups[monday]
        expected_distance = sum((Decimal(str(r["distance"])) for r in members), Decimal(0))
        error = abs(Decimal(str(result.running_distance_meters)) - expected_distance)
        # Decimal source total vs float production sum: tolerate float representation only.
        passed = (result.week_start_date == monday
                  and result.running_activity_count == len(members)
                  and error <= Decimal("0.000001"))
        if not passed:
            failures.append(monday.isoformat())
        rows.append({
            "week_start_date": result.week_start_date.isoformat(),
            "week_end_date": (next_monday - timedelta(days=1)).isoformat(),
            "complete_calendar_week_in_declared_export": complete,
            "running_distance_meters": result.running_distance_meters,
            "running_activity_count": result.running_activity_count,
            "expected_distance_meters": str(expected_distance),
            "distance_error_meters": str(error), "passed": passed,
            "source_ledger": [{"id": r["id"], "start_date": r["start_date"],
                               "start_date_local": r["start_date_local"],
                               "distance_meters": str(r["distance"])} for r in members],
        })
        monday = next_monday

    ids = Counter(r["id"] for r in records)
    candidate_duplicates = []
    ordered = sorted(records, key=lambda r: r["start_date"])
    for first, second in zip(ordered, ordered[1:]):
        seconds = (datetime.fromisoformat(second["start_date"])
                   - datetime.fromisoformat(first["start_date"])).total_seconds()
        if seconds <= 60 and first["distance"] == second["distance"]:
            candidate_duplicates.append({"ids": [first["id"], second["id"]],
                                         "start_gap_seconds": seconds,
                                         "distance_meters_each": first["distance"]})
    assigned_ids = [r["id"] for row in rows for r in row["source_ledger"]]
    expected_ids = [r["id"] for r in records if r["sport_type"] == "Run"]
    partition_matches = Counter(assigned_ids) == Counter(expected_ids)
    report = {
        "source": str(args.source), "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "athlete_timezone_assumed": args.timezone,
        "source_metadata": {k: v for k, v in raw.items() if k != "activities"},
        "actual_utc_range": [ordered[0]["start_date"], ordered[-1]["start_date"]],
        "mapped_activity_count": len(activities), "excluded_activity_ids": excluded,
        "local_time_mismatches": local_mismatches,
        "repeated_ids": [key for key, count in ids.items() if count > 1],
        "candidate_duplicate_uploads": candidate_duplicates,
        "zero_distance_ids": [r["id"] for r in records if r["distance"] == 0],
        "source_partition_matches": partition_matches,
        "weekly_failures": failures, "weeks": rows,
    }
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("Week | Complete | km | Activities | Independent check")
    for row in rows:
        print(f"{row['week_start_date']} | {row['complete_calendar_week_in_declared_export']} | "
              f"{row['running_distance_meters'] / 1000:.4f} | "
              f"{row['running_activity_count']} | {row['passed']}")
    print(json.dumps({k: v for k, v in report.items() if k != "weeks"}, indent=2))
    if failures or local_mismatches or not partition_matches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
