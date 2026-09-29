"""Unit tests for the weekly analysis data contract."""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary, WeeklyAnalysis


def structure_with_other_count(count, distance=0.0, moving_time=0):
    return tuple(
        TrainingTypeSummary(
            kind,
            count if kind is TrainingType.OTHER else 0,
            distance if kind is TrainingType.OTHER else 0.0,
            moving_time if kind is TrainingType.OTHER else 0,
        )
        for kind in TrainingType
    )


def test_preserves_local_week_date_and_supplied_measurements() -> None:
    analysis = WeeklyAnalysis(
        week_start_date=date(2026, 12, 28),
        running_distance_meters=6250.5,
        running_activity_count=2,
        running_moving_time_seconds=1837,
        running_structure_by_type=structure_with_other_count(2, 6250.5, 1837),
    )

    assert analysis.week_start_date == date(2026, 12, 28)
    assert analysis.running_distance_meters == 6250.5
    assert analysis.running_activity_count == 2
    assert analysis.running_moving_time_seconds == 1837
    assert analysis.running_structure_by_type == structure_with_other_count(2, 6250.5, 1837)


@pytest.mark.parametrize(("activity_count", "moving_time"), [(0, 0), (2, 0), (2, 1500)])
def test_preserves_zero_distance_with_zero_or_positive_count(activity_count, moving_time) -> None:
    analysis = WeeklyAnalysis(
        week_start_date=date(2026, 9, 21),
        running_distance_meters=0.0,
        running_activity_count=activity_count,
        running_moving_time_seconds=moving_time,
        running_structure_by_type=structure_with_other_count(activity_count, moving_time=moving_time),
    )

    assert analysis.running_distance_meters == 0.0
    assert analysis.running_activity_count == activity_count
    assert analysis.running_moving_time_seconds == moving_time
    assert analysis.running_structure_by_type[-1].moving_time_seconds == moving_time


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("week_start_date", date(2026, 9, 28)),
        ("running_distance_meters", 1000.0),
        ("running_activity_count", 1),
        ("running_moving_time_seconds", 1500),
        ("running_structure_by_type", structure_with_other_count(1)),
    ],
)
def test_fields_are_immutable(field, value) -> None:
    analysis = WeeklyAnalysis(
        week_start_date=date(2026, 9, 21),
        running_distance_meters=0.0,
        running_activity_count=0,
        running_moving_time_seconds=0,
        running_structure_by_type=structure_with_other_count(0),
    )

    with pytest.raises(FrozenInstanceError):
        setattr(analysis, field, value)


@pytest.mark.parametrize("field,value", [("training_type", TrainingType.EASY), ("activity_count", 3), ("distance_meters", 1250.25), ("moving_time_seconds", 91)])
def test_category_summaries_are_immutable(field, value) -> None:
    summary = TrainingTypeSummary(TrainingType.OTHER, 2, 6250.5, 1837)
    with pytest.raises(FrozenInstanceError):
        setattr(summary, field, value)


def test_structure_entries_cannot_be_replaced() -> None:
    analysis = WeeklyAnalysis(date(2026, 9, 21), 0.0, 0, 0, structure_with_other_count(0))
    with pytest.raises(TypeError):
        analysis.running_structure_by_type[0] = TrainingTypeSummary(TrainingType.EASY, 1, 0.0, 0)
