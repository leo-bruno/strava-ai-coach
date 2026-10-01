"""Audit history normalization without modifying the supplied snapshot.

Run with python -m local_validation.validate_weekly_history_normalization SNAPSHOT.
Only the snapshot's existing weekly observation dates are used. No claim about
history coverage or calendar closure is made. Results are printed as JSON.
"""

import argparse
from copy import deepcopy
from datetime import date, datetime, time
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from src.analytics.weekly_analysis import weekly_analysis_from_activities
from src.models.activity import Activity
from src.trends.history import normalize_weekly_history


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    source_bytes = args.source.read_bytes()
    before_hash = hashlib.sha256(source_bytes).hexdigest()
    snapshot = json.loads(source_bytes)
    timezone = ZoneInfo(snapshot["timezone"])
    activities = [Activity(**{**record, "start_date": datetime.fromisoformat(record["start_date"])})
                  for record in snapshot["activities"]]
    # The source chronology is the oracle, independent of normalization.
    dates = [date.fromisoformat(row["week_start_date"]) for row in snapshot["weeks"]]
    assert len(dates) == 24
    assert all(left < right for left, right in zip(dates, dates[1:]))
    observations = [weekly_analysis_from_activities(
        activities, reference_datetime=datetime.combine(day, time.min, timezone),
        athlete_timezone=timezone,
    ) for day in dates]
    originals = deepcopy(observations)
    orders = {}
    for name, supplied in (
        ("normal", observations.copy()),
        ("reverse", list(reversed(observations))),
        ("permutation", observations[::2] + observations[1::2]),
    ):
        input_ids = [id(item) for item in supplied]
        result = normalize_weekly_history(supplied)
        assert type(result) is tuple
        assert [item.week_start_date for item in result] == dates
        assert len(result) == 24
        assert all(actual is expected for actual, expected in zip(result, observations))
        assert [id(item) for item in supplied] == input_ids
        assert observations == originals
        orders[name] = len(result)

    removed = observations[10]
    supplied = [item for item in reversed(observations) if item is not removed]
    input_copy = supplied.copy()
    result = normalize_weekly_history(supplied)
    assert len(result) == 23
    assert [item.week_start_date for item in result] == [day for day in dates if day != removed.week_start_date]
    assert all(actual is expected for actual, expected in zip(
        result, [item for item in observations if item is not removed],
    ))
    assert supplied == input_copy

    supplied = list(reversed(observations)) + [observations[10]]
    input_ids = [id(item) for item in supplied]
    try:
        normalize_weekly_history(supplied)
    except ValueError:
        duplicate_rejected = True
    else:
        raise AssertionError("Duplicate observation was accepted")
    assert [id(item) for item in supplied] == input_ids
    assert observations == originals
    zero_dates = [item.week_start_date.isoformat() for item in observations
                  if item.running_activity_count == 0]
    normalized = normalize_weekly_history(observations)
    assert zero_dates == [item.week_start_date.isoformat() for item in normalized
                          if item.running_activity_count == 0]
    after_hash = hashlib.sha256(args.source.read_bytes()).hexdigest()
    assert before_hash == after_hash
    print(json.dumps({
        "orders": orders, "removed_date": removed.week_start_date.isoformat(),
        "remaining_observations": len(result), "duplicate_rejected": duplicate_rejected,
        "zero_run_dates_preserved": zero_dates,
        "all_fields_and_structure_unchanged": observations == originals,
        "original_objects_preserved": True, "input_collections_unchanged": True,
        "source_sha256_before": before_hash, "source_sha256_after": after_hash,
    }, indent=2))


if __name__ == "__main__":
    main()
