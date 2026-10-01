"""Data contract of dated absolute activity count changes."""

from dataclasses import FrozenInstanceError, fields
from datetime import date
from typing import get_type_hints

import pytest

from src.models.weekly_running_activity_count_change import WeeklyRunningActivityCountChange


def test_construction_fields_and_equality():
    previous, current = date(2026, 6, 1), date(2026, 6, 8)
    result = WeeklyRunningActivityCountChange(previous, current, -123)
    assert result.previous_week_start_date == previous
    assert result.current_week_start_date == current
    assert result.value == -123
    assert type(result.value) is int
    assert result == WeeklyRunningActivityCountChange(previous, current, -123)
    assert result != WeeklyRunningActivityCountChange(previous, current, 0)
    assert [field.name for field in fields(result)] == [
        'previous_week_start_date', 'current_week_start_date', 'value',
    ]
    assert get_type_hints(WeeklyRunningActivityCountChange) == {
        'previous_week_start_date': date, 'current_week_start_date': date, 'value': int,
    }


@pytest.mark.parametrize('field,value', [
    ('previous_week_start_date', date(2026, 6, 15)),
    ('current_week_start_date', date(2026, 6, 22)), ('value', 1),
])
def test_immutable(field, value):
    result = WeeklyRunningActivityCountChange(date(2026, 6, 1), date(2026, 6, 8), 0)
    with pytest.raises(FrozenInstanceError):
        setattr(result, field, value)
