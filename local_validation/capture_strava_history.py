"""Manual snapshot and reconciliation; uses only the existing public client.

Run as python -m local_validation.capture_strava_history --help.
No details, laps, streams, credentials or automatic duplicate removal.
"""

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from src.analytics.weekly_analysis import weekly_analysis_from_activities
from src.models.activity import Activity
from src.strava.client import StravaClient


def retrieve(client, start, end, per_page):
    activities, pages = [], []
    page = 1
    previous_batches = set()
    while True:
        try:
            batch = client.get_activities(
                after=int(start.timestamp()) - 1, before=int(end.timestamp()),
                page=page, per_page=per_page,
            )
        except RuntimeError:
            raise RuntimeError(f"Activity page {page} failed; no complete snapshot saved.") from None
        pages.append({"page": page, "returned_count": len(batch)})
        if not batch:
            return activities, pages
        signature = tuple(batch)
        if signature in previous_batches:
            raise RuntimeError("Repeated page detected; pagination completion unverified.")
        previous_batches.add(signature)
        activities.extend(batch)
        page += 1


def record(activity):
    result = asdict(activity)
    result["start_date"] = activity.start_date.isoformat()
    return result


def meters(records):
    return sum((Decimal(str(r["distance_meters"])) for r in records), Decimal(0))


def reconcile(records, old):
    """Group by ID without collapsing repeated records or losing multiplicity."""
    before, after = defaultdict(list), defaultdict(list)
    for r in old:
        before[r["id"]].append(r)
    for r in records:
        after[r["id"]].append(r)
    differences = []
    for activity_id in sorted(before.keys() | after.keys()):
        a, b = before[activity_id], after[activity_id]
        if a != b:
            differences.append({
                "id": activity_id, "status": "added" if not a else "removed" if not b else "changed",
                "old": a, "new": b, "distance_delta_meters": str(meters(b) - meters(a)),
            })
    return differences


def analyze(records, start, end, extracted_at, tz):
    activities = [Activity(**{**r, "start_date": datetime.fromisoformat(r["start_date"])}) for r in records]
    runs = [r for r in records if r["sport_type"] == "Run"]
    groups = defaultdict(list)
    for r in runs:
        local = datetime.fromisoformat(r["start_date"]).astimezone(tz)
        iso = local.isocalendar()
        groups[date.fromisocalendar(iso.year, iso.week, 1)].append(r)
    monday = start.date() - timedelta(days=start.weekday())
    weeks = []
    while datetime.combine(monday, time.min, tz) < end:
        next_start = datetime.combine(monday + timedelta(days=7), time.min, tz)
        result = weekly_analysis_from_activities(
            activities, reference_datetime=datetime.combine(monday, time(hour=12), tz), athlete_timezone=tz,
        )
        expected = groups[monday]
        error = abs(Decimal(str(result.running_distance_meters)) - meters(expected))
        weeks.append({
            "week_start_date": result.week_start_date.isoformat(),
            "running_distance_meters": result.running_distance_meters,
            "running_activity_count": result.running_activity_count,
            "independent_distance_meters": str(meters(expected)),
            "source_ids": [r["id"] for r in expected],
            "period_closed_at_extraction": next_start <= extracted_at,
            "passed": result.week_start_date == monday and result.running_activity_count == len(expected) and error <= Decimal("0.000001"),
        })
        monday += timedelta(days=7)
    return weeks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end-exclusive", required=True, type=date.fromisoformat)
    parser.add_argument("--timezone", required=True)
    parser.add_argument("--per-page", type=int, default=30)
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strava-display-km", type=Decimal, required=True)
    args = parser.parse_args()
    tz = ZoneInfo(args.timezone)
    start = datetime.combine(args.start, time.min, tz)
    end = datetime.combine(args.end_exclusive, time.min, tz)
    if start >= end or not 1 <= args.per_page <= 200:
        parser.error("Require start < end and per-page between 1 and 200")
    if start.weekday() != 0 or end.weekday() != 0:
        parser.error("This weekly comparison requires Monday boundaries")
    if args.output.exists():
        parser.error("Output already exists; choose a new snapshot path")
    old_bytes = args.previous.read_bytes()
    old_data = json.loads(old_bytes)
    old = [{"id": r["id"], "name": r["name"], "sport_type": r["sport_type"],
            "start_date": datetime.fromisoformat(r["start_date"]).isoformat(),
            "distance_meters": r["distance"], "moving_time_seconds": r["moving_time"]}
           for r in old_data["activities"]]
    started = datetime.now(timezone.utc)
    try:
        client = StravaClient()
    except RuntimeError:
        raise SystemExit("Strava authentication failed; check local configuration. No snapshot saved.") from None
    try:
        downloaded, pages = retrieve(client, start, end, args.per_page)
    except RuntimeError as error:
        raise SystemExit(str(error)) from None
    finished = datetime.now(timezone.utc)
    kept = [a for a in downloaded if start <= a.start_date < end]
    records = [record(a) for a in kept]
    runs = [r for r in records if r["sport_type"] == "Run"]
    old_runs = [r for r in old if r["sport_type"] == "Run"]
    weeks = analyze(records, start, end, finished, tz)
    sports = sorted({r["sport_type"] for r in records})
    differences = reconcile(runs, old_runs)
    total = meters(runs)
    delta = total - meters(old_runs)
    ids = Counter(r["id"] for r in records)
    report = {
        "extraction_started_at": started.isoformat(), "extraction_finished_at": finished.isoformat(),
        "timezone": args.timezone, "start_inclusive": start.isoformat(), "end_exclusive": end.isoformat(),
        "period_still_open": finished < end, "pagination_completed": True,
        "pages": pages, "per_page": args.per_page,
        "source_representation": "Activity values returned by StravaClient; not raw HTTP responses",
        "previous_source": str(args.previous), "previous_sha256": hashlib.sha256(old_bytes).hexdigest(),
        "activities": records, "out_of_interval": [record(a) for a in downloaded if not start <= a.start_date < end],
        "repeated_ids": {str(k): v for k, v in ids.items() if v > 1},
        "sports": {s: {"count": sum(r["sport_type"] == s for r in records),
                        "distance_meters": str(meters([r for r in records if r["sport_type"] == s]))} for s in sports},
        "run_total_meters": str(total), "run_count": len(runs), "weeks": weeks,
        "old_run_total_meters": str(meters(old_runs)), "run_delta_meters": str(delta),
        "id_differences": differences,
        "delta_reconciled": sum((Decimal(d["distance_delta_meters"]) for d in differences), Decimal(0)) == delta,
        "weekly_total_matches": sum((Decimal(w["independent_distance_meters"]) for w in weeks), Decimal(0)) == total,
        "display_km": str(args.strava_display_km),
        "display_minus_run_total_km": str(args.strava_display_km - total / 1000),
        "matches_display_rounded_one_decimal": (total / 1000).quantize(Decimal("0.1")) == args.strava_display_km,
    }
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2, allow_nan=False)
        output.write("\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"activities", "weeks", "id_differences"}}, indent=2))
    if not all(w["passed"] for w in weeks) or not report["delta_reconciled"] or not report["weekly_total_matches"]:
        raise SystemExit("Snapshot saved, but independent verification failed.")


if __name__ == "__main__":
    main()
