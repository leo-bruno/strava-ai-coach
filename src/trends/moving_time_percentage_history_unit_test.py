"""Percentage history results preserve undefined values and omit missing pairs."""

from copy import deepcopy
from datetime import date, timedelta

import pytest

from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary, WeeklyAnalysis
from src.models.weekly_running_moving_time_percentage_change import WeeklyRunningMovingTimePercentageChange
from src.trends.moving_time import weekly_running_moving_time_percentage_change, weekly_running_moving_time_percentage_changes


def week(offset, seconds):
    return WeeklyAnalysis(date(2026, 6, 1) + timedelta(weeks=offset), 1234.5, 3, seconds, tuple(
        TrainingTypeSummary(kind, 3, 1234.5, seconds) if kind is TrainingType.OTHER
        else TrainingTypeSummary(kind, 0, 0.0, 0) for kind in TrainingType
    ))


@pytest.mark.parametrize('offsets', [[], [0], [0, 2]])
def test_no_pairs(offsets):
    assert weekly_running_moving_time_percentage_changes([week(offset, 0) for offset in offsets]) == ()


@pytest.mark.parametrize('before,after,expected', [
    (4, 5, 25.0), (4, 3, -25.0), (4, 4, 0.0),
    (4, 0, -100.0), (0, 4, None), (0, 0, None),
    (3, 4, 33.333333333333336),
])
def test_percentage_result_present_and_matches_scalar(before, after, expected):
    previous, current = week(0, before), week(1, after)
    results = weekly_running_moving_time_percentage_changes([previous, current])
    assert type(results) is tuple and len(results) == 1
    result = results[0]
    assert type(result) is WeeklyRunningMovingTimePercentageChange
    assert result.previous_week_start_date == previous.week_start_date
    assert result.current_week_start_date == current.week_start_date
    assert result.value == weekly_running_moving_time_percentage_change(previous, current)
    assert result.value == expected
    assert result.value is None or type(result.value) is float


def test_multiple_weeks_preserve_defined_and_undefined_transitions():
    observations = [week(offset, seconds) for offset, seconds in enumerate((3, 4, 0, 0, 2))]
    results = weekly_running_moving_time_percentage_changes(observations)
    assert results == tuple(
        WeeklyRunningMovingTimePercentageChange(
            previous.week_start_date, current.week_start_date,
            weekly_running_moving_time_percentage_change(previous, current),
        ) for previous, current in zip(observations, observations[1:])
    )
    assert tuple(result.value for result in results) == (33.333333333333336, -100.0, None, None)


@pytest.mark.parametrize('container', [list, tuple])
@pytest.mark.parametrize('order', [(0, 1, 2, 3, 4), (4, 3, 2, 1, 0), (2, 0, 4, 1, 3)])
def test_order_gaps_none_repeatability_and_no_mutation(container, order):
    observations = [week(0, 0), week(1, 0), week(2, 3), week(4, 0), week(5, 4)]
    supplied = container(observations[index] for index in order)
    original = deepcopy(supplied)
    identities = tuple(id(item) for item in supplied)
    expected = tuple(WeeklyRunningMovingTimePercentageChange(left.week_start_date, right.week_start_date, None)
                     for left, right in ((observations[0], observations[1]),
                                         (observations[1], observations[2]),
                                         (observations[3], observations[4])))
    assert weekly_running_moving_time_percentage_changes(supplied) == expected
    assert weekly_running_moving_time_percentage_changes(supplied) == expected
    assert supplied == original
    assert tuple(id(item) for item in supplied) == identities


@pytest.mark.parametrize('invalid', ['non_monday', 'duplicate'])
def test_normalization_errors_do_not_mutate(invalid):
    from dataclasses import replace
    observation = week(0, 0)
    supplied = ([replace(observation, week_start_date=date(2026, 6, 2))]
                if invalid == 'non_monday' else [observation, week(1, 0), observation])
    original = deepcopy(supplied)
    identities = tuple(id(item) for item in supplied)
    with pytest.raises(ValueError):
        weekly_running_moving_time_percentage_changes(supplied)
    assert supplied == original
    assert tuple(id(item) for item in supplied) == identities
