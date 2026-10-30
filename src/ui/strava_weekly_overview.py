"""Load a session-only seven-week Strava overview on explicit user request."""

from collections.abc import Callable, MutableMapping
from datetime import datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.analytics.weekly_analysis import weekly_analysis_from_activities
from src.insights.running_activity import detect_observed_running_after_zero_run_weeks
from src.insights.running_distance import (
    detect_persistent_weekly_running_distance_decreases,
    detect_persistent_weekly_running_distance_increases,
)
from src.models.activity import Activity
from src.models.weekly_analysis import WeeklyAnalysis
from src.strava.client import DEFAULT_ACTIVITIES_PAGE_SIZE, StravaClient
from src.ui.strava_connection import ACCESS_TOKEN_KEY, EXPIRES_AT_KEY


WEEKLY_TIMEZONE_KEY = "athlete_timezone"
WEEKLY_ACTIVITIES_KEY = "strava_weekly_activities"
WEEKLY_ANALYSES_KEY = "strava_weekly_analyses"
WEEKLY_INSIGHTS_KEY = "strava_weekly_insights"
WEEKLY_PERIOD_START_KEY = "strava_weekly_period_start"
WEEKLY_PERIOD_END_KEY = "strava_weekly_period_end"
WEEKLY_PAGE_COUNT_KEY = "strava_weekly_page_count"
WEEKLY_AS_OF_KEY = "strava_weekly_as_of"
ACTIVITY_BOUNDARY_MARGIN_SECONDS = 1
COMPLETED_WEEK_COUNT = 7


def clear_weekly_overview(session_state: MutableMapping[str, Any]) -> None:
    """Clear the loaded data and all derived weekly outputs from this session."""
    for key in (
        WEEKLY_ACTIVITIES_KEY,
        WEEKLY_ANALYSES_KEY,
        WEEKLY_INSIGHTS_KEY,
        WEEKLY_PERIOD_START_KEY,
        WEEKLY_PERIOD_END_KEY,
        WEEKLY_PAGE_COUNT_KEY,
        WEEKLY_AS_OF_KEY,
    ):
        session_state.pop(key, None)


def clear_expired_weekly_overview(
    session_state: MutableMapping[str, Any], *, now: float | None = None
) -> None:
    """Discard any loaded overview if its session access token is absent/expired."""
    expires_at = session_state.get(EXPIRES_AT_KEY)
    current_time = datetime.now(timezone.utc).timestamp() if now is None else now
    if type(expires_at) is not int or expires_at <= current_time:
        clear_weekly_overview(session_state)


def _local_week_bounds(
    as_of: datetime, athlete_timezone: ZoneInfo
) -> tuple[datetime, datetime]:
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("The as-of time must include a timezone.")
    as_of_local = as_of.astimezone(athlete_timezone)
    current_monday = as_of_local.date() - timedelta(days=as_of_local.weekday())
    period_end_date = current_monday
    period_start_date = period_end_date - timedelta(weeks=COMPLETED_WEEK_COUNT)
    start = datetime.combine(period_start_date, time.min, tzinfo=athlete_timezone)
    end = datetime.combine(period_end_date, time.min, tzinfo=athlete_timezone)
    return start, end


def _resolve_timezone(timezone_name: object) -> ZoneInfo:
    if not isinstance(timezone_name, str) or not timezone_name.strip():
        raise ValueError("Enter a valid IANA time zone before loading weekly Strava data.")
    try:
        return ZoneInfo(timezone_name.strip())
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("Enter a valid IANA time zone before loading weekly Strava data.") from None


def _activities_in_local_period(
    activities: list[Activity], start: datetime, end: datetime, athlete_timezone: ZoneInfo
) -> list[Activity]:
    return [
        activity
        for activity in activities
        if activity.sport_type == "Run"
        and start <= activity.start_date.astimezone(athlete_timezone) < end
    ]


def _build_weekly_analyses(
    activities: list[Activity], start: datetime, athlete_timezone: ZoneInfo
) -> tuple[WeeklyAnalysis, ...]:
    analyses = []
    for offset in range(COMPLETED_WEEK_COUNT):
        week_start = start.date() + timedelta(weeks=offset)
        reference = datetime.combine(
            week_start + timedelta(days=3), time(hour=12), tzinfo=athlete_timezone
        )
        analyses.append(
            weekly_analysis_from_activities(
                activities,
                reference_datetime=reference,
                athlete_timezone=athlete_timezone,
            )
        )
    return tuple(analyses)


def load_recent_weekly_overview(
    session_state: MutableMapping[str, Any],
    timezone_name: object,
    *,
    client_factory=None,
    now: datetime | None = None,
    clock: Callable[[], datetime] | None = None,
) -> None:
    """Fetch the latest seven complete local weeks and derive existing Insights.

    API boundary timestamps are widened by one second because Strava's public
    reference describes before/after filtering but does not promise endpoint
    inclusivity. Returned starts are post-filtered against the exact local
    Monday-to-Monday half-open interval before any weekly metrics are built.
    """
    clear_weekly_overview(session_state)
    athlete_timezone = _resolve_timezone(timezone_name)
    token = session_state.get(ACCESS_TOKEN_KEY)
    expires_at = session_state.get(EXPIRES_AT_KEY)
    clock_now = datetime.now(timezone.utc) if clock is None else clock()
    as_of = clock_now if now is None else now
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("The as-of time must include a timezone.")
    as_of_utc = as_of.astimezone(timezone.utc)
    if not isinstance(token, str) or not token.strip() or type(expires_at) is not int:
        raise ValueError("Connect Strava again before loading weekly data.")
    if expires_at <= as_of_utc.timestamp():
        raise ValueError("The Strava session has expired. Connect again before loading weekly data.")

    start_local, end_local = _local_week_bounds(as_of_utc, athlete_timezone)
    after = int(start_local.astimezone(timezone.utc).timestamp()) - ACTIVITY_BOUNDARY_MARGIN_SECONDS
    before = int(end_local.astimezone(timezone.utc).timestamp()) + ACTIVITY_BOUNDARY_MARGIN_SECONDS
    client = (StravaClient if client_factory is None else client_factory)(access_token=token)

    activities: list[Activity] = []
    page = 1
    page_count = 0
    while True:
        current_time = datetime.now(timezone.utc) if clock is None else clock()
        if expires_at <= current_time.timestamp():
            raise ValueError("The Strava session has expired. Connect again before loading weekly data.")
        page_activities = client.get_activities(
            after=after,
            before=before,
            page=page,
            per_page=DEFAULT_ACTIVITIES_PAGE_SIZE,
        )
        if not isinstance(page_activities, list):
            raise RuntimeError("Strava returned an invalid activities page.")
        current_time = datetime.now(timezone.utc) if clock is None else clock()
        if expires_at <= current_time.timestamp():
            raise ValueError("The Strava session has expired. Connect again before loading weekly data.")
        activities.extend(page_activities)
        page_count += 1
        if len(page_activities) < DEFAULT_ACTIVITIES_PAGE_SIZE:
            break
        page += 1

    exact_period_activities = _activities_in_local_period(
        activities, start_local, end_local, athlete_timezone
    )
    weekly_analyses = _build_weekly_analyses(
        exact_period_activities, start_local, athlete_timezone
    )
    insights = {
        "distance_increases": detect_persistent_weekly_running_distance_increases(
            weekly_analyses
        ),
        "distance_decreases": detect_persistent_weekly_running_distance_decreases(
            weekly_analyses
        ),
        "observed_running_after_zero_weeks": detect_observed_running_after_zero_run_weeks(
            weekly_analyses
        ),
    }

    session_state[WEEKLY_ACTIVITIES_KEY] = tuple(exact_period_activities)
    session_state[WEEKLY_ANALYSES_KEY] = weekly_analyses
    session_state[WEEKLY_INSIGHTS_KEY] = insights
    session_state[WEEKLY_PERIOD_START_KEY] = start_local
    session_state[WEEKLY_PERIOD_END_KEY] = end_local
    session_state[WEEKLY_PAGE_COUNT_KEY] = page_count
    session_state[WEEKLY_AS_OF_KEY] = as_of_utc.astimezone(athlete_timezone)
