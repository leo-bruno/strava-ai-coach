"""Offline count, distance and moving-time audit using independently reviewed name labels.

Run with python -m local_validation.validate_weekly_structure SNAPSHOT LABELS.
LABELS is a JSON object mapping every observed Run name to its reviewed type.
Unknown names fail rather than silently becoming Other. Personal labels and
snapshots stay in ignored JSON files; results go to stdout. No network access.
"""

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import hashlib
import json
from math import isclose
from pathlib import Path
from zoneinfo import ZoneInfo

from src.analytics.weekly_analysis import weekly_analysis_from_activities
from src.models.activity import Activity
from src.models.training_analysis import TrainingType


def distances_match(actual: float, expected: float | Decimal) -> bool:
    """Compare audit measurements without rounding or changing production data.

    Allow relative float error of 1e-12 and an absolute floor of 1e-9 meters,
    including for zero totals. These tolerances apply only to this audit.
    """
    return isclose(actual, float(expected), rel_tol=1e-12, abs_tol=1e-9)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("labels", type=Path)
    args = parser.parse_args()
    source_bytes = args.source.read_bytes()
    label_bytes = args.labels.read_bytes()
    snapshot = json.loads(source_bytes)
    labels = json.loads(label_bytes)
    kinds = [kind.value for kind in TrainingType]
    if any(label not in kinds for label in labels.values()):
        raise ValueError("Labels must use existing TrainingType values.")
    tz = ZoneInfo(snapshot["timezone"])
    start = datetime.fromisoformat(snapshot["start_inclusive"])
    end = datetime.fromisoformat(snapshot["end_exclusive"])
    extracted = datetime.fromisoformat(snapshot["extraction_finished_at"])
    records = snapshot["activities"]
    activities = [
        Activity(**{**record, "start_date": datetime.fromisoformat(record["start_date"])})
        for record in records
    ]

    # Independent oracle: exact, manually reviewed names and ISO local dates.
    # No production classifier, regular expressions, week bounds or selectors.
    groups = defaultdict(Counter)
    source_counts = Counter(dict.fromkeys(kinds, 0))
    distance_groups = defaultdict(lambda: defaultdict(Decimal))
    source_distances = dict.fromkeys(kinds, Decimal(0))
    time_groups = defaultdict(Counter)
    source_times = Counter(dict.fromkeys(kinds, 0))
    # Parse JSON decimal literals directly for an exact, independent sum.
    for record in json.loads(source_bytes, parse_float=Decimal)["activities"]:
        if record["sport_type"] == "Run":
            label = labels[record["name"]]
            local = datetime.fromisoformat(record["start_date"]).astimezone(tz)
            iso = local.date().isocalendar()
            monday = date.fromisocalendar(iso.year, iso.week, 1)
            groups[monday][label] += 1
            source_counts[label] += 1
            distance_groups[monday][label] += record["distance_meters"]
            source_distances[label] += record["distance_meters"]
            time_groups[monday][label] += record["moving_time_seconds"]
            source_times[label] += record["moving_time_seconds"]

    rows = []
    weekly_counts = Counter(dict.fromkeys(kinds, 0))
    weekly_distances = dict.fromkeys(kinds, 0.0)
    weekly_times = Counter(dict.fromkeys(kinds, 0))
    monday = start.astimezone(tz).date()
    monday -= timedelta(days=monday.weekday())
    while datetime.combine(monday, time.min, tz) < end:
        expected = {kind: groups[monday][kind] for kind in kinds}
        result = weekly_analysis_from_activities(
            activities,
            reference_datetime=datetime.combine(monday, time.min, tz),
            athlete_timezone=tz,
        )
        summaries = result.running_structure_by_type
        actual = {item.training_type.value: item.activity_count for item in summaries}
        reconciled = sum(actual.values()) == result.running_activity_count
        expected_distances = {kind: distance_groups[monday][kind] for kind in kinds}
        actual_distances = {item.training_type.value: item.distance_meters for item in summaries}
        category_total = sum(actual_distances.values())
        expected_total = sum(expected_distances.values(), Decimal(0))
        distance_reconciled = distances_match(category_total, result.running_distance_meters)
        expected_times = {kind: time_groups[monday][kind] for kind in kinds}
        actual_times = {item.training_type.value: item.moving_time_seconds for item in summaries}
        time_reconciled = sum(actual_times.values()) == result.running_moving_time_seconds
        passed = (
            result.week_start_date == monday
            and [item.training_type.value for item in summaries] == kinds
            and all(type(item.activity_count) is int for item in summaries)
            and actual == expected
            and result.running_activity_count == sum(expected.values())
            and reconciled
            and all(type(item.distance_meters) is float for item in summaries)
            and all(distances_match(actual_distances[kind], expected_distances[kind]) for kind in kinds)
            and distances_match(result.running_distance_meters, expected_total)
            and distance_reconciled
            and all(type(item.moving_time_seconds) is int for item in summaries)
            and actual_times == expected_times
            and result.running_moving_time_seconds == sum(expected_times.values())
            and time_reconciled
        )
        rows.append({
            "week_start_date": monday.isoformat(),
            "expected": expected,
            "actual": actual,
            "running_activity_count": result.running_activity_count,
            "reconciled": reconciled,
            "expected_moving_time_seconds": expected_times,
            "actual_moving_time_seconds": actual_times,
            "running_moving_time_seconds": result.running_moving_time_seconds,
            "moving_time_reconciled": time_reconciled,
            "expected_distance_meters": {kind: str(value) for kind, value in expected_distances.items()},
            "actual_distance_meters": actual_distances,
            "running_distance_meters": result.running_distance_meters,
            "category_distance_total_meters": category_total,
            "distance_reconciled": distance_reconciled,
            "distance_reconciliation_delta_meters": category_total - result.running_distance_meters,
            "period_closed_at_extraction": datetime.combine(monday + timedelta(days=7), time.min, tz) <= extracted,
            "passed": passed,
        })
        weekly_counts.update(actual)
        weekly_times.update(actual_times)
        for kind in kinds:
            weekly_distances[kind] += actual_distances[kind]
        monday += timedelta(days=7)

    run_count = sum(record["sport_type"] == "Run" for record in records)
    unchanged = args.source.read_bytes() == source_bytes and args.labels.read_bytes() == label_bytes
    source_total_distance = sum(source_distances.values(), Decimal(0))
    category_total_distance = sum(weekly_distances.values())
    weekly_total_distance = sum(row["running_distance_meters"] for row in rows)
    global_distance_reconciled = (
        distances_match(category_total_distance, weekly_total_distance)
        and distances_match(category_total_distance, source_total_distance)
        and distances_match(weekly_total_distance, source_total_distance)
    )
    source_total_time = sum(source_times.values())
    weekly_total_time = sum(row["running_moving_time_seconds"] for row in rows)
    global_time_reconciled = sum(weekly_times.values()) == weekly_total_time == source_total_time
    passed = (
        unchanged and all(row["passed"] for row in rows)
        and weekly_counts == source_counts
        and sum(weekly_counts.values()) == run_count
        and all(distances_match(weekly_distances[kind], source_distances[kind]) for kind in kinds)
        and global_distance_reconciled
        and weekly_times == source_times
        and global_time_reconciled
    )
    print(json.dumps({
        "source": str(args.source),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "labels": str(args.labels),
        "labels_sha256": hashlib.sha256(label_bytes).hexdigest(),
        "inputs_unchanged": unchanged,
        "timezone": snapshot["timezone"],
        "activity_count": len(records),
        "run_count": run_count,
        "independent_counts": dict(source_counts),
        "weekly_counts": dict(weekly_counts),
        "independent_distance_meters": {kind: str(value) for kind, value in source_distances.items()},
        "weekly_distance_meters": weekly_distances,
        "source_total_distance_meters": str(source_total_distance),
        "category_total_distance_meters": category_total_distance,
        "weekly_total_distance_meters": weekly_total_distance,
        "global_distance_reconciled": global_distance_reconciled,
        "distance_relative_tolerance": 1e-12,
        "distance_absolute_tolerance_meters": 1e-9,
        "independent_moving_time_seconds": dict(source_times),
        "weekly_moving_time_seconds": dict(weekly_times),
        "source_total_moving_time_seconds": source_total_time,
        "weekly_total_moving_time_seconds": weekly_total_time,
        "global_moving_time_reconciled": global_time_reconciled,
        "passed": passed,
        "weeks": rows,
    }, indent=2))
    if not passed:
        raise SystemExit("Offline weekly structure verification failed.")


if __name__ == "__main__":
    main()
