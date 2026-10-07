"""Acceptance coverage for count-based observed running episodes."""

from copy import deepcopy
from dataclasses import replace
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from src.insights.running_activity import detect_observed_running_after_zero_run_weeks
from src.models.observed_running_after_zero_run_weeks import ObservedRunningAfterZeroRunWeeks
from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary, WeeklyAnalysis
from src.trends.history import consecutive_week_pairs


def weeks(counts, *, distances=None, offsets=None, start=date(2026, 6, 1)):
    if distances is None:
        distances = [1234.56789 if count else 0.0 for count in counts]
    if offsets is None:
        offsets = range(len(counts))
    return [WeeklyAnalysis(
        start + timedelta(weeks=offset), distance, count, 600 if count else 0,
        tuple(TrainingTypeSummary(kind, count, distance, 600 if count else 0)
              if kind is TrainingType.OTHER else TrainingTypeSummary(kind, 0, 0.0, 0)
              for kind in TrainingType),
    ) for offset, count, distance in zip(offsets, counts, distances)]


@pytest.mark.parametrize('zero_count', [2, 3, 4, 10])
def test_maximal_episode_preserves_exact_evidence(zero_count):
    observations = weeks([0] * zero_count + [3])
    results = detect_observed_running_after_zero_run_weeks(observations)
    assert type(results) is tuple
    assert results == (ObservedRunningAfterZeroRunWeeks(
        observations[0].week_start_date, zero_count,
        observations[-1].week_start_date, 3, observations[-1].running_distance_meters,
    ),)
    assert type(results[0]) is ObservedRunningAfterZeroRunWeeks


@pytest.mark.parametrize('counts', [
    [], [0], [1], [0, 0], [0, 1], [1, 0, 1],
    [0, 0, 0], [1, 0, 0], [1, 2, 3],
])
def test_empty_short_single_zero_and_trailing_zero_histories(counts):
    assert detect_observed_running_after_zero_run_weeks(weeks(counts)) == ()


@pytest.mark.parametrize('counts,start_index,zero_count,running_index', [
    ([0, 0, 2, 3, 4], 0, 2, 2),
    ([3, 0, 0, 2], 1, 2, 3),
    ([3, 0, 0, 0, 2], 1, 3, 4),
    ([0, 0, 2, 0, 0, 0], 0, 2, 2),
])
def test_episode_boundaries_and_no_repeated_result(counts, start_index, zero_count, running_index):
    observations = weeks(counts)
    result, = detect_observed_running_after_zero_run_weeks(observations)
    assert result.first_zero_week_date == observations[start_index].week_start_date
    assert result.observed_zero_week_count == zero_count
    assert result.running_week_date == observations[running_index].week_start_date


def test_multiple_separate_episodes_in_running_week_order():
    observations = weeks([0, 0, 2, 0, 0, 0, 4])
    results = detect_observed_running_after_zero_run_weeks(observations)
    assert results == (
        ObservedRunningAfterZeroRunWeeks(observations[0].week_start_date, 2,
                                        observations[2].week_start_date, 2, 1234.56789),
        ObservedRunningAfterZeroRunWeeks(observations[3].week_start_date, 3,
                                        observations[6].week_start_date, 4, 1234.56789),
    )


@pytest.mark.parametrize('counts,offsets', [
    ([0, 0, 1], [0, 2, 3]),
    ([0, 0, 1], [0, 1, 3]),
    ([0, 0, 0, 1], [0, 1, 3, 4]),
    ([0, 0, 0, 1], [0, 2, 3, 5]),
    ([0, 0, 0, 1], [0, 1, 3, 5]),
    ([0, 0, 1, 1], [0, 1, 3, 4]),
    ([0, 0, 0, 1], [0, 2, 4, 6]),
])
def test_gaps_and_disconnected_pair_chains_break_episode(counts, offsets):
    assert detect_observed_running_after_zero_run_weeks(weeks(counts, offsets=offsets)) == ()


@pytest.mark.parametrize('counts,offsets,first_index,zero_count', [
    ([0, 0, 0, 1], [0, 2, 3, 4], 1, 2),
    ([0, 0, 0, 0, 1], [0, 1, 3, 4, 5], 2, 2),
    ([0, 0, 0, 0, 0, 1], [0, 1, 3, 4, 5, 6], 2, 3),
])
def test_new_qualifying_episode_after_gap(counts, offsets, first_index, zero_count):
    observations = weeks(counts, offsets=offsets)
    result, = detect_observed_running_after_zero_run_weeks(observations)
    assert result.first_zero_week_date == observations[first_index].week_start_date
    assert result.observed_zero_week_count == zero_count
    assert result.running_week_date == observations[-1].week_start_date


@pytest.mark.parametrize('running_distance', [0.0, 0.000001, 1234.56789])
def test_running_distance_does_not_determine_eligibility(running_distance):
    observations = weeks([0, 0, 2], distances=[0.0, 0.0, running_distance])
    result, = detect_observed_running_after_zero_run_weeks(observations)
    assert result.running_week_activity_count == 2
    assert result.running_week_distance_meters == running_distance


def test_positive_count_zero_distance_terminates_zero_sequence():
    observations = weeks([0, 0, 1, 0, 2], distances=[0.0, 0.0, 0.0, 0.0, 50.0])
    result, = detect_observed_running_after_zero_run_weeks(observations)
    assert result.observed_zero_week_count == 2
    assert result.running_week_date == observations[2].week_start_date
    assert result.running_week_distance_meters == 0.0


def test_count_zero_distance_positive_follows_count_only_rule_without_correction():
    observations = weeks([0, 0, 2], distances=[99.5, 50.25, 0.0])
    original = deepcopy(observations)
    result, = detect_observed_running_after_zero_run_weeks(observations)
    assert result.first_zero_week_date == observations[0].week_start_date
    assert result.observed_zero_week_count == 2
    assert result.running_week_distance_meters == 0.0
    assert observations == original


def test_reuses_history_api_with_all_supplied_observations():
    observations = weeks([0, 0, 1], distances=[50.0, 0.0, 0.0])
    supplied = list(reversed(observations))
    with patch('src.insights.running_activity.consecutive_week_pairs',
               wraps=consecutive_week_pairs) as history_api:
        result, = detect_observed_running_after_zero_run_weeks(supplied)
    history_api.assert_called_once_with(supplied)
    assert result.first_zero_week_date == observations[0].week_start_date


@pytest.mark.parametrize('container', [list, tuple])
@pytest.mark.parametrize('order', [range(7), [6, 5, 4, 3, 2, 1, 0], [3, 0, 6, 2, 4, 1, 5]])
def test_order_repeatability_and_input_immutability(container, order):
    observations = weeks([0, 0, 1, 0, 0, 0, 2])
    supplied = container(observations[index] for index in order)
    original = deepcopy(supplied)
    identities = tuple(id(item) for item in supplied)
    structures = tuple(item.running_structure_by_type for item in supplied)
    expected = detect_observed_running_after_zero_run_weeks(observations)
    assert detect_observed_running_after_zero_run_weeks(supplied) == expected
    assert detect_observed_running_after_zero_run_weeks(supplied) == expected
    assert supplied == original
    assert tuple(id(item) for item in supplied) == identities
    assert all(item.running_structure_by_type is structure
               for item, structure in zip(supplied, structures))


@pytest.mark.parametrize('duplicate_kind', ['identical_object', 'equivalent', 'different'])
def test_duplicate_mondays_propagate_validation_error(duplicate_kind):
    observations = weeks([0, 0, 1])
    duplicate = observations[0]
    if duplicate_kind == 'equivalent':
        duplicate = deepcopy(duplicate)
    elif duplicate_kind == 'different':
        duplicate = replace(duplicate, running_activity_count=3)
    supplied = observations + [duplicate]
    original = deepcopy(supplied)
    with pytest.raises(ValueError, match='Duplicate week_start_date'):
        detect_observed_running_after_zero_run_weeks(supplied)
    assert supplied == original


@pytest.mark.parametrize('counts', [[0], [0, 0, 1]])
def test_non_monday_validation_including_singleton(counts):
    supplied = weeks(counts, start=date(2026, 6, 2))
    original = deepcopy(supplied)
    with pytest.raises(ValueError, match='Monday'):
        detect_observed_running_after_zero_run_weeks(supplied)
    assert supplied == original


@pytest.mark.parametrize('start', [date(2026, 12, 21), date(2026, 3, 16), date(2026, 10, 19)])
def test_year_and_dst_calendar_boundaries(start):
    observations = weeks([0, 0, 0, 1], start=start)
    result, = detect_observed_running_after_zero_run_weeks(observations)
    assert result.first_zero_week_date == observations[0].week_start_date
    assert result.observed_zero_week_count == 3
    assert result.running_week_date == observations[-1].week_start_date
