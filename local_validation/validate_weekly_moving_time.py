"""Offline moving-time audit of an existing normalized Strava snapshot.

Run with python -m local_validation.validate_weekly_moving_time SNAPSHOT.
No network access or writes to the snapshot. JSON results go to stdout.
"""

import argparse
from collections import defaultdict
from datetime import date, datetime, time, timedelta
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from src.analytics.weekly_analysis import weekly_analysis_from_activities
from src.models.activity import Activity


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    source_bytes = args.source.read_bytes()
    snapshot = json.loads(source_bytes)
    tz = ZoneInfo(snapshot["timezone"])
    start = datetime.fromisoformat(snapshot["start_inclusive"])
    end = datetime.fromisoformat(snapshot["end_exclusive"])
    extracted = datetime.fromisoformat(snapshot["extraction_finished_at"])
    records = snapshot["activities"]
    activities = [
        Activity(**{**record, "start_date": datetime.fromisoformat(record["start_date"])})
        for record in records
    ]

    # Independent oracle: group source records by local ISO calendar week,
    # without using analytics boundaries, selectors or aggregation functions.
    groups = defaultdict(list)
    for record in records:
        if record["sport_type"] == "Run":
            local = datetime.fromisoformat(record["start_date"]).astimezone(tz)
            iso = local.date().isocalendar()
            groups[date.fromisocalendar(iso.year, iso.week, 1)].append(record)

    rows = []
    monday = start.astimezone(tz).date()
    monday -= timedelta(days=monday.weekday())
    while datetime.combine(monday, time.min, tz) < end:
        expected = sum(record["moving_time_seconds"] for record in groups[monday])
        result = weekly_analysis_from_activities(
            activities,
            reference_datetime=datetime.combine(monday, time.min, tz),
            athlete_timezone=tz,
        )
        rows.append({
            "week_start_date": monday.isoformat(),
            "running_activity_count": len(groups[monday]),
            "actual_seconds": result.running_moving_time_seconds,
            "expected_seconds": expected,
            "period_closed_at_extraction": datetime.combine(monday + timedelta(days=7), time.min, tz) <= extracted,
            "passed": result.week_start_date == monday
            and result.running_activity_count == len(groups[monday])
            and type(result.running_moving_time_seconds) is int
            and result.running_moving_time_seconds == expected,
        })
        monday += timedelta(days=7)

    source_total = sum(r["moving_time_seconds"] for r in records if r["sport_type"] == "Run")
    weekly_total = sum(row["actual_seconds"] for row in rows)
    unchanged = args.source.read_bytes() == source_bytes
    passed = unchanged and all(row["passed"] for row in rows) and weekly_total == source_total
    print(json.dumps({
        "source": str(args.source),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_unchanged": unchanged,
        "timezone": snapshot["timezone"],
        "activity_count": len(records),
        "run_count": sum(len(group) for group in groups.values()),
        "source_total_seconds": source_total,
        "weekly_total_seconds": weekly_total,
        "passed": passed,
        "weeks": rows,
    }, indent=2))
    if not passed:
        raise SystemExit("Offline moving-time verification failed.")


if __name__ == "__main__":
    main()
