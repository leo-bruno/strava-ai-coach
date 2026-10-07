"""Immutable evidence contract of the persistent distance decrease."""

from dataclasses import FrozenInstanceError, fields
from datetime import date
from typing import get_type_hints

import pytest

from src.models.persistent_weekly_running_distance_decrease import (
    PersistentWeeklyRunningDistanceDecrease,
)
from src.models.weekly_running_distance_change import WeeklyRunningDistanceChange


def evidence():
    dates = (date(2026, 6, 22), date(2026, 6, 29),
             date(2026, 7, 6), date(2026, 7, 13))
    distances = (36571.5, 35607.5, 31246.6, 10057.0)
    counts = (2, 4, 4, 4)
    changes = tuple(WeeklyRunningDistanceChange(left, right, value)
                    for left, right, value in zip(dates, dates[1:],
                                                 (-964.0, -4360.9000000000015, -21189.6)))
    return PersistentWeeklyRunningDistanceDecrease(
        dates[0], dates[-1], distances, counts, changes,
    ), distances, counts, changes


def test_construction_preserves_exact_evidence_and_fields():
    result, distances, counts, changes = evidence()
    assert result.start_week_date == date(2026, 6, 22)
    assert result.end_week_date == date(2026, 7, 13)
    assert result.weekly_distances_meters is distances
    assert result.weekly_activity_counts is counts
    assert result.distance_changes is changes
    assert all(stored is supplied for stored, supplied in zip(result.distance_changes, changes))
    assert all(type(value) is tuple for value in (distances, counts, changes))
    assert [field.name for field in fields(result)] == [
        'start_week_date', 'end_week_date', 'weekly_distances_meters',
        'weekly_activity_counts', 'distance_changes',
    ]
    assert get_type_hints(PersistentWeeklyRunningDistanceDecrease) == {
        'start_week_date': date,
        'end_week_date': date,
        'weekly_distances_meters': tuple[float, float, float, float],
        'weekly_activity_counts': tuple[int, int, int, int],
        'distance_changes': tuple[WeeklyRunningDistanceChange,
                                  WeeklyRunningDistanceChange,
                                  WeeklyRunningDistanceChange],
    }


@pytest.mark.parametrize('field', [
    'start_week_date', 'end_week_date', 'weekly_distances_meters',
    'weekly_activity_counts', 'distance_changes',
])
def test_fields_are_frozen(field):
    result, _, _, _ = evidence()
    with pytest.raises(FrozenInstanceError):
        setattr(result, field, None)


def test_nested_evidence_is_immutable():
    result, _, _, _ = evidence()
    with pytest.raises(TypeError):
        result.weekly_distances_meters[0] = 0.0
    with pytest.raises(TypeError):
        result.weekly_activity_counts[0] = 0
    with pytest.raises(TypeError):
        result.distance_changes[0] = result.distance_changes[1]
    with pytest.raises(FrozenInstanceError):
        result.distance_changes[0].value = 0.0
