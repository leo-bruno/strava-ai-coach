"""Audit absolute and percentage volume differences for existing consecutive snapshot observations.

Run with python -m local_validation.validate_weekly_distance_change SNAPSHOT.
No observations are synthesized, and no calendar-closure or completeness
assessment is performed. The snapshot remains unchanged; JSON goes to stdout.
"""

import argparse
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import hashlib
import json
from math import isclose
from pathlib import Path
from zoneinfo import ZoneInfo

from src.analytics.weekly_analysis import weekly_analysis_from_activities
from src.models.activity import Activity
from src.trends.distance import weekly_running_distance_change
from src.trends.activity_count import weekly_running_activity_count_change
from src.trends.moving_time import weekly_running_moving_time_change
from src.trends.distance import weekly_running_distance_percentage_change
from src.trends.activity_count import weekly_running_activity_count_percentage_change
from src.trends.moving_time import weekly_running_moving_time_percentage_change


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    source_bytes = args.source.read_bytes()
    snapshot = json.loads(source_bytes)
    tz = ZoneInfo(snapshot["timezone"])
    activities = [
        Activity(**{**record, "start_date": datetime.fromisoformat(record["start_date"])})
        for record in snapshot["activities"]
    ]

    # Independent source totals: decimal literals grouped by local ISO week.
    source_totals = defaultdict(Decimal)
    source_counts = defaultdict(int)
    source_times = defaultdict(int)
    for record in json.loads(source_bytes, parse_float=Decimal)["activities"]:
        if record["sport_type"] == "Run":
            local = datetime.fromisoformat(record["start_date"]).astimezone(tz)
            iso = local.date().isocalendar()
            monday = date.fromisocalendar(iso.year, iso.week, 1)
            source_totals[monday] += record["distance_meters"]
            source_counts[monday] += 1
            source_times[monday] += record["moving_time_seconds"]

    # Only dates already recorded in the snapshot's weekly observations.
    dates = sorted(date.fromisoformat(row["week_start_date"]) for row in snapshot["weeks"])
    observations = {
        monday: weekly_analysis_from_activities(
            activities,
            reference_datetime=datetime.combine(monday, time.min, tz),
            athlete_timezone=tz,
        )
        for monday in dates
    }
    rows = []
    for previous_date, current_date in zip(dates, dates[1:]):
        if current_date - previous_date != timedelta(days=7):
            continue
        previous, current = observations[previous_date], observations[current_date]
        expected = source_totals[current_date] - source_totals[previous_date]
        actual = weekly_running_distance_change(previous, current)
        expected_count = source_counts[current_date] - source_counts[previous_date]
        expected_time = source_times[current_date] - source_times[previous_date]
        actual_count = weekly_running_activity_count_change(previous, current)
        actual_time = weekly_running_moving_time_change(previous, current)
        integer_totals_match = all(
            observations[day].running_activity_count == source_counts[day]
            and observations[day].running_moving_time_seconds == source_times[day]
            for day in (previous_date, current_date)
        )
        totals_match = all(
            isclose(observations[day].running_distance_meters, float(source_totals[day]),
                    rel_tol=1e-12, abs_tol=1e-9)
            for day in (previous_date, current_date)
        )
        percentages = {}
        for metric, source_values, actual_percentage in (
            ("distance", source_totals, weekly_running_distance_percentage_change(previous, current)),
            ("activity_count", source_counts, weekly_running_activity_count_percentage_change(previous, current)),
            ("moving_time", source_times, weekly_running_moving_time_percentage_change(previous, current)),
        ):
            base = Decimal(source_values[previous_date])
            value = Decimal(source_values[current_date])
            # Independent Decimal ratio of source totals, not production helpers.
            expected_percentage = None if base == 0 else (value / base - 1) * 100
            percentage_passed = (
                actual_percentage is None if expected_percentage is None else
                type(actual_percentage) is float and isclose(
                    actual_percentage, float(expected_percentage), rel_tol=1e-12, abs_tol=1e-10,
                )
            )
            percentages[metric] = {
                "previous_source": str(base), "current_source": str(value),
                "expected": None if expected_percentage is None else str(expected_percentage),
                "actual": actual_percentage, "passed": percentage_passed,
            }
        rows.append({
            "percentages": percentages,
            "previous_week": previous_date.isoformat(),
            "current_week": current_date.isoformat(),
            "previous_source_meters": str(source_totals[previous_date]),
            "current_source_meters": str(source_totals[current_date]),
            "expected_change_meters": str(expected),
            "actual_change_meters": actual,
            "difference_meters": actual - float(expected),
            "previous_source_count": source_counts[previous_date],
            "current_source_count": source_counts[current_date],
            "previous_source_seconds": source_times[previous_date],
            "current_source_seconds": source_times[current_date],
            "expected_count_change": expected_count,
            "actual_count_change": actual_count,
            "expected_time_change_seconds": expected_time,
            "actual_time_change_seconds": actual_time,
            "count_passed": type(actual_count) is int and actual_count == expected_count,
            "time_passed": type(actual_time) is int and actual_time == expected_time,
            "passed": all(item["passed"] for item in percentages.values())
            and totals_match and integer_totals_match
            and type(actual_count) is int and actual_count == expected_count
            and type(actual_time) is int and actual_time == expected_time
            and type(actual) is float
            and isclose(actual, float(expected), rel_tol=1e-12, abs_tol=1e-9),
        })

    unchanged = args.source.read_bytes() == source_bytes
    passed = unchanged and bool(rows) and all(row["passed"] for row in rows)
    percentage_counts = {
        metric: {
            "defined": sum(row["percentages"][metric]["actual"] is not None for row in rows),
            "undefined_zero_base": sum(row["percentages"][metric]["actual"] is None for row in rows),
        }
        for metric in ("distance", "activity_count", "moving_time")
    }
    print(json.dumps({
        "source": str(args.source),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_unchanged": unchanged,
        "observation_count": len(dates),
        "consecutive_pair_count": len(rows),
        "relative_tolerance": 1e-12,
        "absolute_tolerance_meters": 1e-9,
        "percentage_counts": percentage_counts,
        "percentage_absolute_tolerance": 1e-10,
        "passed": passed,
        "pairs": rows,
    }, indent=2))
    if not passed:
        raise SystemExit("Offline weekly volume change verification failed.")


if __name__ == "__main__":
    main()
