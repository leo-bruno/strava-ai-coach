"""Unit tests for weekly running distance."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from src.analytics.distance import weekly_running_distance
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


def test_empty_input_returns_float_zero(activity) -> None:
    result = weekly_running_distance(
        [],
        reference_datetime=activity.start_date,
        athlete_timezone=ZoneInfo("UTC"),
    )

    assert result == 0.0
    assert isinstance(result, float)


def test_sums_runs_and_preserves_fractional_meters(activity) -> None:
    activities = [
        activity,
        replace(activity, id=124, distance_meters=1250.5),
        replace(activity, id=125, distance_meters=100.2),
        replace(activity, id=126, distance_meters=0.0),
    ]

    result = weekly_running_distance(
        activities,
        reference_datetime=activity.start_date,
        athlete_timezone=ZoneInfo("UTC"),
    )

    assert result == pytest.approx(6350.7)
    assert isinstance(result, float)


@pytest.mark.parametrize("sport_type", ["Ride", "Walk", "TrailRun", "run"])
def test_excludes_other_sports(activity, sport_type) -> None:
    other_activity = replace(activity, id=124, sport_type=sport_type)

    assert weekly_running_distance(
        [activity, other_activity],
        reference_datetime=activity.start_date,
        athlete_timezone=ZoneInfo("UTC"),
    ) == 5000.0


def test_no_matching_runs_returns_float_zero(activity) -> None:
    activities = [
        replace(activity, sport_type="Ride"),
        replace(activity, start_date=activity.start_date - timedelta(days=7)),
        replace(activity, start_date=activity.start_date + timedelta(days=7)),
    ]

    result = weekly_running_distance(
        activities,
        reference_datetime=activity.start_date,
        athlete_timezone=ZoneInfo("UTC"),
    )

    assert result == 0.0
    assert isinstance(result, float)


@pytest.mark.parametrize(
    ("timezone_name", "reference", "start_utc", "end_utc"),
    [
        (
            "UTC",
            "2026-09-23T12:00:00+00:00",
            "2026-09-21T00:00:00+00:00",
            "2026-09-28T00:00:00+00:00",
        ),
        (
            "Europe/Madrid",
            "2026-09-23T12:00:00+00:00",
            "2026-09-20T22:00:00+00:00",
            "2026-09-27T22:00:00+00:00",
        ),
        (
            "America/New_York",
            "2026-09-23T12:00:00+00:00",
            "2026-09-21T04:00:00+00:00",
            "2026-09-28T04:00:00+00:00",
        ),
        (
            "Europe/Madrid",
            "2026-03-29T12:00:00+00:00",
            "2026-03-22T23:00:00+00:00",
            "2026-03-29T22:00:00+00:00",
        ),
        (
            "Europe/Madrid",
            "2026-10-25T12:00:00+00:00",
            "2026-10-18T22:00:00+00:00",
            "2026-10-25T23:00:00+00:00",
        ),
        (
            "Europe/Madrid",
            "2027-01-01T12:00:00+00:00",
            "2026-12-27T23:00:00+00:00",
            "2027-01-03T23:00:00+00:00",
        ),
    ],
    ids=["utc", "positive-offset", "negative-offset", "spring-dst", "autumn-dst", "new-year"],
)
@pytest.mark.parametrize(
    ("boundary", "microseconds", "expected"),
    [("start", -1, 0.0), ("start", 0, 5000.0), ("end", -1, 5000.0), ("end", 0, 0.0)],
)
def test_week_boundaries(
    activity, timezone_name, reference, start_utc, end_utc,
    boundary, microseconds, expected,
) -> None:
    boundary_datetime = datetime.fromisoformat(
        start_utc if boundary == "start" else end_utc
    )
    activity = replace(
        activity,
        start_date=boundary_datetime + timedelta(microseconds=microseconds),
    )

    assert weekly_running_distance(
        [activity],
        reference_datetime=datetime.fromisoformat(reference),
        athlete_timezone=ZoneInfo(timezone_name),
    ) == expected


@pytest.mark.parametrize(
    ("timezone_name", "start_date", "reference", "expected"),
    [
        ("Europe/Madrid", "2026-09-20T22:30:00+00:00", "2026-09-23T12:00:00+00:00", 5000.0),
        ("America/New_York", "2026-09-21T00:30:00+00:00", "2026-09-23T12:00:00+00:00", 0.0),
        ("America/New_York", "2026-09-21T00:30:00+00:00", "2026-09-16T12:00:00+00:00", 5000.0),
        ("Europe/Madrid", "2026-09-22T08:00:00+00:00", "2026-09-20T22:30:00+00:00", 5000.0),
        ("America/New_York", "2026-09-16T08:00:00+00:00", "2026-09-21T00:30:00+00:00", 5000.0),
    ],
)
def test_uses_local_dates_for_activities_and_reference(
    activity, timezone_name, start_date, reference, expected
) -> None:
    activity = replace(activity, start_date=datetime.fromisoformat(start_date))

    assert weekly_running_distance(
        [activity],
        reference_datetime=datetime.fromisoformat(reference),
        athlete_timezone=ZoneInfo(timezone_name),
    ) == expected


@pytest.mark.parametrize("reference_timezone", ["UTC", "Europe/Madrid", "America/New_York"])
def test_equivalent_reference_instants_select_same_week(activity, reference_timezone) -> None:
    reference = datetime(2026, 9, 20, 22, 30, tzinfo=timezone.utc)

    assert weekly_running_distance(
        [activity],
        reference_datetime=reference.astimezone(ZoneInfo(reference_timezone)),
        athlete_timezone=ZoneInfo("Europe/Madrid"),
    ) == 5000.0


def test_rejects_naive_reference_even_with_empty_input() -> None:
    with pytest.raises(ValueError, match="Reference datetime must be timezone-aware"):
        weekly_running_distance(
            [],
            reference_datetime=datetime(2026, 9, 23),
            athlete_timezone=ZoneInfo("UTC"),
        )


def test_does_not_mutate_inputs_and_is_repeatable(activity) -> None:
    activities = [activity, replace(activity, id=124, distance_meters=1250.5)]
    original_activities = [replace(item) for item in activities]

    for _ in range(2):
        assert weekly_running_distance(
            activities,
            reference_datetime=activity.start_date,
            athlete_timezone=ZoneInfo("Europe/Madrid"),
        ) == 6250.5

    assert activities == original_activities
