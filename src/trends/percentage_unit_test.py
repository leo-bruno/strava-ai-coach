"""Percentage semantics through the three public volume APIs."""

from copy import deepcopy
from dataclasses import replace
from datetime import date

import pytest

from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary, WeeklyAnalysis
from src.trends.activity_count import weekly_running_activity_count_percentage_change
from src.trends.distance import weekly_running_distance_percentage_change
from src.trends.moving_time import weekly_running_moving_time_percentage_change


def week(start, distance, count, seconds):
    return WeeklyAnalysis(start, distance, count, seconds, tuple(
        TrainingTypeSummary(kind, count, distance, seconds)
        if kind is TrainingType.OTHER else TrainingTypeSummary(kind, 0, 0.0, 0)
        for kind in TrainingType
    ))


@pytest.fixture(params=[
    (weekly_running_distance_percentage_change, "running_distance_meters"),
    (weekly_running_activity_count_percentage_change, "running_activity_count"),
    (weekly_running_moving_time_percentage_change, "running_moving_time_seconds"),
], ids=["distance", "count", "time"])
def metric(request):
    return request.param


@pytest.mark.parametrize("before,after,expected", [
    (100, 110, 10.0), (100, 75, -25.0), (7, 7, 0.0),
    (7, 0, -100.0), (0, 7, None), (0, 0, None),
    (3, 4, 33.333333333333336),
])
def test_percentage_semantics(metric, before, after, expected):
    compare, field = metric
    previous = replace(week(date(2026, 9, 14), 50.0, 2, 600), **{field: before})
    current = replace(week(date(2026, 9, 21), 50.0, 2, 600), **{field: after})
    original = deepcopy((previous, current))
    for _ in range(2):
        result = compare(previous, current)
        if expected is None:
            assert result is None
        else:
            assert type(result) is float
            assert result == pytest.approx(expected, rel=1e-14, abs=1e-14)
    assert (previous, current) == original


def test_fractional_distance_is_not_rounded_or_treated_as_zero():
    previous = week(date(2026, 9, 14), 0.000003, 1, 1)
    current = week(date(2026, 9, 21), 0.000004, 1, 1)
    result = weekly_running_distance_percentage_change(previous, current)
    assert type(result) is float
    assert result == pytest.approx(33.33333333333333, rel=1e-14)


@pytest.mark.parametrize("previous_date,current_date", [
    (date(2026, 9, 14), date(2026, 9, 14)),
    (date(2026, 9, 21), date(2026, 9, 14)),
    (date(2026, 9, 7), date(2026, 9, 21)),
    (date(2026, 9, 15), date(2026, 9, 21)),
    (date(2026, 9, 14), date(2026, 9, 22)),
])
def test_invalid_dates_are_rejected_before_zero_base_result(metric, previous_date, current_date):
    compare, _ = metric
    previous = week(previous_date, 0.0, 0, 0)
    current = week(current_date, 0.0, 0, 0)
    original = deepcopy((previous, current))
    with pytest.raises(ValueError):
        compare(previous, current)
    assert (previous, current) == original
