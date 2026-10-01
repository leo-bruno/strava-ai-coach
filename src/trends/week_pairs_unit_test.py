"""Public contract of consecutive weekly pairs."""

from copy import deepcopy
from datetime import date, timedelta

import pytest

from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary, WeeklyAnalysis
from src.trends.history import consecutive_week_pairs
from src.trends.distance import weekly_running_distance_change, weekly_running_distance_percentage_change
from src.trends.activity_count import weekly_running_activity_count_change, weekly_running_activity_count_percentage_change
from src.trends.moving_time import weekly_running_moving_time_change, weekly_running_moving_time_percentage_change


def week(offset, *, empty=False, start=date(2026, 6, 1)):
    count, distance, seconds = (0, 0.0, 0) if empty else (1, 1234.5, 601)
    return WeeklyAnalysis(
        start + timedelta(weeks=offset), distance, count, seconds,
        tuple(TrainingTypeSummary(kind, count, distance, seconds)
              if kind is TrainingType.OTHER else TrainingTypeSummary(kind, 0, 0.0, 0)
              for kind in TrainingType),
    )


@pytest.mark.parametrize("offsets,expected", [
    ([], []), ([0], []), ([0, 1], [(0, 1)]), ([0, 2], []),
    ([0, 1, 2, 3], [(0, 1), (1, 2), (2, 3)]),
    ([0, 1, 2, 4, 5], [(0, 1), (1, 2), (4, 5)]),
    ([0, 1, 3, 6, 7, 10], [(0, 1), (6, 7)]),
])
def test_adjacent_pairs_only(offsets, expected):
    observations = {offset: week(offset) for offset in offsets}
    result = consecutive_week_pairs(list(observations.values()))
    assert type(result) is tuple
    assert result == tuple((observations[left], observations[right]) for left, right in expected)
    for pair, (left, right) in zip(result, expected):
        assert type(pair) is tuple
        assert pair[0] is observations[left]
        assert pair[1] is observations[right]


@pytest.mark.parametrize("container", [list, tuple])
@pytest.mark.parametrize("order", [(0, 1, 2), (2, 1, 0), (1, 0, 2)])
def test_normalization_identity_no_mutation_and_repeatability(container, order):
    observations = [week(offset) for offset in range(3)]
    supplied = container(observations[index] for index in order)
    original = deepcopy(supplied)
    identities = tuple(id(item) for item in supplied)
    expected = ((observations[0], observations[1]), (observations[1], observations[2]))
    result = consecutive_week_pairs(supplied)
    assert result == expected
    assert consecutive_week_pairs(supplied) == result
    for actual, source in zip(result, expected):
        assert all(left is right for left, right in zip(actual, source))
    assert supplied == original
    assert tuple(id(item) for item in supplied) == identities


@pytest.mark.parametrize("invalid", ["non_monday_singleton", "duplicate"])
def test_invalid_history_raises_without_mutation(invalid):
    observation = week(0)
    supplied = ([week(0, start=date(2026, 6, 2))] if invalid == "non_monday_singleton"
                else [week(2), observation, observation])
    original = deepcopy(supplied)
    identities = tuple(id(item) for item in supplied)
    with pytest.raises(ValueError):
        consecutive_week_pairs(supplied)
    assert supplied == original
    assert tuple(id(item) for item in supplied) == identities


@pytest.mark.parametrize("zero_offsets", [(1,), (1, 2)])
def test_zero_observations_participate(zero_offsets):
    observations = [week(offset, empty=offset in zero_offsets) for offset in range(4)]
    result = consecutive_week_pairs(observations)
    assert result == tuple(zip(observations, observations[1:]))


@pytest.mark.parametrize("start", [date(2025, 12, 29), date(2026, 3, 23), date(2026, 10, 19)])
def test_calendar_boundaries(start):
    observations = [week(offset, start=start) for offset in range(2)]
    assert consecutive_week_pairs(observations) == ((observations[0], observations[1]),)


@pytest.mark.parametrize("compare", [
    weekly_running_distance_change, weekly_running_distance_percentage_change,
    weekly_running_activity_count_change, weekly_running_activity_count_percentage_change,
    weekly_running_moving_time_change, weekly_running_moving_time_percentage_change,
])
def test_pairs_accepted_by_existing_comparisons(compare):
    supplied = [week(4), week(1, empty=True), week(0), week(3)]
    original = deepcopy(supplied)
    pairs = consecutive_week_pairs(supplied)
    assert len(pairs) == 2
    for previous, current in pairs:
        compare(previous, current)
    assert supplied == original
