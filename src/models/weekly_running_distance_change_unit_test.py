"""Data contract of dated absolute distance changes."""

from dataclasses import FrozenInstanceError, fields
from datetime import date
from typing import get_type_hints

import pytest

from src.models.weekly_running_distance_change import WeeklyRunningDistanceChange


def test_construction_fields_and_equality():
    previous, current = date(2026, 6, 1), date(2026, 6, 8)
    result = WeeklyRunningDistanceChange(previous, current, -123.456789)
    assert result.previous_week_start_date == previous
    assert result.current_week_start_date == current
    assert result.value == -123.456789
    assert type(result.value) is float
    assert result == WeeklyRunningDistanceChange(previous, current, -123.456789)
    assert result != WeeklyRunningDistanceChange(previous, current, 0.0)
    assert [field.name for field in fields(result)] == [
        'previous_week_start_date', 'current_week_start_date', 'value',
    ]
    assert get_type_hints(WeeklyRunningDistanceChange) == {
        'previous_week_start_date': date, 'current_week_start_date': date, 'value': float,
    }


@pytest.mark.parametrize('field,value', [
    ('previous_week_start_date', date(2026, 6, 15)),
    ('current_week_start_date', date(2026, 6, 22)), ('value', 1.0),
])
def test_immutable(field, value):
    result = WeeklyRunningDistanceChange(date(2026, 6, 1), date(2026, 6, 8), 0.0)
    with pytest.raises(FrozenInstanceError):
        setattr(result, field, value)
