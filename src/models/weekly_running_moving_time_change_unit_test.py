"""Data contract of dated absolute moving time changes."""

from dataclasses import FrozenInstanceError, fields
from datetime import date
from typing import get_type_hints

import pytest

from src.models.weekly_running_moving_time_change import WeeklyRunningMovingTimeChange


def test_construction_fields_and_equality():
    previous, current = date(2026, 6, 1), date(2026, 6, 8)
    result = WeeklyRunningMovingTimeChange(previous, current, -123)
    assert result.previous_week_start_date == previous
    assert result.current_week_start_date == current
    assert result.value == -123
    assert type(result.value) is int
    assert result == WeeklyRunningMovingTimeChange(previous, current, -123)
    assert result != WeeklyRunningMovingTimeChange(previous, current, 0)
    assert [field.name for field in fields(result)] == [
        'previous_week_start_date', 'current_week_start_date', 'value',
    ]
    assert get_type_hints(WeeklyRunningMovingTimeChange) == {
        'previous_week_start_date': date, 'current_week_start_date': date, 'value': int,
    }


@pytest.mark.parametrize('field,value', [
    ('previous_week_start_date', date(2026, 6, 15)),
    ('current_week_start_date', date(2026, 6, 22)), ('value', 1),
])
def test_immutable(field, value):
    result = WeeklyRunningMovingTimeChange(date(2026, 6, 1), date(2026, 6, 8), 0)
    with pytest.raises(FrozenInstanceError):
        setattr(result, field, value)


def test_model_preserves_fields_without_date_validation_or_numeric_conversion():
    previous, current = date(2026, 6, 9), date(2026, 6, 2)
    value = 2**53 + 1
    result = WeeklyRunningMovingTimeChange(previous, current, value)
    assert result.previous_week_start_date == previous
    assert result.current_week_start_date == current
    assert result.value == value
    assert type(result.value) is int
