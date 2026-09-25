"""Unit tests for average moving pace."""

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from src.analytics.pace import average_moving_pace, moving_pace
from src.models.activity import Activity


@pytest.fixture
def activity() -> Activity:
    return Activity(
        id=123,
        name="Morning Run",
        sport_type="Run",
        start_date=datetime(2026, 9, 22, 8, tzinfo=timezone.utc),
        distance_meters=5000.0,
        moving_time_seconds=1500,
    )


def test_returns_seconds_per_kilometer(activity) -> None:
    assert average_moving_pace(activity) == 300.0


@pytest.mark.parametrize(
    ("distance_meters", "moving_time_seconds", "expected"),
    [
        (2400.0, 721, 300.4166666666667),
        (1250.5, 400, 319.8720511795282),
    ],
)
def test_preserves_fractional_pace(
    activity, distance_meters, moving_time_seconds, expected
) -> None:
    activity = replace(
        activity,
        distance_meters=distance_meters,
        moving_time_seconds=moving_time_seconds,
    )

    assert average_moving_pace(activity) == pytest.approx(expected)


@pytest.mark.parametrize("moving_time_seconds", [1800, 0])
def test_returns_none_for_zero_distance(activity, moving_time_seconds) -> None:
    activity = replace(
        activity,
        sport_type="WeightTraining",
        distance_meters=0.0,
        moving_time_seconds=moving_time_seconds,
    )

    assert average_moving_pace(activity) is None


def test_returns_zero_for_zero_moving_time_with_positive_distance(activity) -> None:
    activity = replace(activity, moving_time_seconds=0)

    assert average_moving_pace(activity) == 0.0


@pytest.mark.parametrize(
    "distance",
    [-1.0, float("nan"), float("inf"), float("-inf"), None, "5000", True,
     pytest.param(10**400, id="overflow"), 5e-324],
)
def test_invalid_distance_has_undefined_pace(activity, distance) -> None:
    assert moving_pace(distance, 1500) is None
    assert average_moving_pace(replace(activity, distance_meters=distance)) is None


@pytest.mark.parametrize(
    "moving_time", [-1, None, "1500", True, 1.5, float("nan"), float("inf"),
                    pytest.param(10**400, id="overflow")],
)
def test_invalid_time_has_undefined_pace(moving_time) -> None:
    assert moving_pace(1000.0, moving_time) is None


@pytest.mark.parametrize(
    ("distance", "moving_time", "expected"),
    [(400.0, 96, 240.0), (1000.0, 0, 0.0), (0.0, 120, None)],
)
def test_shared_pace_for_lap_measurements(distance, moving_time, expected) -> None:
    assert moving_pace(distance, moving_time) == expected
