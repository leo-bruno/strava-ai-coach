"""Acceptance coverage for persistent observed weekly distance increases."""

from copy import deepcopy
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from src.insights.running_distance import detect_persistent_weekly_running_distance_increases
from src.models.persistent_weekly_running_distance_increase import (
    PersistentWeeklyRunningDistanceIncrease,
)
from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary, WeeklyAnalysis
from src.trends.distance import weekly_running_distance_changes


def weeks(distances, *, offsets=None, counts=None, start=date(2026, 6, 1)):
    if offsets is None:
        offsets = range(len(distances))
    if counts is None:
        counts = [1 if distance > 0 else 0 for distance in distances]
    return [WeeklyAnalysis(
        start + timedelta(weeks=offset), float(distance), count, 600 if count else 0,
        tuple(TrainingTypeSummary(kind, count, float(distance), 600 if count else 0)
              if kind is TrainingType.OTHER else TrainingTypeSummary(kind, 0, 0.0, 0)
              for kind in TrainingType),
    ) for offset, distance, count in zip(offsets, distances, counts)]


@pytest.mark.parametrize('distances', [
    [], [10], [10, 20], [10, 20, 30],
    [10, 20, 30, 25], [10, 20, 20, 30], [10, 20, 15, 30],
    [0, 10, 20, 30], [10, 0, 20, 30], [10, 20, 0, 30], [10, 20, 30, 0],
])
def test_no_pattern(distances):
    assert detect_persistent_weekly_running_distance_increases(weeks(distances)) == ()


@pytest.mark.parametrize('distances', [
    [10, 20, 30, 40], [30000, 30001, 30002, 30003],
    [10, 20, 20.000001, 30], [30, 30.000001, 30.000002, 30.000003],
])
def test_four_increases_preserve_exact_evidence(distances):
    observations = weeks(distances, counts=[2, 3, 4, 5])
    changes = weekly_running_distance_changes(observations)
    original_changes = deepcopy(changes)
    with patch('src.insights.running_distance.weekly_running_distance_changes',
               wraps=lambda supplied: changes) as trend_api:
        results = detect_persistent_weekly_running_distance_increases(observations)
    trend_api.assert_called_once_with(tuple(observations))
    assert type(results) is tuple and len(results) == 1
    result = results[0]
    assert type(result) is PersistentWeeklyRunningDistanceIncrease
    assert result.start_week_date == observations[0].week_start_date
    assert result.end_week_date == observations[3].week_start_date
    assert result.weekly_distances_meters == tuple(item.running_distance_meters for item in observations)
    assert result.weekly_activity_counts == (2, 3, 4, 5)
    assert result.distance_changes == changes
    assert all(stored is original for stored, original in zip(result.distance_changes, changes))
    assert changes == original_changes


@pytest.mark.parametrize('zero_index', range(4))
def test_positive_distances_require_positive_counts(zero_index):
    counts = [1, 1, 1, 1]
    counts[zero_index] = 0
    assert detect_persistent_weekly_running_distance_increases(
        weeks([10, 20, 30, 40], counts=counts),
    ) == ()


def test_zero_distance_with_positive_count():
    assert detect_persistent_weekly_running_distance_increases(
        weeks([0, 10, 20, 30], counts=[1, 1, 1, 1]),
    ) == ()


@pytest.mark.parametrize('offsets', [
    [0, 2, 3, 4], [0, 1, 3, 4], [0, 1, 2, 4],
    [0, 1, 2, 4, 5], [0, 1, 3, 4, 5],
])
def test_gaps_and_disconnected_positive_changes_do_not_form_pattern(offsets):
    observations = weeks([10 * (index + 1) for index in range(len(offsets))], offsets=offsets)
    assert all(change.value > 0 for change in weekly_running_distance_changes(observations))
    assert detect_persistent_weekly_running_distance_increases(observations) == ()


def test_overlapping_windows():
    observations = weeks([10, 20, 30, 40, 50])
    results = detect_persistent_weekly_running_distance_increases(observations)
    assert len(results) == 2
    for index, result in enumerate(results):
        window = observations[index:index + 4]
        assert result.start_week_date == window[0].week_start_date
        assert result.end_week_date == window[-1].week_start_date
        assert result.weekly_distances_meters == tuple(item.running_distance_meters for item in window)
        assert result.distance_changes == weekly_running_distance_changes(window)


def test_two_independent_sequences():
    observations = weeks([10, 20, 30, 40, 50, 60, 70, 80], offsets=[0, 1, 2, 3, 5, 6, 7, 8])
    results = detect_persistent_weekly_running_distance_increases(observations)
    assert len(results) == 2
    assert [(result.start_week_date, result.end_week_date) for result in results] == [
        (observations[0].week_start_date, observations[3].week_start_date),
        (observations[4].week_start_date, observations[7].week_start_date),
    ]


@pytest.mark.parametrize('container', [list, tuple])
@pytest.mark.parametrize('order', [range(5), [4, 3, 2, 1, 0], [2, 0, 4, 1, 3]])
def test_order_repeatability_and_no_mutation(container, order):
    observations = weeks([10, 20, 30, 40, 50])
    supplied = container(observations[index] for index in order)
    original = deepcopy(supplied)
    identities = tuple(id(item) for item in supplied)
    structures = tuple(item.running_structure_by_type for item in supplied)
    expected = detect_persistent_weekly_running_distance_increases(observations)
    assert detect_persistent_weekly_running_distance_increases(supplied) == expected
    assert detect_persistent_weekly_running_distance_increases(supplied) == expected
    assert supplied == original
    assert tuple(id(item) for item in supplied) == identities
    assert all(item.running_structure_by_type is structure
               for item, structure in zip(supplied, structures))


@pytest.mark.parametrize('invalid', ['duplicate', 'non_monday', 'non_monday_singleton'])
def test_errors_propagate_without_mutation(invalid):
    if invalid == 'duplicate':
        supplied = weeks([10, 20], offsets=[0, 0])
    else:
        supplied = weeks([10] if invalid.endswith('singleton') else [10, 20, 30, 40],
                         start=date(2026, 6, 2))
    original = deepcopy(supplied)
    with pytest.raises(ValueError):
        detect_persistent_weekly_running_distance_increases(supplied)
    assert supplied == original


@pytest.mark.parametrize('start', [date(2026, 12, 21), date(2026, 10, 19)])
def test_calendar_year_and_dst_boundaries(start):
    observations = weeks([10, 20, 30, 40], start=start)
    result, = detect_persistent_weekly_running_distance_increases(observations)
    assert result.start_week_date == observations[0].week_start_date
    assert result.end_week_date == observations[-1].week_start_date


@pytest.mark.parametrize('distances', [[10, 20, 20, 30, 40, 50], [50, 10, 20, 30, 40]])
def test_break_followed_by_valid_window(distances):
    observations = weeks(distances)
    result, = detect_persistent_weekly_running_distance_increases(observations)
    assert result.start_week_date == observations[-4].week_start_date
    assert result.end_week_date == observations[-1].week_start_date
