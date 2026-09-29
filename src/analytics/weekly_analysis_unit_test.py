"""Unit tests for composing weekly analysis from supplied activities."""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from src.analytics.weekly_analysis import weekly_analysis_from_activities
from src.models.activity import Activity
from src.models.weekly_analysis import WeeklyAnalysis


@pytest.fixture
def activity() -> Activity:
    return Activity(
        id=123,
        name="Morning Run",
        sport_type="Run",
        start_date=datetime(2026, 9, 20, 22, 30, tzinfo=timezone.utc),
        distance_meters=5000.0,
        moving_time_seconds=1500,
    )


def test_composes_local_week_and_metrics_without_mutating_inputs(activity) -> None:
    activities = [
        activity,
        replace(activity, id=124, distance_meters=1250.5),
        replace(activity, id=125, sport_type="Ride"),
        replace(activity, id=126, sport_type="TrailRun"),
        replace(activity, id=127, start_date=activity.start_date - timedelta(days=7)),
        replace(activity, id=128, start_date=activity.start_date + timedelta(days=7)),
    ]
    original = [replace(item) for item in activities]

    for _ in range(2):
        result = weekly_analysis_from_activities(
            activities,
            reference_datetime=activity.start_date,
            athlete_timezone=ZoneInfo("Europe/Madrid"),
        )

        assert result == WeeklyAnalysis(date(2026, 9, 21), 6250.5, 2)
    assert activities == original


@pytest.mark.parametrize("empty", [True, False])
def test_no_matching_runs_keeps_week_identity_and_zero_metrics(activity, empty) -> None:
    result = weekly_analysis_from_activities(
        [] if empty else [replace(activity, sport_type="Ride")],
        reference_datetime=activity.start_date,
        athlete_timezone=ZoneInfo("Europe/Madrid"),
    )

    assert result == WeeklyAnalysis(date(2026, 9, 21), 0.0, 0)
    assert type(result.running_distance_meters) is float
    assert type(result.running_activity_count) is int


def test_zero_distance_run_still_counts(activity) -> None:
    result = weekly_analysis_from_activities(
        [replace(activity, distance_meters=0.0, moving_time_seconds=0)],
        reference_datetime=activity.start_date,
        athlete_timezone=ZoneInfo("Europe/Madrid"),
    )

    assert result == WeeklyAnalysis(date(2026, 9, 21), 0.0, 1)


@pytest.mark.parametrize(
    ("reference", "start", "end", "expected_date"),
    [
        ("2026-03-29T12:00:00+00:00", "2026-03-22T23:00:00+00:00",
         "2026-03-29T22:00:00+00:00", date(2026, 3, 23)),
        ("2026-10-25T12:00:00+00:00", "2026-10-18T22:00:00+00:00",
         "2026-10-25T23:00:00+00:00", date(2026, 10, 19)),
        ("2027-01-01T12:00:00+00:00", "2026-12-27T23:00:00+00:00",
         "2027-01-03T23:00:00+00:00", date(2026, 12, 28)),
    ],
    ids=["spring-dst", "autumn-dst", "new-year"],
)
def test_week_identity_and_metrics_share_local_boundaries(
    activity, reference, start, end, expected_date,
) -> None:
    end_datetime = datetime.fromisoformat(end)
    activities = [
        replace(activity, start_date=datetime.fromisoformat(start)),
        replace(activity, id=124, distance_meters=250.5,
                start_date=end_datetime - timedelta(microseconds=1)),
        replace(activity, id=125, start_date=end_datetime),
    ]

    result = weekly_analysis_from_activities(
        activities,
        reference_datetime=datetime.fromisoformat(reference),
        athlete_timezone=ZoneInfo("Europe/Madrid"),
    )

    assert result == WeeklyAnalysis(expected_date, 5250.5, 2)


def test_equivalent_reference_instants_produce_same_analysis(activity) -> None:
    for reference_timezone in (ZoneInfo("UTC"), ZoneInfo("America/New_York")):
        result = weekly_analysis_from_activities(
            [activity],
            reference_datetime=activity.start_date.astimezone(reference_timezone),
            athlete_timezone=ZoneInfo("Europe/Madrid"),
        )

        assert result == WeeklyAnalysis(date(2026, 9, 21), 5000.0, 1)


@pytest.mark.parametrize("empty", [True, False])
def test_rejects_naive_reference_including_empty_input(activity, empty) -> None:
    with pytest.raises(ValueError, match="Reference datetime must be timezone-aware"):
        weekly_analysis_from_activities(
            [] if empty else [activity],
            reference_datetime=datetime(2026, 9, 23),
            athlete_timezone=ZoneInfo("Europe/Madrid"),
        )
