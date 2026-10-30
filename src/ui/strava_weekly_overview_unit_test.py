"""Deterministic tests for the manual seven-week Strava overview."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from src.models.activity import Activity
from src.ui.strava_weekly_overview import (
    WEEKLY_ACTIVITIES_KEY,
    WEEKLY_ANALYSES_KEY,
    WEEKLY_AS_OF_KEY,
    WEEKLY_INSIGHTS_KEY,
    WEEKLY_PAGE_COUNT_KEY,
    WEEKLY_PERIOD_END_KEY,
    WEEKLY_PERIOD_START_KEY,
    WEEKLY_QUERY_TIMEZONE_KEY,
    COACH_EVIDENCE_CONTEXT_KEY,
    clear_expired_weekly_overview,
    clear_weekly_overview,
    load_recent_weekly_overview,
)
from src.ui.strava_connection import ACCESS_TOKEN_KEY, EXPIRES_AT_KEY


NOW = datetime(2026, 4, 15, 10, tzinfo=timezone.utc)
ZONE = ZoneInfo("Europe/Madrid")
EXPIRES_AT = 2_100_000_000


def make_activity(
    activity_id: int,
    start_date: datetime,
    *,
    sport_type: str = "Run",
    distance_meters: float = 5000,
) -> Activity:
    return Activity(
        id=activity_id,
        name=f"Activity {activity_id}",
        sport_type=sport_type,
        start_date=start_date,
        distance_meters=distance_meters,
        moving_time_seconds=1500,
    )


def session_with_stale_overview():
    return {
        ACCESS_TOKEN_KEY: "session-access-token",
        EXPIRES_AT_KEY: EXPIRES_AT,
        WEEKLY_ACTIVITIES_KEY: "stale-activities",
        WEEKLY_ANALYSES_KEY: "stale-analyses",
        WEEKLY_INSIGHTS_KEY: "stale-insights",
        WEEKLY_PERIOD_START_KEY: "stale-start",
        WEEKLY_PERIOD_END_KEY: "stale-end",
        WEEKLY_PAGE_COUNT_KEY: 99,
        WEEKLY_AS_OF_KEY: "stale-as-of",
        WEEKLY_QUERY_TIMEZONE_KEY: "stale-timezone",
        COACH_EVIDENCE_CONTEXT_KEY: "stale-context",
    }


def test_local_week_bounds_use_selected_timezone_and_dst_offsets():
    from src.ui.strava_weekly_overview import _local_week_bounds

    start, end = _local_week_bounds(NOW, ZONE)

    assert start.isoformat() == "2026-02-23T00:00:00+01:00"
    assert end.isoformat() == "2026-04-13T00:00:00+02:00"
    assert int(start.astimezone(timezone.utc).timestamp()) == 1_771_801_200
    assert int(end.astimezone(timezone.utc).timestamp()) == 1_776_031_200


def test_fetch_uses_widened_epoch_filters_and_exact_local_half_open_period():
    session = session_with_stale_overview()
    zone = ZONE
    start = datetime(2026, 2, 23, 0, tzinfo=zone)
    end = datetime(2026, 4, 13, 0, tzinfo=zone)
    activities = [
        make_activity(1, start.astimezone(timezone.utc)),
        make_activity(2, (start - timedelta(microseconds=1)).astimezone(timezone.utc)),
        make_activity(3, (end - timedelta(microseconds=1)).astimezone(timezone.utc)),
        make_activity(4, end.astimezone(timezone.utc)),
        make_activity(5, (start + timedelta(days=3)).astimezone(timezone.utc), sport_type="Ride"),
    ]
    page_calls = []

    class FakeClient:
        def __init__(self, *, access_token):
            assert access_token == "session-access-token"

        def get_activities(self, **kwargs):
            page_calls.append(kwargs)
            return activities

    load_recent_weekly_overview(
        session,
        "Europe/Madrid",
        client_factory=FakeClient,
        now=NOW,
        clock=lambda: NOW,
    )

    assert page_calls == [{
        "after": 1_771_801_199,
        "before": 1_776_031_201,
        "page": 1,
        "per_page": 30,
    }]
    assert [activity.id for activity in session[WEEKLY_ACTIVITIES_KEY]] == [1, 3]
    analyses = session[WEEKLY_ANALYSES_KEY]
    assert len(analyses) == 7
    assert [week.running_activity_count for week in analyses] == [1, 0, 0, 0, 0, 0, 1]
    assert session[WEEKLY_PERIOD_START_KEY] == start
    assert session[WEEKLY_PERIOD_END_KEY] == end
    assert session[WEEKLY_PAGE_COUNT_KEY] == 1
    assert session[WEEKLY_AS_OF_KEY] == NOW.astimezone(zone)
    assert set(session[WEEKLY_INSIGHTS_KEY]) == {
        "distance_increases",
        "distance_decreases",
        "observed_running_after_zero_weeks",
    }


def test_pagination_continues_after_full_page_and_stops_after_short_page():
    session = session_with_stale_overview()
    zone = ZONE
    start = datetime(2026, 4, 6, 9, tzinfo=zone).astimezone(timezone.utc)
    full_page = [make_activity(index, start) for index in range(30)]
    short_page = [make_activity(31, start)]
    responses = [full_page, short_page]
    page_calls = []

    class FakeClient:
        def __init__(self, *, access_token):
            pass

        def get_activities(self, **kwargs):
            page_calls.append(kwargs)
            return responses[kwargs["page"] - 1]

    load_recent_weekly_overview(
        session, "Europe/Madrid", client_factory=FakeClient, now=NOW, clock=lambda: NOW
    )

    assert [call["page"] for call in page_calls] == [1, 2]
    assert all(call["per_page"] == 30 for call in page_calls)
    assert session[WEEKLY_PAGE_COUNT_KEY] == 2
    assert len(session[WEEKLY_ACTIVITIES_KEY]) == 31
    assert sum(week.running_activity_count for week in session[WEEKLY_ANALYSES_KEY]) == 31


def test_empty_first_page_creates_seven_zero_weeks_and_counts_one_page():
    session = session_with_stale_overview()
    calls = []

    class FakeClient:
        def __init__(self, *, access_token):
            pass

        def get_activities(self, **kwargs):
            calls.append(kwargs)
            return []

    load_recent_weekly_overview(
        session, "Europe/Madrid", client_factory=FakeClient, now=NOW, clock=lambda: NOW
    )

    assert len(calls) == 1
    assert session[WEEKLY_PAGE_COUNT_KEY] == 1
    assert len(session[WEEKLY_ANALYSES_KEY]) == 7
    assert [week.running_activity_count for week in session[WEEKLY_ANALYSES_KEY]] == [0] * 7
    assert [week.running_distance_meters for week in session[WEEKLY_ANALYSES_KEY]] == [0.0] * 7
    assert all(not outputs for outputs in session[WEEKLY_INSIGHTS_KEY].values())


def test_non_run_activity_does_not_count_as_a_weekly_run_record():
    session = session_with_stale_overview()
    activity = make_activity(1, datetime(2026, 4, 6, 9, tzinfo=ZONE), sport_type="Ride")

    class FakeClient:
        def __init__(self, *, access_token):
            pass

        def get_activities(self, **_kwargs):
            return [activity]

    load_recent_weekly_overview(
        session, "Europe/Madrid", client_factory=FakeClient, now=NOW, clock=lambda: NOW
    )

    assert session[WEEKLY_ACTIVITIES_KEY] == ()
    assert sum(week.running_activity_count for week in session[WEEKLY_ANALYSES_KEY]) == 0


def test_page_failure_discards_partial_data_and_all_stale_outputs():
    session = session_with_stale_overview()
    full_page = [
        make_activity(index, datetime(2026, 4, 6, 9, tzinfo=ZONE).astimezone(timezone.utc))
        for index in range(30)
    ]
    calls = []

    class FakeClient:
        def __init__(self, *, access_token):
            pass

        def get_activities(self, **kwargs):
            calls.append(kwargs["page"])
            assert WEEKLY_ANALYSES_KEY not in session
            assert WEEKLY_ACTIVITIES_KEY not in session
            if kwargs["page"] == 1:
                return full_page
            raise RuntimeError("private provider detail")

    with pytest.raises(RuntimeError, match="private provider detail"):
        load_recent_weekly_overview(
            session, "Europe/Madrid", client_factory=FakeClient, now=NOW, clock=lambda: NOW
        )

    assert calls == [1, 2]
    assert not any(key.startswith("strava_weekly_") and key != "strava_weekly_timezone" for key in session)


def test_invalid_timezone_and_expired_token_clear_stale_results_before_client_creation():
    session = session_with_stale_overview()
    calls = []
    client_factory = lambda **kwargs: calls.append(kwargs)

    with pytest.raises(ValueError, match="valid IANA time zone"):
        load_recent_weekly_overview(
            session, "Not/A_Zone", client_factory=client_factory, now=NOW, clock=lambda: NOW
        )
    assert not calls
    assert WEEKLY_ANALYSES_KEY not in session

    session.update(session_with_stale_overview())
    session[EXPIRES_AT_KEY] = int(NOW.timestamp())
    with pytest.raises(ValueError, match="expired"):
        load_recent_weekly_overview(
            session, "Europe/Madrid", client_factory=client_factory, now=NOW, clock=lambda: NOW
        )
    assert not calls
    assert WEEKLY_ANALYSES_KEY not in session


def test_token_expiring_during_pagination_discards_fetched_page():
    session = session_with_stale_overview()
    session[EXPIRES_AT_KEY] = int(NOW.timestamp()) + 1
    clock_values = iter((NOW, NOW, NOW + timedelta(seconds=2)))
    calls = []

    class FakeClient:
        def __init__(self, *, access_token):
            pass

        def get_activities(self, **kwargs):
            calls.append(kwargs["page"])
            return [make_activity(1, datetime(2026, 4, 6, 9, tzinfo=ZONE))]

    with pytest.raises(ValueError, match="expired"):
        load_recent_weekly_overview(
            session,
            "Europe/Madrid",
            client_factory=FakeClient,
            now=NOW,
            clock=lambda: next(clock_values),
        )

    assert calls == [1]
    assert WEEKLY_ANALYSES_KEY not in session
    assert WEEKLY_ACTIVITIES_KEY not in session


def test_expiry_clear_helper_removes_every_loaded_result():
    session = session_with_stale_overview()
    clear_expired_weekly_overview(session, now=EXPIRES_AT)
    assert not any(key.startswith("strava_weekly_") and key != "strava_weekly_timezone" for key in session)

    session[WEEKLY_ANALYSES_KEY] = "stale"
    clear_weekly_overview(session)
    assert WEEKLY_ANALYSES_KEY not in session
    assert WEEKLY_QUERY_TIMEZONE_KEY not in session
    assert COACH_EVIDENCE_CONTEXT_KEY not in session
