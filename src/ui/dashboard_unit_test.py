from datetime import date, datetime, timedelta, timezone

from src.models.activity import Activity
from src.models.weekly_analysis import WeeklyAnalysis
from src.ui.dashboard import build_home_dashboard_data
from src.ui.strava_weekly_overview import (
    WEEKLY_ACTIVITIES_KEY,
    WEEKLY_ANALYSES_KEY,
    WEEKLY_AS_OF_KEY,
    WEEKLY_PERIOD_END_KEY,
    WEEKLY_PERIOD_START_KEY,
)


def _week(day, distance=0, count=0, moving=0):
    return WeeklyAnalysis(date.fromisoformat(day), distance, count, moving, ())


def test_home_payload_is_empty_without_a_complete_loaded_overview():
    assert build_home_dashboard_data({}) == {"mode": "empty"}
    assert build_home_dashboard_data({WEEKLY_ANALYSES_KEY: (_week("2026-01-05"),)}) == {"mode": "empty"}


def test_home_payload_serializes_loaded_seven_week_summary_and_activities():
    start = datetime(2026, 1, 5, tzinfo=timezone.utc)
    end = datetime(2026, 2, 23, tzinfo=timezone.utc)
    as_of = datetime(2026, 2, 25, tzinfo=timezone.utc)
    weeks = tuple(
        _week((date(2026, 1, 5) + timedelta(weeks=index)).isoformat(), 5000, 1, 1500)
        for index in range(7)
    )
    activity = Activity(1, "Rodaje", "Run", as_of, 5000, 1500)
    session = {
        WEEKLY_ANALYSES_KEY: weeks,
        WEEKLY_ACTIVITIES_KEY: (activity,),
        WEEKLY_PERIOD_START_KEY: start,
        WEEKLY_PERIOD_END_KEY: end,
        WEEKLY_AS_OF_KEY: as_of,
    }

    payload = build_home_dashboard_data(session)

    assert payload["mode"] == "weekly"
    assert len(payload["weeks"]) == 7
    assert payload["weeks"][0] == {
        "weekStart": weeks[0].week_start_date.isoformat(),
        "distanceMeters": 5000,
        "activityCount": 1,
        "movingTimeSeconds": 1500,
    }
    assert payload["activities"][0]["name"] == "Rodaje"
    assert payload["periodStart"] == "2026-01-05"
    assert payload["asOf"] == "2026-02-25"


def test_loaded_zero_week_values_are_preserved_as_real_zeroes():
    session = {
        WEEKLY_ANALYSES_KEY: tuple(
            _week((date(2026, 1, 5) + timedelta(weeks=i)).isoformat())
            for i in range(7)
        ),
        WEEKLY_ACTIVITIES_KEY: (),
        WEEKLY_PERIOD_START_KEY: datetime(2026, 1, 5, tzinfo=timezone.utc),
        WEEKLY_PERIOD_END_KEY: datetime(2026, 2, 23, tzinfo=timezone.utc),
        WEEKLY_AS_OF_KEY: datetime(2026, 2, 25, tzinfo=timezone.utc),
    }

    payload = build_home_dashboard_data(session)

    assert payload["mode"] == "weekly"
    assert all(week["activityCount"] == 0 for week in payload["weeks"])
    assert payload["activities"] == []
