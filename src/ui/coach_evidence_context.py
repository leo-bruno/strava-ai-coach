"""Prepare and render a neutral, session-only Coach evidence context."""

from collections.abc import MutableMapping
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.ai.coach_context import build_coach_context
from src.models.coach_context import CoachContext, SourceMetadata
from src.models.coach_request import CoachRequest, coach_request_from_input
from src.models.weekly_analysis import WeeklyAnalysis
from src.ui.strava_connection import ACCESS_TOKEN_KEY, EXPIRES_AT_KEY
from src.ui.strava_weekly_overview import (
    WEEKLY_ANALYSES_KEY,
    WEEKLY_AS_OF_KEY,
    WEEKLY_QUERY_TIMEZONE_KEY,
    COACH_EVIDENCE_CONTEXT_KEY,
)

def clear_coach_evidence_context(session_state: MutableMapping[str, object]) -> None:
    session_state.pop(COACH_EVIDENCE_CONTEXT_KEY, None)


def coach_evidence_context_is_available(
    session_state: MutableMapping[str, object],
    timezone_name: object,
    reference_datetime: datetime,
) -> bool:
    """Whether a current, session-only weekly overview can seed evidence."""
    return coach_evidence_context_guidance(
        session_state, timezone_name, reference_datetime
    ) is None


def coach_evidence_context_guidance(
    session_state: MutableMapping[str, object],
    timezone_name: object,
    reference_datetime: datetime,
) -> str | None:
    """Return concise, state-specific guidance when evidence cannot be prepared."""
    if (
        not isinstance(reference_datetime, datetime)
        or reference_datetime.tzinfo is None
        or reference_datetime.utcoffset() is None
    ):
        return "Select the shared time zone before preparing Coach evidence context."
    token = session_state.get(ACCESS_TOKEN_KEY)
    expires_at = session_state.get(EXPIRES_AT_KEY)
    if not isinstance(token, str) or not token.strip():
        return "Connect Strava to prepare Coach evidence context, then load the weekly overview."
    if type(expires_at) is not int or expires_at <= reference_datetime.timestamp():
        return "Reconnect Strava before preparing Coach evidence context; the access token has expired."
    if not isinstance(timezone_name, str) or not timezone_name:
        return "Select the shared time zone, then load its weekly overview before preparing Coach evidence context."
    try:
        ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        return "Select the shared time zone, then load its weekly overview before preparing Coach evidence context."
    weeks = session_state.get(WEEKLY_ANALYSES_KEY)
    as_of = session_state.get(WEEKLY_AS_OF_KEY)
    if (
        not isinstance(weeks, (tuple, list))
        or len(weeks) != 7
        or any(not isinstance(week, WeeklyAnalysis) for week in weeks)
        or not isinstance(as_of, datetime)
        or as_of.tzinfo is None
        or as_of.utcoffset() is None
    ):
        return "Load the seven completed-week overview for the selected time zone before preparing Coach evidence context."
    if session_state.get(WEEKLY_QUERY_TIMEZONE_KEY) != timezone_name:
        return "Reload the weekly overview for the selected time zone before preparing Coach evidence context."
    if as_of > reference_datetime:
        return "Reload the weekly overview for the selected time zone before preparing Coach evidence context."
    return None


def prepare_coach_evidence_context(
    session_state: MutableMapping[str, object],
    request_data: dict[str, object],
    timezone_name: object,
    reference_datetime: datetime,
) -> tuple[CoachRequest, CoachContext]:
    """Validate current request and build from the already-loaded weekly data."""
    if (
        not isinstance(reference_datetime, datetime)
        or reference_datetime.tzinfo is None
        or reference_datetime.utcoffset() is None
    ):
        raise ValueError("Could not prepare the Coach evidence context from the current request and weekly data.")
    if not isinstance(timezone_name, str) or not timezone_name:
        raise ValueError("Select a valid IANA time zone before preparing Coach evidence context.")
    try:
        athlete_timezone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("Select a valid IANA time zone before preparing Coach evidence context.") from None

    request = coach_request_from_input(
        request_data,
        reference_datetime=reference_datetime,
        athlete_timezone=athlete_timezone,
    )

    token = session_state.get(ACCESS_TOKEN_KEY)
    expires_at = session_state.get(EXPIRES_AT_KEY)
    if not isinstance(token, str) or not token.strip() or type(expires_at) is not int:
        raise ValueError("Connect Strava again before preparing Coach evidence context.")
    if expires_at <= reference_datetime.timestamp():
        raise ValueError("Connect Strava again before preparing Coach evidence context.")

    weeks = session_state.get(WEEKLY_ANALYSES_KEY)
    as_of = session_state.get(WEEKLY_AS_OF_KEY)
    if (
        not isinstance(weeks, (tuple, list))
        or len(weeks) != 7
        or any(not isinstance(week, WeeklyAnalysis) for week in weeks)
        or not isinstance(as_of, datetime)
        or as_of.tzinfo is None
        or as_of.utcoffset() is None
    ):
        raise ValueError("Load the seven-week Strava overview before preparing Coach evidence context.")
    if session_state.get(WEEKLY_QUERY_TIMEZONE_KEY) != timezone_name:
        raise ValueError("Reload the weekly overview for the selected time zone before preparing Coach evidence context.")
    if as_of > reference_datetime:
        raise ValueError("Reload the Strava overview before preparing Coach evidence context.")

    context = build_coach_context(
        request,
        weeks,
        reference_datetime=reference_datetime,
        athlete_timezone=athlete_timezone,
        source_metadata=SourceMetadata(
            source_name="Strava weekly overview",
            data_as_of=as_of,
            coverage="incomplete",
        ),
    )
    return request, context


def render_coach_evidence_context(
    ui, context: CoachContext, weeks: tuple[WeeklyAnalysis, ...]
) -> None:
    """Display safe fields explicitly; never dump RunnerContext or CoachContext."""
    ui.subheader("Coach evidence context")
    ui.info("Deterministic evidence for Coach; no advice was generated.")
    metadata = context.source_metadata
    ui.write(
        f"Local evidence window: {context.recent_window_start.isoformat()} to "
        f"{context.recent_window_end_exclusive.isoformat()} (end exclusive)."
    )
    ui.write(f"Source: {metadata.source_name}; coverage: {metadata.coverage}.")
    ui.write(f"Data as of: {metadata.data_as_of.isoformat() if metadata.data_as_of else 'unavailable'}.")
    ui.write(f"Reference time: {context.reference_datetime.isoformat()} ({context.athlete_timezone.key}).")

    ui.write("Seven loaded weekly Run observations:")
    ui.table([
        {
            "week_start": week.week_start_date.isoformat(),
            "run_records": week.running_activity_count,
            "distance_meters": week.running_distance_meters,
            "moving_time_seconds": week.running_moving_time_seconds,
        }
        for week in weeks
    ])
    if context.missing_recent_week_dates:
        ui.write("No supplied observation for weeks: " + ", ".join(
            day.isoformat() for day in context.missing_recent_week_dates
        ) + ".")

    trend_rows = []
    for label, trends in (
        ("distance_change_meters", context.distance_changes),
        ("distance_change_percent", context.distance_percentage_changes),
        ("run_record_change", context.activity_count_changes),
        ("moving_time_change_seconds", context.moving_time_changes),
    ):
        trend_rows.extend(
            {
                "measure": label,
                "from_week": item.previous_week_start_date.isoformat(),
                "to_week": item.current_week_start_date.isoformat(),
                "observed_change": item.value,
            }
            for item in trends
        )
    ui.write("Existing deterministic trends:")
    if trend_rows:
        ui.table(trend_rows)
    else:
        ui.write("No comparable supplied weekly observations for trends.")

    insight_rows = []
    for kind, insights in (
        ("Persistent weekly running distance increase", context.distance_increase_insights),
        ("Persistent weekly running distance decrease", context.distance_decrease_insights),
    ):
        insight_rows.extend({
            "existing_insight": kind,
            "first_week": item.start_week_date.isoformat(),
            "last_week": item.end_week_date.isoformat(),
            "weekly_distances_meters": item.weekly_distances_meters,
            "weekly_run_records": item.weekly_activity_counts,
        } for item in insights)
    insight_rows.extend({
        "existing_insight": "Observed Run records after zero-Run records",
        "first_zero_run_week": item.first_zero_week_date.isoformat(),
        "observed_zero_run_weeks": item.observed_zero_week_count,
        "following_week": item.running_week_date.isoformat(),
        "following_week_run_records": item.running_week_activity_count,
        "following_week_distance_meters": item.running_week_distance_meters,
    } for item in context.observed_running_insights)
    ui.write("Existing Insights:")
    if insight_rows:
        ui.table(insight_rows)
    else:
        ui.write("No existing Insight detector output in the supplied evidence window.")

    ui.write("Evidence limitations:")
    if context.limitations:
        for limitation in context.limitations:
            dates = ", ".join(day.isoformat() for day in limitation.week_dates)
            suffix = f" Weeks: {dates}." if dates else ""
            ui.write(f"{limitation.code}: {limitation.detail}{suffix}")
    else:
        ui.write("No limitation was recorded by the evidence builder.")

