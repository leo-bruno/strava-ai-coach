"""Public contract for normalization of supplied weekly observations."""

from copy import deepcopy
from dataclasses import replace
from datetime import date

import pytest

from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary, WeeklyAnalysis
from src.trends.history import normalize_weekly_history


def week(start, *, empty=False):
    structure = tuple(
        TrainingTypeSummary(kind, 0 if empty else index,
                            0.0 if empty else index * 1000.25,
                            0 if empty else index * 601)
        for index, kind in enumerate(TrainingType, start=1)
    )
    return WeeklyAnalysis(
        start, sum(item.distance_meters for item in structure),
        sum(item.activity_count for item in structure),
        sum(item.moving_time_seconds for item in structure), structure,
    )


@pytest.mark.parametrize("container", [list, tuple])
def test_empty_history(container):
    result = normalize_weekly_history(container())
    assert type(result) is tuple
    assert result == ()


def test_single_observation():
    observation = week(date(2026, 6, 1))
    result = normalize_weekly_history([observation])
    assert type(result) is tuple
    assert len(result) == 1
    assert result[0] is observation


@pytest.mark.parametrize("container", [list, tuple])
@pytest.mark.parametrize("order", [(0, 1, 2), (2, 1, 0), (1, 0, 2)])
def test_order_identity_fields_and_repeatability(container, order):
    expected = tuple(week(date(2026, 6, day)) for day in (1, 8, 15))
    supplied = container(expected[index] for index in order)
    original = deepcopy(supplied)
    original_ids = tuple(id(item) for item in supplied)

    result = normalize_weekly_history(supplied)

    assert type(result) is tuple
    assert result == expected
    assert all(actual is source for actual, source in zip(result, expected))
    assert all(actual.running_structure_by_type is source.running_structure_by_type
               for actual, source in zip(result, expected))
    assert normalize_weekly_history(supplied) == result
    assert normalize_weekly_history(result) == result
    assert supplied == original
    assert tuple(id(item) for item in supplied) == original_ids


@pytest.mark.parametrize("invalid_date", [date(2026, 6, day) for day in range(2, 8)])
def test_non_monday_rejected_without_mutation(invalid_date):
    supplied = [week(date(2026, 6, 15)), week(invalid_date), week(date(2026, 6, 1))]
    original = deepcopy(supplied)
    original_ids = tuple(id(item) for item in supplied)
    with pytest.raises(ValueError):
        normalize_weekly_history(supplied)
    assert supplied == original
    assert tuple(id(item) for item in supplied) == original_ids


@pytest.mark.parametrize("duplicate_kind", ["same_object", "equivalent", "different"])
def test_any_duplicate_date_rejected_without_mutation(duplicate_kind):
    observation = week(date(2026, 6, 1))
    duplicate = observation
    if duplicate_kind == "equivalent":
        duplicate = deepcopy(observation)
        assert duplicate is not observation
    elif duplicate_kind == "different":
        duplicate = week(observation.week_start_date, empty=True)
    supplied = [week(date(2026, 6, 15)), observation, duplicate]
    original = deepcopy(supplied)
    original_ids = tuple(id(item) for item in supplied)
    with pytest.raises(ValueError):
        normalize_weekly_history(supplied)
    assert supplied == original
    assert tuple(id(item) for item in supplied) == original_ids


@pytest.mark.parametrize("last_date", [date(2026, 6, 22), date(2026, 7, 13)])
def test_gaps_are_preserved(last_date):
    expected = (week(date(2026, 6, 1)), week(date(2026, 6, 8)), week(last_date))
    result = normalize_weekly_history(list(reversed(expected)))
    assert result == expected
    assert all(actual is source for actual, source in zip(result, expected))


def test_existing_zero_observation_is_preserved():
    empty = week(date(2026, 6, 8), empty=True)
    expected = (week(date(2026, 6, 1)), empty, week(date(2026, 6, 15)))
    result = normalize_weekly_history(list(reversed(expected)))
    assert result == expected
    assert result[1] is empty


def test_year_boundary():
    expected = (week(date(2025, 12, 29)), week(date(2026, 1, 5)))
    assert normalize_weekly_history(list(reversed(expected))) == expected


def test_internal_metrics_are_not_validated_or_recalculated():
    observation = replace(week(date(2026, 6, 1)), running_activity_count=0)
    assert normalize_weekly_history([observation])[0] is observation
