"""Dated distance changes composed from weekly observations."""

from copy import deepcopy
from datetime import date, timedelta

import pytest

from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary, WeeklyAnalysis
from src.models.weekly_running_distance_change import WeeklyRunningDistanceChange
from src.trends.distance import weekly_running_distance_change, weekly_running_distance_changes


def week(offset, distance=1000.0, start=date(2026, 6, 1)):
    return WeeklyAnalysis(start + timedelta(weeks=offset), distance, 1, 601, tuple(
        TrainingTypeSummary(kind, 1, distance, 601) if kind is TrainingType.OTHER
        else TrainingTypeSummary(kind, 0, 0.0, 0) for kind in TrainingType
    ))


@pytest.mark.parametrize('offsets', [[], [0], [0, 2, 4]])
def test_no_pairs(offsets):
    assert weekly_running_distance_changes([week(offset) for offset in offsets]) == ()


@pytest.mark.parametrize('before,after', [
    (1000.0, 1500.0), (1500.0, 1000.0), (1000.0, 1000.0),
    (0.0, 1000.0), (1000.0, 0.0), (0.0, 0.0), (1234.56789, 1234.56812),
])
def test_value_and_dates_match_scalar_exactly(before, after):
    previous, current = week(0, before), week(1, after)
    results = weekly_running_distance_changes([previous, current])
    assert type(results) is tuple
    assert len(results) == 1
    result = results[0]
    assert type(result) is WeeklyRunningDistanceChange
    assert result.previous_week_start_date == previous.week_start_date
    assert result.current_week_start_date == current.week_start_date
    assert type(result.value) is float
    assert result.value == weekly_running_distance_change(previous, current)


@pytest.mark.parametrize('container', [list, tuple])
@pytest.mark.parametrize('order', [(0, 1, 2, 3), (3, 2, 1, 0), (2, 0, 3, 1)])
def test_order_gaps_repeatability_and_no_mutation(container, order):
    observations = [week(offset, offset * 123.456789) for offset in (0, 1, 2, 4)]
    supplied = container(observations[index] for index in order)
    original = deepcopy(supplied)
    identities = tuple(id(item) for item in supplied)
    expected = tuple(WeeklyRunningDistanceChange(left.week_start_date, right.week_start_date,
                                                weekly_running_distance_change(left, right))
                     for left, right in ((observations[0], observations[1]),
                                         (observations[1], observations[2])))
    assert weekly_running_distance_changes(supplied) == expected
    assert weekly_running_distance_changes(supplied) == expected
    assert supplied == original
    assert tuple(id(item) for item in supplied) == identities


def test_year_boundary():
    previous = week(0, start=date(2025, 12, 29))
    current = week(1, start=date(2025, 12, 29))
    assert weekly_running_distance_changes([current, previous]) == (
        WeeklyRunningDistanceChange(date(2025, 12, 29), date(2026, 1, 5), 0.0),
    )


@pytest.mark.parametrize('invalid', ['non_monday', 'duplicate'])
def test_errors_propagate_without_mutation(invalid):
    observation = week(0)
    supplied = ([week(0, start=date(2026, 6, 2))] if invalid == 'non_monday'
                else [observation, week(1), observation])
    original = deepcopy(supplied)
    identities = tuple(id(item) for item in supplied)
    with pytest.raises(ValueError):
        weekly_running_distance_changes(supplied)
    assert supplied == original
    assert tuple(id(item) for item in supplied) == identities
