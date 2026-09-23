"""Unit tests for weekly running activity count."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from src.analytics.activity_count import weekly_running_activity_count
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


def test_empty_input_returns_int_zero(activity) -> None:
    result = weekly_running_activity_count(
        [],
        reference_datetime=activity.start_date,
        athlete_timezone=ZoneInfo("UTC"),
    )

    assert result == 0
    assert type(result) is int


def test_counts_runs_including_zero_distance_and_time(activity) -> None:
    activities = [
        activity,
        replace(activity, id=124, distance_meters=1250.5),
        replace(activity, id=125, distance_meters=0.0, moving_time_seconds=0),
    ]

    result = weekly_running_activity_count(
        activities,
        reference_datetime=activity.start_date,
        athlete_timezone=ZoneInfo("UTC"),
    )

    assert result == 3
    assert type(result) is int


@pytest.mark.parametrize("sport_type", ["Ride", "Walk", "TrailRun", "run"])
def test_excludes_other_sports(activity, sport_type) -> None:
    other_activity = replace(activity, id=124, sport_type=sport_type)

    assert weekly_running_activity_count(
        [activity, other_activity],
        reference_datetime=activity.start_date,
        athlete_timezone=ZoneInfo("UTC"),
    ) == 1


def test_no_matching_runs_returns_int_zero(activity) -> None:
    activities = [
        replace(activity, sport_type="Ride"),
        replace(activity, start_date=activity.start_date - timedelta(days=7)),
        replace(activity, start_date=activity.start_date + timedelta(days=7)),
    ]

    result = weekly_running_activity_count(
        activities,
        reference_datetime=activity.start_date,
        athlete_timezone=ZoneInfo("UTC"),
    )

    assert result == 0
    assert type(result) is int


@pytest.mark.parametrize(
    ("boundary", "microseconds", "expected"),
    [("start", -1, 0), ("start", 0, 1), ("end", -1, 1), ("end", 0, 0)],
)
def test_local_week_boundaries(activity, boundary, microseconds, expected) -> None:
    boundary_datetime = datetime.fromisoformat(
        "2026-09-20T22:00:00+00:00"
        if boundary == "start"
        else "2026-09-27T22:00:00+00:00"
    )
    boundary_activity = replace(
        activity,
        start_date=boundary_datetime + timedelta(microseconds=microseconds),
    )

    assert weekly_running_activity_count(
        [boundary_activity],
        reference_datetime=activity.start_date,
        athlete_timezone=ZoneInfo("Europe/Madrid"),
    ) == expected


def test_rejects_naive_reference_even_with_empty_input() -> None:
    with pytest.raises(ValueError, match="Reference datetime must be timezone-aware"):
        weekly_running_activity_count(
            [],
            reference_datetime=datetime(2026, 9, 23),
            athlete_timezone=ZoneInfo("UTC"),
        )


def test_does_not_mutate_inputs_and_is_repeatable(activity) -> None:
    activities = [activity, replace(activity, id=124, distance_meters=1250.5)]
    original_activities = [replace(item) for item in activities]

    for _ in range(2):
        assert weekly_running_activity_count(
            activities,
            reference_datetime=activity.start_date,
            athlete_timezone=ZoneInfo("Europe/Madrid"),
        ) == 2

    assert activities == original_activities
