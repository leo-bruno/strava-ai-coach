"""Dated moving time changes composed from weekly observations."""

from copy import deepcopy
from datetime import date, timedelta

import pytest

from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary, WeeklyAnalysis
from src.models.weekly_running_moving_time_change import WeeklyRunningMovingTimeChange
from src.trends.moving_time import weekly_running_moving_time_change, weekly_running_moving_time_changes


def week(offset, seconds=3600, start=date(2026, 6, 1)):
    return WeeklyAnalysis(start + timedelta(weeks=offset), 1234.5, 3, seconds, tuple(
        TrainingTypeSummary(kind, 3, 1234.5, seconds) if kind is TrainingType.OTHER
        else TrainingTypeSummary(kind, 0, 0.0, 0) for kind in TrainingType
    ))


@pytest.mark.parametrize('offsets', [[], [0], [0, 2, 4]])
def test_no_pairs(offsets):
    assert weekly_running_moving_time_changes([week(offset) for offset in offsets]) == ()


@pytest.mark.parametrize('before,after', [
    (3600, 5400), (5400, 3600), (3600, 3600), (0, 3600), (3600, 0), (0, 0), (2**53, 2**53 + 1),
])
def test_value_and_dates_match_scalar_exactly(before, after):
    previous, current = week(0, before), week(1, after)
    results = weekly_running_moving_time_changes([previous, current])
    assert type(results) is tuple
    assert len(results) == 1
    result = results[0]
    assert type(result) is WeeklyRunningMovingTimeChange
    assert result.previous_week_start_date == previous.week_start_date
    assert result.current_week_start_date == current.week_start_date
    assert type(result.value) is int
    assert result.value == weekly_running_moving_time_change(previous, current)


@pytest.mark.parametrize('container', [list, tuple])
@pytest.mark.parametrize('order', [(0, 1, 2, 3), (3, 2, 1, 0), (2, 0, 3, 1)])
def test_order_gaps_repeatability_and_no_mutation(container, order):
    observations = [week(offset, offset * 3) for offset in (0, 1, 2, 4)]
    supplied = container(observations[index] for index in order)
    original = deepcopy(supplied)
    identities = tuple(id(item) for item in supplied)
    expected = tuple(WeeklyRunningMovingTimeChange(left.week_start_date, right.week_start_date,
                                                weekly_running_moving_time_change(left, right))
                     for left, right in ((observations[0], observations[1]),
                                         (observations[1], observations[2])))
    assert weekly_running_moving_time_changes(supplied) == expected
    assert weekly_running_moving_time_changes(supplied) == expected
    assert supplied == original
    assert tuple(id(item) for item in supplied) == identities


def test_year_boundary():
    previous = week(0, start=date(2025, 12, 29))
    current = week(1, start=date(2025, 12, 29))
    assert weekly_running_moving_time_changes([current, previous]) == (
        WeeklyRunningMovingTimeChange(date(2025, 12, 29), date(2026, 1, 5), 0),
    )


@pytest.mark.parametrize('invalid', ['non_monday', 'duplicate'])
def test_errors_propagate_without_mutation(invalid):
    observation = week(0)
    supplied = ([week(0, start=date(2026, 6, 2))] if invalid == 'non_monday'
                else [observation, week(1), observation])
    original = deepcopy(supplied)
    identities = tuple(id(item) for item in supplied)
    with pytest.raises(ValueError):
        weekly_running_moving_time_changes(supplied)
    assert supplied == original
    assert tuple(id(item) for item in supplied) == identities


def test_multiple_consecutive_weeks_keep_integer_seconds_and_zero_transitions():
    observations = [week(offset, seconds) for offset, seconds in
                    enumerate((3600, 5400, 3600, 3600, 0, 0, 3600))]
    results = weekly_running_moving_time_changes(observations)
    assert len(results) == 6
    assert tuple(result.value for result in results) == (1800, -1800, 0, -3600, 0, 3600)
    assert all(type(result.value) is int for result in results)
    assert results == tuple(
        WeeklyRunningMovingTimeChange(previous.week_start_date, current.week_start_date,
                                      weekly_running_moving_time_change(previous, current))
        for previous, current in zip(observations, observations[1:])
    )
