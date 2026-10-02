"""Audit dated percentage activity count changes against snapshot weekly totals.

Run with python -m local_validation.validate_activity_count_percentage_history SNAPSHOT.
Only supplied observations are used; coverage and calendar closure are not assessed.
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
from src.models.weekly_running_activity_count_percentage_change import WeeklyRunningActivityCountPercentageChange
from src.trends.activity_count import weekly_running_activity_count_percentage_change, weekly_running_activity_count_percentage_changes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    before_hash = hashlib.sha256(raw).hexdigest()
    assert before_hash == '69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac'
    snapshot = json.loads(raw)
    source = {date.fromisoformat(row['week_start_date']): row['running_activity_count']
              for row in snapshot['weeks']}
    dates = list(source)
    assert len(dates) == 24
    assert all(left < right for left, right in zip(dates, dates[1:]))
    expected_pairs = [(day, day + timedelta(days=7)) for day in dates
                      if day + timedelta(days=7) in source]
    assert len(expected_pairs) == 23
    timezone = ZoneInfo(snapshot['timezone'])
    activities = [Activity(**{**row, 'start_date': datetime.fromisoformat(row['start_date'])})
                  for row in snapshot['activities']]
    observations = [weekly_analysis_from_activities(
        activities, reference_datetime=datetime.combine(day, time.min, timezone),
        athlete_timezone=timezone,
    ) for day in dates]
    originals = deepcopy(observations)
    by_date = dict(zip(dates, observations))
    assert all(item.running_activity_count == source[item.week_start_date] for item in observations)
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
    baseline = None
    max_error = 0.0
    for name, supplied, removed, count in cases:
        identities = [id(item) for item in supplied]
        supplied_originals = deepcopy(supplied)
        expected = [(left, right) for left, right in expected_pairs
                    if left not in removed and right not in removed]
        actual = weekly_running_activity_count_percentage_changes(supplied)
        assert type(actual) is tuple and len(actual) == count
        assert [(item.previous_week_start_date, item.current_week_start_date) for item in actual] == expected
        for item, (left, right) in zip(actual, expected):
            assert type(item) is WeeklyRunningActivityCountPercentageChange
            assert item.value == weekly_running_activity_count_percentage_change(by_date[left], by_date[right])
            if source[left] == 0:
                assert item.value is None
            else:
                assert type(item.value) is float
                independent = float(100 * (source[right] - source[left]) / source[left])
                assert item.value == independent
                max_error = max(max_error, abs(item.value - independent))
        if name == 'normal':
            baseline = actual
        elif not removed:
            assert actual == baseline
        assert observations == originals
        assert supplied == supplied_originals
        assert [id(item) for item in supplied] == identities
        results[name] = len(actual)
    zero_dates = [day for day in dates if source[day] == 0]
    assert zero_dates == [item.week_start_date for item in observations if item.running_activity_count == 0]
    zero_transitions = []
    examples = {}
    for item in baseline:
        left, right = item.previous_week_start_date, item.current_week_start_date
        row = {'previous': left.isoformat(), 'current': right.isoformat(), 'value_percentage': item.value}
        label = ('undefined' if item.value is None else 'minus_100' if item.value == -100.0
                 else 'positive' if item.value > 0 else 'negative' if item.value < 0 else 'zero')
        examples.setdefault(label, row)
        if left in zero_dates or right in zero_dates:
            zero_transitions.append(row)
    assert all(any(day.isoformat() in (row['previous'], row['current'])
                   for row in zero_transitions) for day in zero_dates)
    defined = sum(item.value is not None for item in baseline)
    undefined = sum(item.value is None for item in baseline)
    assert (defined, undefined) == (19, 4)
    assert set(examples) == {'positive', 'negative', 'zero', 'minus_100', 'undefined'}
    after_hash = hashlib.sha256(args.source.read_bytes()).hexdigest()
    assert before_hash == after_hash
    print(json.dumps({'result_counts': results, 'examples': examples,
                      'zero_transitions': zero_transitions, 'defined': defined, 'undefined': undefined, 'max_source_error_percentage_points': max_error,
                      'exact_scalar_match': True, 'inputs_and_identity_unchanged': True,
                      'sha256_before': before_hash, 'sha256_after': after_hash}, indent=2))


if __name__ == '__main__':
    main()
