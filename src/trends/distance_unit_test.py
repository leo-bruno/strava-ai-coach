"""Public contract for absolute weekly running distance change."""

from copy import deepcopy
from dataclasses import replace
from datetime import date

import pytest

from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary, WeeklyAnalysis
from src.trends.distance import weekly_running_distance_change


def week(start: date, distance: float) -> WeeklyAnalysis:
    return WeeklyAnalysis(
        week_start_date=start,
        running_distance_meters=distance,
        running_activity_count=1,
        running_moving_time_seconds=1500,
        running_structure_by_type=tuple(
            TrainingTypeSummary(kind, 1, distance, 1500)
            if kind is TrainingType.OTHER else TrainingTypeSummary(kind, 0, 0.0, 0)
            for kind in TrainingType
        ),
    )


@pytest.mark.parametrize("previous_distance,current_distance,expected", [
    (30000.0, 33000.0, 3000.0),
    (33000.0, 30000.0, -3000.0),
    (30000.0, 30000.0, 0.0),
    (0.0, 10000.0, 10000.0),
    (10000.0, 0.0, -10000.0),
    (0.0, 0.0, 0.0),
])
def test_change_in_meters(previous_distance, current_distance, expected) -> None:
    result = weekly_running_distance_change(
        previous=week(date(2026, 9, 14), previous_distance),
        current=week(date(2026, 9, 21), current_distance),
    )
    assert type(result) is float
    assert result == expected


def test_preserves_fractional_meters_without_rounding() -> None:
    result = weekly_running_distance_change(
        week(date(2026, 9, 14), 1234.56789),
        week(date(2026, 9, 21), 1234.56812),
    )
    assert type(result) is float
    assert result == pytest.approx(0.00023, rel=1e-12, abs=1e-12)


@pytest.mark.parametrize("previous_date,current_date", [
    (date(2026, 9, 21), date(2026, 9, 21)),
    (date(2026, 9, 21), date(2026, 9, 14)),
    (date(2026, 9, 7), date(2026, 9, 21)),
    (date(2026, 8, 31), date(2026, 9, 21)),
    (date(2026, 9, 15), date(2026, 9, 21)),
    (date(2026, 9, 14), date(2026, 9, 22)),
    (date(2026, 9, 15), date(2026, 9, 22)),
], ids=["same-week", "reversed", "one-missing-week", "two-missing-weeks",
        "previous-not-monday", "current-not-monday", "both-tuesdays"])
def test_rejects_invalid_week_dates(previous_date, current_date) -> None:
    with pytest.raises(ValueError):
        weekly_running_distance_change(week(previous_date, 10.0), week(current_date, 20.0))


@pytest.mark.parametrize("previous_date,current_date", [
    (date(2026, 12, 28), date(2027, 1, 4)),
    (date(2026, 3, 23), date(2026, 3, 30)),
    (date(2026, 10, 19), date(2026, 10, 26)),
], ids=["new-year", "spring-dst-calendar", "autumn-dst-calendar"])
def test_consecutive_calendar_weeks(previous_date, current_date) -> None:
    assert weekly_running_distance_change(
        week(previous_date, 10.0), week(current_date, 20.0),
    ) == 10.0


def test_repeatable_without_mutating_either_observation() -> None:
    previous = week(date(2026, 9, 14), 30000.0)
    current = week(date(2026, 9, 21), 33000.0)
    original = deepcopy((previous, current))
    for _ in range(2):
        assert weekly_running_distance_change(previous, current) == 3000.0
    assert (previous, current) == original

    invalid = replace(current, week_start_date=previous.week_start_date)
    invalid_original = deepcopy(invalid)
    with pytest.raises(ValueError):
        weekly_running_distance_change(previous, invalid)
    assert previous == original[0]
    assert invalid == invalid_original
