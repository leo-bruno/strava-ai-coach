"""Public contracts for integer weekly volume changes.

Distance tests cover the exhaustive shared date contract. These tests exercise
both rejection rules through each new API without repeating that whole matrix.
"""

from copy import deepcopy
from datetime import date

import pytest

from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary, WeeklyAnalysis
from src.trends.activity_count import weekly_running_activity_count_change
from src.trends.moving_time import weekly_running_moving_time_change


def week(start: date, count: int, seconds: int) -> WeeklyAnalysis:
    return WeeklyAnalysis(
        week_start_date=start,
        running_distance_meters=0.0,
        running_activity_count=count,
        running_moving_time_seconds=seconds,
        running_structure_by_type=tuple(
            TrainingTypeSummary(kind, count, 0.0, seconds)
            if kind is TrainingType.OTHER else TrainingTypeSummary(kind, 0, 0.0, 0)
            for kind in TrainingType
        ),
    )


@pytest.mark.parametrize("previous_count,current_count,previous_seconds,current_seconds,expected_count,expected_seconds", [
    (3, 5, 3601, 1801, 2, -1800),
    (5, 3, 1801, 3601, -2, 1800),
    (3, 3, 61, 61, 0, 0),
    (0, 2, 0, 91, 2, 91),
    (2, 0, 91, 0, -2, -91),
    (0, 0, 0, 0, 0, 0),
    (1, 2, 2**53, 2**53 + 1, 1, 1),
])
def test_exact_integer_changes(previous_count, current_count, previous_seconds,
                              current_seconds, expected_count, expected_seconds) -> None:
    previous = week(date(2026, 9, 14), previous_count, previous_seconds)
    current = week(date(2026, 9, 21), current_count, current_seconds)
    count = weekly_running_activity_count_change(previous=previous, current=current)
    seconds = weekly_running_moving_time_change(previous=previous, current=current)
    assert type(count) is int
    assert type(seconds) is int
    assert count == expected_count
    assert seconds == expected_seconds


@pytest.mark.parametrize("compare", [weekly_running_activity_count_change, weekly_running_moving_time_change])
@pytest.mark.parametrize("previous_date,current_date", [
    (date(2026, 9, 15), date(2026, 9, 22)),
    (date(2026, 9, 7), date(2026, 9, 21)),
], ids=["not-mondays", "not-consecutive"])
def test_temporal_contract_through_each_public_api(compare, previous_date, current_date) -> None:
    previous = week(previous_date, 1, 61)
    current = week(current_date, 2, 91)
    original = deepcopy((previous, current))
    with pytest.raises(ValueError):
        compare(previous, current)
    assert (previous, current) == original


def test_repeatability_and_no_mutation() -> None:
    previous = week(date(2026, 9, 14), 3, 3601)
    current = week(date(2026, 9, 21), 5, 1801)
    original = deepcopy((previous, current))
    for _ in range(2):
        assert weekly_running_activity_count_change(previous, current) == 2
        assert weekly_running_moving_time_change(previous, current) == -1800
    assert (previous, current) == original
