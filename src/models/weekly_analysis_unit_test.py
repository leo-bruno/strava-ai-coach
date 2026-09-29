"""Unit tests for the weekly analysis data contract."""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from src.models.weekly_analysis import WeeklyAnalysis


def test_preserves_local_week_date_and_supplied_measurements() -> None:
    analysis = WeeklyAnalysis(
        week_start_date=date(2026, 12, 28),
        running_distance_meters=6250.5,
        running_activity_count=2,
    )

    assert analysis.week_start_date == date(2026, 12, 28)
    assert analysis.running_distance_meters == 6250.5
    assert analysis.running_activity_count == 2


@pytest.mark.parametrize("activity_count", [0, 2])
def test_preserves_zero_distance_with_zero_or_positive_count(activity_count) -> None:
    analysis = WeeklyAnalysis(
        week_start_date=date(2026, 9, 21),
        running_distance_meters=0.0,
        running_activity_count=activity_count,
    )

    assert analysis.running_distance_meters == 0.0
    assert analysis.running_activity_count == activity_count


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("week_start_date", date(2026, 9, 28)),
        ("running_distance_meters", 1000.0),
        ("running_activity_count", 1),
    ],
)
def test_fields_are_immutable(field, value) -> None:
    analysis = WeeklyAnalysis(
        week_start_date=date(2026, 9, 21),
        running_distance_meters=0.0,
        running_activity_count=0,
    )

    with pytest.raises(FrozenInstanceError):
        setattr(analysis, field, value)
