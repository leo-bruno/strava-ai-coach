"""Contract of the immutable dated percentage result."""

from dataclasses import FrozenInstanceError, fields
from datetime import date
from typing import get_type_hints

import pytest

from src.models.weekly_running_activity_count_percentage_change import WeeklyRunningActivityCountPercentageChange


@pytest.mark.parametrize('value', [12.3456789, 0.0, -100.0, None])
def test_fields_types_and_equality(value):
    previous, current = date(2026, 6, 1), date(2026, 6, 8)
    result = WeeklyRunningActivityCountPercentageChange(previous, current, value)
    assert result.previous_week_start_date == previous
    assert result.current_week_start_date == current
    assert result.value == value
    assert result.value is None or type(result.value) is float
    assert result == WeeklyRunningActivityCountPercentageChange(previous, current, value)
    assert result != WeeklyRunningActivityCountPercentageChange(previous, current, 42.0)
    assert [field.name for field in fields(result)] == [
        'previous_week_start_date', 'current_week_start_date', 'value',
    ]
    assert get_type_hints(WeeklyRunningActivityCountPercentageChange) == {
        'previous_week_start_date': date, 'current_week_start_date': date, 'value': float | None,
    }


@pytest.mark.parametrize('field,value', [
    ('previous_week_start_date', date(2026, 6, 15)),
    ('current_week_start_date', date(2026, 6, 22)), ('value', 1.0),
])
def test_immutable(field, value):
    result = WeeklyRunningActivityCountPercentageChange(date(2026, 6, 1), date(2026, 6, 8), None)
    with pytest.raises(FrozenInstanceError):
        setattr(result, field, value)


def test_model_preserves_supplied_fields_without_validation_or_calculation():
    previous, current = date(2026, 6, 9), date(2026, 6, 2)
    result = WeeklyRunningActivityCountPercentageChange(previous, current, 12.3456789)
    assert result.previous_week_start_date == previous
    assert result.current_week_start_date == current
    assert result.value == 12.3456789
