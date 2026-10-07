"""Acceptance coverage for persistent observed weekly distance increases."""

from copy import deepcopy
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from src.insights.running_distance import detect_persistent_weekly_running_distance_increases
from src.insights.running_distance import detect_persistent_weekly_running_distance_decreases
from src.models.persistent_weekly_running_distance_decrease import (
    PersistentWeeklyRunningDistanceDecrease,
)
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


@pytest.mark.parametrize('distances', [
    [], [40], [40, 30], [40, 30, 20],
    [35, 35, 30, 20], [35, 30, 30, 20], [35, 30, 20, 20],
    [35, 36, 30, 20], [35, 30, 31, 20], [35, 30, 20, 21],
])
def test_decrease_no_pattern(distances):
    assert detect_persistent_weekly_running_distance_decreases(weeks(distances)) == ()


@pytest.mark.parametrize('distances', [
    [35000, 31000, 27000, 22000], [30003, 30002, 30001, 30000],
    [30, 20.000001, 20, 10], [30.000003, 30.000002, 30.000001, 30],
])
def test_decrease_preserves_exact_trends_evidence(distances):
    observations = weeks(distances, counts=[2, 3, 4, 5])
    changes = weekly_running_distance_changes(observations)
    original_changes = deepcopy(changes)
    with patch('src.insights.running_distance.weekly_running_distance_changes',
               return_value=changes) as trend_api:
        results = detect_persistent_weekly_running_distance_decreases(observations)
    trend_api.assert_called_once_with(tuple(observations))
    assert type(results) is tuple and len(results) == 1
    result = results[0]
    assert type(result) is PersistentWeeklyRunningDistanceDecrease
    assert result.start_week_date == observations[0].week_start_date
    assert result.end_week_date == observations[3].week_start_date
    assert result.weekly_distances_meters == tuple(distances)
    assert result.weekly_activity_counts == (2, 3, 4, 5)
    assert result.distance_changes == changes
    assert all(stored is source for stored, source in zip(result.distance_changes, changes))
    assert changes == original_changes


@pytest.mark.parametrize('zero_index', range(4))
def test_decrease_positive_distances_require_positive_counts(zero_index):
    counts = [1, 1, 1, 1]
    counts[zero_index] = 0
    assert detect_persistent_weekly_running_distance_decreases(
        weeks([35, 31, 27, 22], counts=counts),
    ) == ()


@pytest.mark.parametrize('zero_index', range(4))
@pytest.mark.parametrize('zero_count', [0, 1])
def test_decrease_zero_distance_is_ineligible(zero_index, zero_count):
    distances, counts = [20000, 15000, 10000, 5000], [1, 1, 1, 1]
    distances[zero_index] = 0
    counts[zero_index] = zero_count
    assert detect_persistent_weekly_running_distance_decreases(
        weeks(distances, counts=counts),
    ) == ()


@pytest.mark.parametrize('offsets', [
    [0, 2, 3, 4], [0, 1, 3, 4], [0, 1, 2, 4],
    [0, 1, 2, 4, 5], [0, 1, 3, 4, 5], [0, 1, 3, 4, 6, 7],
])
def test_decrease_gaps_and_disconnected_negative_transitions(offsets):
    observations = weeks([100 - 10 * index for index in range(len(offsets))], offsets=offsets)
    changes = weekly_running_distance_changes(observations)
    assert all(change.value < 0 for change in changes)
    if len(offsets) > 4:
        assert len(changes) == 3
    assert detect_persistent_weekly_running_distance_decreases(observations) == ()


@pytest.mark.parametrize('distances', [[50, 40, 30, 20, 10], [60, 50, 40, 30, 20, 10]])
def test_decrease_overlapping_windows(distances):
    observations = weeks(distances)
    results = detect_persistent_weekly_running_distance_decreases(observations)
    assert len(results) == len(observations) - 3
    for index, result in enumerate(results):
        window = observations[index:index + 4]
        assert result.start_week_date == window[0].week_start_date
        assert result.end_week_date == window[-1].week_start_date
        assert result.weekly_distances_meters == tuple(item.running_distance_meters for item in window)
        assert result.distance_changes == weekly_running_distance_changes(window)
    assert results[0].distance_changes[1] is results[1].distance_changes[0]


def test_decrease_multiple_separated_valid_segments():
    observations = weeks([80, 70, 60, 50, 40, 30, 20, 10], offsets=[0, 1, 2, 3, 5, 6, 7, 8])
    results = detect_persistent_weekly_running_distance_decreases(observations)
    assert [(result.start_week_date, result.end_week_date) for result in results] == [
        (observations[0].week_start_date, observations[3].week_start_date),
        (observations[4].week_start_date, observations[7].week_start_date),
    ]


@pytest.mark.parametrize('distances,counts', [
    ([50, 40, 40, 30, 20, 10], [1] * 6),
    ([10, 40, 30, 20, 10], [1] * 5),
    ([0, 40, 30, 20, 10], [0, 1, 1, 1, 1]),
    ([50, 40, 30, 20, 10], [0, 1, 1, 1, 1]),
])
def test_decrease_valid_window_after_interruption(distances, counts):
    observations = weeks(distances, counts=counts)
    result, = detect_persistent_weekly_running_distance_decreases(observations)
    assert result.start_week_date == observations[-4].week_start_date
    assert result.end_week_date == observations[-1].week_start_date


@pytest.mark.parametrize('zero_distance', [False, True])
def test_decrease_retains_ineligible_observations_in_trends_history(zero_distance):
    distances = [40, 0 if zero_distance else 30, 20, 10]
    counts = [1, 0 if not zero_distance else 1, 1, 1]
    observations = weeks(distances, counts=counts)
    with patch('src.insights.running_distance.weekly_running_distance_changes',
               wraps=weekly_running_distance_changes) as trend_api:
        assert detect_persistent_weekly_running_distance_decreases(observations) == ()
    trend_api.assert_called_once_with(tuple(observations))


@pytest.mark.parametrize('container', [list, tuple])
@pytest.mark.parametrize('order', [range(5), [4, 3, 2, 1, 0], [2, 0, 4, 1, 3]])
def test_decrease_order_repeatability_and_input_immutability(container, order):
    observations = weeks([50, 40, 30, 20, 10])
    supplied = container(observations[index] for index in order)
    original = deepcopy(supplied)
    identities = tuple(id(item) for item in supplied)
    structures = tuple(item.running_structure_by_type for item in supplied)
    expected = detect_persistent_weekly_running_distance_decreases(observations)
    assert detect_persistent_weekly_running_distance_decreases(supplied) == expected
    assert detect_persistent_weekly_running_distance_decreases(supplied) == expected
    assert supplied == original
    assert tuple(id(item) for item in supplied) == identities
    assert all(item.running_structure_by_type is structure
               for item, structure in zip(supplied, structures))


@pytest.mark.parametrize('invalid', ['duplicate', 'non_monday', 'non_monday_singleton'])
def test_decrease_validation_errors_propagate_without_mutation(invalid):
    supplied = (weeks([40, 30], offsets=[0, 0]) if invalid == 'duplicate'
                else weeks([40] if invalid.endswith('singleton') else [40, 30, 20, 10],
                           start=date(2026, 6, 2)))
    original = deepcopy(supplied)
    with pytest.raises(ValueError):
        detect_persistent_weekly_running_distance_decreases(supplied)
    assert supplied == original


@pytest.mark.parametrize('start', [date(2026, 12, 21), date(2026, 3, 16), date(2026, 10, 19)])
def test_decrease_calendar_year_and_dst_boundaries(start):
    observations = weeks([40, 30, 20, 10], start=start)
    result, = detect_persistent_weekly_running_distance_decreases(observations)
    assert result.start_week_date == observations[0].week_start_date
    assert result.end_week_date == observations[-1].week_start_date


def test_increase_and_decrease_remain_independent():
    increasing = weeks([10, 20, 30, 40])
    decreasing = weeks([40, 30, 20, 10])
    assert len(detect_persistent_weekly_running_distance_increases(increasing)) == 1
    assert detect_persistent_weekly_running_distance_decreases(increasing) == ()
    assert len(detect_persistent_weekly_running_distance_decreases(decreasing)) == 1
    assert detect_persistent_weekly_running_distance_increases(decreasing) == ()
