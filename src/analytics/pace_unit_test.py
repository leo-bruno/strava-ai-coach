"""Unit tests for average moving pace."""

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from src.analytics.pace import average_moving_pace
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
