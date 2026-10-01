"""Percentage history results preserve undefined values and omit missing pairs."""

from copy import deepcopy
from datetime import date, timedelta

import pytest

from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary, WeeklyAnalysis
from src.models.weekly_running_distance_percentage_change import WeeklyRunningDistancePercentageChange
from src.trends.distance import weekly_running_distance_percentage_change, weekly_running_distance_percentage_changes


def week(offset, distance):
    return WeeklyAnalysis(date(2026, 6, 1) + timedelta(weeks=offset), distance, 1, 601, tuple(
        TrainingTypeSummary(kind, 1, distance, 601) if kind is TrainingType.OTHER
        else TrainingTypeSummary(kind, 0, 0.0, 0) for kind in TrainingType
    ))


@pytest.mark.parametrize('offsets', [[], [0], [0, 2]])
def test_no_pairs(offsets):
    assert weekly_running_distance_percentage_changes([week(offset, 0.0) for offset in offsets]) == ()


@pytest.mark.parametrize('before,after,expected', [
    (100.0, 125.0, 25.0), (100.0, 75.0, -25.0), (100.0, 100.0, 0.0),
    (100.0, 0.0, -100.0), (0.0, 100.0, None), (0.0, 0.0, None),
    (3.0, 4.0, 33.333333333333336),
])
def test_percentage_result_present_and_matches_scalar(before, after, expected):
    previous, current = week(0, before), week(1, after)
    results = weekly_running_distance_percentage_changes([previous, current])
    assert type(results) is tuple and len(results) == 1
    result = results[0]
    assert type(result) is WeeklyRunningDistancePercentageChange
    assert result.previous_week_start_date == previous.week_start_date
    assert result.current_week_start_date == current.week_start_date
    assert result.value == weekly_running_distance_percentage_change(previous, current)
    assert result.value == expected
    assert result.value is None or type(result.value) is float


@pytest.mark.parametrize('container', [list, tuple])
@pytest.mark.parametrize('order', [(0, 1, 2, 3, 4), (4, 3, 2, 1, 0), (2, 0, 4, 1, 3)])
def test_order_gaps_none_repeatability_and_no_mutation(container, order):
    observations = [week(0, 0.0), week(1, 0.0), week(2, 10.0), week(4, 0.0), week(5, 20.0)]
    supplied = container(observations[index] for index in order)
    original = deepcopy(supplied)
    identities = tuple(id(item) for item in supplied)
    expected = tuple(WeeklyRunningDistancePercentageChange(left.week_start_date, right.week_start_date, None)
                     for left, right in ((observations[0], observations[1]),
                                         (observations[1], observations[2]),
                                         (observations[3], observations[4])))
    assert weekly_running_distance_percentage_changes(supplied) == expected
    assert weekly_running_distance_percentage_changes(supplied) == expected
    assert supplied == original
    assert tuple(id(item) for item in supplied) == identities


@pytest.mark.parametrize('invalid', ['non_monday', 'duplicate'])
def test_normalization_errors_do_not_mutate(invalid):
    from dataclasses import replace
    observation = week(0, 0.0)
    supplied = ([replace(observation, week_start_date=date(2026, 6, 2))]
                if invalid == 'non_monday' else [observation, week(1, 0.0), observation])
    original = deepcopy(supplied)
    identities = tuple(id(item) for item in supplied)
    with pytest.raises(ValueError):
        weekly_running_distance_percentage_changes(supplied)
    assert supplied == original
    assert tuple(id(item) for item in supplied) == identities
