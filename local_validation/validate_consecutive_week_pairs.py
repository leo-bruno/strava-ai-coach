"""Audit weekly pairs against source dates; never modify the snapshot.

Run with python -m local_validation.validate_consecutive_week_pairs SNAPSHOT.
This audit assesses neither coverage nor calendar closure.
"""

import argparse
from copy import deepcopy
from datetime import date, datetime, time, timedelta
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from src.analytics.weekly_analysis import weekly_analysis_from_activities
from src.models.activity import Activity
from src.trends.history import consecutive_week_pairs
from src.trends.distance import weekly_running_distance_change, weekly_running_distance_percentage_change
from src.trends.activity_count import weekly_running_activity_count_change, weekly_running_activity_count_percentage_change
from src.trends.moving_time import weekly_running_moving_time_change, weekly_running_moving_time_percentage_change


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    before_hash = hashlib.sha256(raw).hexdigest()
    assert before_hash == '69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac'
    snapshot = json.loads(raw)
    timezone = ZoneInfo(snapshot['timezone'])
    dates = [date.fromisoformat(row['week_start_date']) for row in snapshot['weeks']]
    assert len(dates) == 24 and len(set(dates)) == 24
    assert all(left < right for left, right in zip(dates, dates[1:]))
    activities = [Activity(**{**row, 'start_date': datetime.fromisoformat(row['start_date'])})
                  for row in snapshot['activities']]
    observations = [weekly_analysis_from_activities(
        activities, reference_datetime=datetime.combine(day, time.min, timezone),
        athlete_timezone=timezone,
    ) for day in dates]
    originals = deepcopy(observations)
    by_date = dict(zip(dates, observations))
    # Independent oracle: calendar successors looked up in the source date set.
    source_dates = set(dates)
    expected_all = [(day, day + timedelta(days=7)) for day in dates
                    if day + timedelta(days=7) in source_dates]
    assert len(expected_all) == 23
    comparisons = (
        weekly_running_distance_change, weekly_running_distance_percentage_change,
        weekly_running_activity_count_change, weekly_running_activity_count_percentage_change,
        weekly_running_moving_time_change, weekly_running_moving_time_percentage_change,
    )
    cases = (
        ('normal', observations.copy(), set(), 23),
        ('reverse', list(reversed(observations)), set(), 23),
        ('permutation', observations[::2] + observations[1::2], set(), 23),
        ('remove_one', [item for item in observations if item.week_start_date != date(2026, 6, 29)],
         {date(2026, 6, 29)}, 21),
        ('remove_two', [item for item in observations
                        if item.week_start_date not in {date(2026, 6, 29), date(2026, 7, 6)}],
         {date(2026, 6, 29), date(2026, 7, 6)}, 20),
    )
    results = {}
    for name, supplied, removed, count in cases:
        input_ids = [id(item) for item in supplied]
        expected = [(left, right) for left, right in expected_all
                    if left not in removed and right not in removed]
        pairs = consecutive_week_pairs(supplied)
        actual = [(left.week_start_date, right.week_start_date) for left, right in pairs]
        assert actual == expected and len(pairs) == count
        assert type(pairs) is tuple
        for pair in pairs:
            assert type(pair) is tuple
            for item in pair:
                assert item is by_date[item.week_start_date]
                assert any(item is source for source in supplied)
            for compare in comparisons:
                compare(*pair)
        assert observations == originals
        assert [id(item) for item in supplied] == input_ids
        results[name] = {'observations': len(supplied), 'pairs': len(pairs),
                         'expected_pairs_match': True, 'six_comparisons_accepted': True}
    assert consecutive_week_pairs([]) == ()
    assert consecutive_week_pairs([observations[0]]) == ()
    zero_dates = [item.week_start_date for item in observations if item.running_activity_count == 0]
    pairs = consecutive_week_pairs(observations)
    zero_connections = {}
    for day in zero_dates:
        expected = [(left, right) for left, right in expected_all if day in (left, right)]
        actual = [(left.week_start_date, right.week_start_date) for left, right in pairs
                  if day in (left.week_start_date, right.week_start_date)]
        assert actual == expected and actual
        zero_connections[day.isoformat()] = len(actual)
    after_hash = hashlib.sha256(args.source.read_bytes()).hexdigest()
    assert before_hash == after_hash
    assert observations == originals
    print(json.dumps({'cases': results, 'zero_week_connections': zero_connections,
                      'identity_preserved': True, 'all_fields_and_inputs_unchanged': True,
                      'empty_and_singleton': 'passed',
                      'sha256_before': before_hash, 'sha256_after': after_hash}, indent=2))


if __name__ == '__main__':
    main()
