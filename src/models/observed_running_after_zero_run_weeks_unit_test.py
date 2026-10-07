"""Immutable evidence contract for observed running after zero-Run weeks."""

from dataclasses import FrozenInstanceError, fields
from datetime import date
from typing import get_type_hints

import pytest

from src.models.observed_running_after_zero_run_weeks import (
    ObservedRunningAfterZeroRunWeeks,
)


def evidence():
    return ObservedRunningAfterZeroRunWeeks(
        date(2026, 6, 1), 3, date(2026, 6, 22), 2, 1234.56789,
    )


def test_exact_fields_types_and_evidence():
    result = evidence()
    assert result.first_zero_week_date == date(2026, 6, 1)
    assert result.observed_zero_week_count == 3
    assert result.running_week_date == date(2026, 6, 22)
    assert result.running_week_activity_count == 2
    assert result.running_week_distance_meters == 1234.56789
    expected = {
        'first_zero_week_date': date,
        'observed_zero_week_count': int,
        'running_week_date': date,
        'running_week_activity_count': int,
        'running_week_distance_meters': float,
    }
    assert [field.name for field in fields(result)] == list(expected)
    assert get_type_hints(ObservedRunningAfterZeroRunWeeks) == expected


@pytest.mark.parametrize('field', [
    'first_zero_week_date', 'observed_zero_week_count', 'running_week_date',
    'running_week_activity_count', 'running_week_distance_meters',
])
def test_fields_are_frozen(field):
    with pytest.raises(FrozenInstanceError):
        setattr(evidence(), field, None)


def test_model_does_not_calculate_or_validate_supplied_evidence():
    result = ObservedRunningAfterZeroRunWeeks(
        date(2026, 6, 2), 1, date(2026, 6, 2), 0, 0.0,
    )
    assert result.first_zero_week_date == result.running_week_date == date(2026, 6, 2)
    assert result.observed_zero_week_count == 1
    assert result.running_week_activity_count == 0
    assert result.running_week_distance_meters == 0.0
