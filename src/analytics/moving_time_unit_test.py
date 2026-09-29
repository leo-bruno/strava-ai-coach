"""Unit tests for weekly running moving time."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from src.analytics.moving_time import weekly_running_moving_time
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


@pytest.mark.parametrize("empty", [True, False])
def test_no_matching_runs_returns_int_zero(activity, empty) -> None:
    activities = [] if empty else [
        replace(activity, sport_type="Ride"),
        replace(activity, start_date=activity.start_date - timedelta(days=7)),
        replace(activity, start_date=activity.start_date + timedelta(days=7)),
    ]

    result = weekly_running_moving_time(
        activities,
        reference_datetime=activity.start_date,
        athlete_timezone=ZoneInfo("UTC"),
    )

    assert result == 0
    assert type(result) is int


def test_sums_integer_seconds_without_mutating_inputs_and_is_repeatable(activity) -> None:
    activities = [activity, replace(activity, id=124, moving_time_seconds=337)]
    original = [replace(item) for item in activities]

    for _ in range(2):
        result = weekly_running_moving_time(
            activities,
            reference_datetime=activity.start_date,
            athlete_timezone=ZoneInfo("Europe/Madrid"),
        )
        assert result == 1837
        assert type(result) is int
    assert activities == original


@pytest.mark.parametrize(("distance", "moving_time"), [(5000.0, 0), (0.0, 0), (0.0, 1500)])
def test_preserves_valid_zero_measurements(activity, distance, moving_time) -> None:
    assert weekly_running_moving_time(
        [replace(activity, distance_meters=distance, moving_time_seconds=moving_time)],
        reference_datetime=activity.start_date,
        athlete_timezone=ZoneInfo("UTC"),
    ) == moving_time


@pytest.mark.parametrize("sport_type", ["Ride", "Walk", "TrailRun", "VirtualRun", "run"])
def test_excludes_other_sports(activity, sport_type) -> None:
    assert weekly_running_moving_time(
        [activity, replace(activity, id=124, sport_type=sport_type)],
        reference_datetime=activity.start_date,
        athlete_timezone=ZoneInfo("UTC"),
    ) == 1500


@pytest.mark.parametrize(
    ("boundary", "microseconds", "expected"),
    [("start", -1, 0), ("start", 0, 1500), ("end", -1, 1500), ("end", 0, 0)],
)
def test_local_week_boundaries_and_no_splitting(activity, boundary, microseconds, expected) -> None:
    boundary_datetime = datetime.fromisoformat(
        "2026-09-20T22:00:00+00:00"
        if boundary == "start"
        else "2026-09-27T22:00:00+00:00"
    )

    assert weekly_running_moving_time(
        [replace(activity, start_date=boundary_datetime + timedelta(microseconds=microseconds))],
        reference_datetime=activity.start_date,
        athlete_timezone=ZoneInfo("Europe/Madrid"),
    ) == expected


@pytest.mark.parametrize("empty", [True, False])
def test_rejects_naive_reference_including_empty_input(activity, empty) -> None:
    with pytest.raises(ValueError, match="Reference datetime must be timezone-aware"):
        weekly_running_moving_time(
            [] if empty else [activity],
            reference_datetime=datetime(2026, 9, 23),
            athlete_timezone=ZoneInfo("UTC"),
        )


def test_does_not_deduplicate(activity) -> None:
    assert weekly_running_moving_time(
        [activity, activity],
        reference_datetime=activity.start_date,
        athlete_timezone=ZoneInfo("UTC"),
    ) == 3000
