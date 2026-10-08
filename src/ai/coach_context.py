"""Build deterministic Coach evidence from supplied data, without retrieval."""

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from src.insights.running_activity import detect_observed_running_after_zero_run_weeks
from src.insights.running_distance import (
    detect_persistent_weekly_running_distance_decreases,
    detect_persistent_weekly_running_distance_increases,
)
from src.models.coach_context import (
    CoachContext, EvidenceLimitation, EvidenceProvenance, EvidenceReference,
    PreInterruptionBackground, SourceMetadata, WeeklyEvidence,
)
from src.models.coach_request import CoachRequest
from src.models.observed_running_after_zero_run_weeks import ObservedRunningAfterZeroRunWeeks
from src.models.persistent_weekly_running_distance_decrease import PersistentWeeklyRunningDistanceDecrease
from src.models.persistent_weekly_running_distance_increase import PersistentWeeklyRunningDistanceIncrease
from src.models.weekly_analysis import WeeklyAnalysis
from src.trends.activity_count import weekly_running_activity_count_changes
from src.trends.distance import (
    weekly_running_distance_changes, weekly_running_distance_percentage_changes,
)
from src.trends.history import normalize_weekly_history
from src.trends.moving_time import weekly_running_moving_time_changes


_WEEK = timedelta(days=7)


def insight_reference(
    insight: PersistentWeeklyRunningDistanceIncrease
    | PersistentWeeklyRunningDistanceDecrease | ObservedRunningAfterZeroRunWeeks,
) -> str:
    """Date-based identity for each existing concrete Insight type."""
    if isinstance(insight, ObservedRunningAfterZeroRunWeeks):
        return f"insight:observed_running:{insight.first_zero_week_date}:{insight.running_week_date}"
    kind = "distance_increase" if isinstance(insight, PersistentWeeklyRunningDistanceIncrease) else "distance_decrease"
    return f"insight:{kind}:{insight.start_week_date}:{insight.end_week_date}"


def _weekly_evidence(
    week: WeeklyAnalysis,
    *,
    open_week: bool,
    partial: bool,
    metadata: SourceMetadata,
) -> WeeklyEvidence:
    return WeeklyEvidence(
        reference=f"week:{week.week_start_date}",
        week_start_date=week.week_start_date,
        running_distance_meters=week.running_distance_meters,
        running_activity_count=week.running_activity_count,
        running_moving_time_seconds=week.running_moving_time_seconds,
        training_type_counts=tuple(
            (summary.training_type, summary.activity_count)
            for summary in week.running_structure_by_type
        ),
        calendar_status="open" if open_week else "completed",
        known_partial=open_week or partial,
        data_as_of=metadata.data_as_of,
    )


def _validate_metadata(metadata: SourceMetadata, reference_datetime: datetime) -> None:
    if not isinstance(metadata, SourceMetadata):
        raise ValueError("Source metadata must be SourceMetadata.")
    if metadata.source_name is not None and (
        not isinstance(metadata.source_name, str) or not metadata.source_name.strip()
    ):
        raise ValueError("Source name must be nonblank text or None.")
    if metadata.coverage not in ("unknown", "incomplete", "complete"):
        raise ValueError("Coverage must be unknown, incomplete or complete.")
    if metadata.data_as_of is not None:
        if (
            not isinstance(metadata.data_as_of, datetime)
            or metadata.data_as_of.tzinfo is None
            or metadata.data_as_of.utcoffset() is None
        ):
            raise ValueError("Data-as-of must be timezone-aware or None.")
        if metadata.data_as_of > reference_datetime:
            raise ValueError("Data-as-of must not be after the reference datetime.")
    if not isinstance(metadata.partial_week_dates, tuple) or any(
        type(day) is not date or day.weekday() != 0
        for day in metadata.partial_week_dates
    ):
        raise ValueError("Partial week dates must be a tuple of local Mondays.")
    if len(set(metadata.partial_week_dates)) != len(metadata.partial_week_dates):
        raise ValueError("Partial week dates must be unique.")


def build_coach_context(
    request: CoachRequest,
    weeks: Sequence[WeeklyAnalysis],
    *,
    reference_datetime: datetime,
    athlete_timezone: ZoneInfo,
    source_metadata: SourceMetadata | None = None,
) -> CoachContext:
    """Select evidence; never assess training or interpret runner reports.

    The caller supplies valid domain observations for one athlete/timezone,
    and a request validated with Increment 1 using this reference/timezone.
    Missing coverage is unknown, not permission to certify completeness.
    Known partial dates and an earlier data-as-of exclude observations from
    comparable history. The open week is always partial. Future observations
    and future as-of metadata are rejected to avoid evidence after reference.
    All calendar periods are local dates with end-exclusive Monday boundaries.
    """
    if (
        not isinstance(reference_datetime, datetime)
        or reference_datetime.tzinfo is None
        or reference_datetime.utcoffset() is None
    ):
        raise ValueError("Reference datetime must be timezone-aware.")
    if not isinstance(athlete_timezone, ZoneInfo):
        raise ValueError("Athlete timezone must be an explicit ZoneInfo.")
    metadata = source_metadata if source_metadata is not None else SourceMetadata()
    _validate_metadata(metadata, reference_datetime)
    local_date = reference_datetime.astimezone(athlete_timezone).date()
    current_monday = local_date - timedelta(days=local_date.weekday())
    recent_start = current_monday - 4 * _WEEK
    latest_completed = current_monday - _WEEK
    normalized = normalize_weekly_history(weeks)
    if any(week.week_start_date > current_monday for week in normalized):
        raise ValueError("Supplied observations must not belong to future calendar weeks.")

    partial_dates = set(metadata.partial_week_dates)
    if metadata.data_as_of is not None:
        partial_dates.update(
            week.week_start_date for week in normalized
            if metadata.data_as_of < datetime.combine(
                week.week_start_date + _WEEK, time.min, tzinfo=athlete_timezone,
            )
        )
    completed = tuple(
        week for week in normalized
        if week.week_start_date < current_monday and week.week_start_date not in partial_dates
    )
    recent_supplied = tuple(
        week for week in normalized if recent_start <= week.week_start_date < current_monday
    )
    recent_comparable = tuple(
        week for week in completed if recent_start <= week.week_start_date
    )
    by_date = {week.week_start_date: week for week in normalized}
    recent_dates = tuple(recent_start + i * _WEEK for i in range(4))
    missing = tuple(day for day in recent_dates if day not in by_date)
    partial_completed = tuple(
        week.week_start_date for week in normalized
        if week.week_start_date < current_monday and week.week_start_date in partial_dates
    )

    # Detect on all eligible supplied completed history, then filter endpoints.
    increases = tuple(
        insight for insight in detect_persistent_weekly_running_distance_increases(completed)
        if recent_start <= insight.end_week_date < current_monday
    )
    decreases = tuple(
        insight for insight in detect_persistent_weekly_running_distance_decreases(completed)
        if recent_start <= insight.end_week_date < current_monday
    )
    observed_running = tuple(
        insight for insight in detect_observed_running_after_zero_run_weeks(completed)
        if recent_start <= insight.running_week_date < current_monday
    )
    recent = tuple(
        _weekly_evidence(week, open_week=False, partial=week.week_start_date in partial_dates, metadata=metadata)
        for week in recent_supplied
    )
    open_evidence = (
        _weekly_evidence(by_date[current_monday], open_week=True, partial=True, metadata=metadata)
        if current_monday in by_date else None
    )
    limitations = []
    if missing:
        limitations.append(EvidenceLimitation("MISSING_RECENT_WEEKS", "Recent calendar weeks have no supplied observation; missing is not zero.", missing))
    if partial_completed:
        limitations.append(EvidenceLimitation("PARTIAL_COMPLETED_WEEKS", "Calendar-completed observations are known incomplete and excluded from comparisons and patterns, including older supporting history.", partial_completed))
    unavailable = []
    if metadata.source_name is None:
        unavailable.append("source identity")
    if metadata.data_as_of is None:
        unavailable.append("data-as-of")
    if unavailable:
        limitations.append(EvidenceLimitation("SOURCE_METADATA_UNAVAILABLE", "Unavailable: " + ", ".join(unavailable) + "."))
    if metadata.coverage != "complete":
        limitations.append(EvidenceLimitation(
            "SOURCE_COVERAGE_" + metadata.coverage.upper(),
            f"Supplied source coverage is {metadata.coverage}; calendar closure does not establish data completeness.",
        ))
    if open_evidence is not None:
        limitations.append(EvidenceLimitation("OPEN_WEEK_PARTIAL", "Current-week evidence is partial and excluded from completed-week comparisons and patterns.", (current_monday,)))

    background = None
    if observed_running:
        trigger = observed_running[-1]
        zero_weeks = tuple(
            _weekly_evidence(by_date[trigger.first_zero_week_date + i * _WEEK], open_week=False, partial=False, metadata=metadata)
            for i in range(trigger.observed_zero_week_count)
        )
        selected = []
        cursor = trigger.first_zero_week_date - _WEEK
        while len(selected) < 4:
            week = by_date.get(cursor)
            if week is None or cursor in partial_dates or week.running_activity_count <= 0:
                break
            selected.append(_weekly_evidence(week, open_week=False, partial=False, metadata=metadata))
            cursor -= _WEEK
        background = PreInterruptionBackground(
            insight_reference(trigger), zero_weeks, tuple(reversed(selected)),
        )
        if not selected:
            limitations.append(EvidenceLimitation("PRE_INTERRUPTION_BACKGROUND_UNAVAILABLE", "No immediately preceding eligible historical observation is supplied; no previous volume can be established."))

    distance_changes = weekly_running_distance_changes(recent_comparable)
    distance_percentages = weekly_running_distance_percentage_changes(recent_comparable)
    count_changes = weekly_running_activity_count_changes(recent_comparable)
    time_changes = weekly_running_moving_time_changes(recent_comparable)
    refs = {
        "request:goal": EvidenceReference("request:goal", EvidenceProvenance.USER_REPORT),
        "request:constraints": EvidenceReference("request:constraints", EvidenceProvenance.USER_REPORT),
        "temporal:context": EvidenceReference("temporal:context", EvidenceProvenance.DETERMINISTIC),
    }
    if request.context.runner_context is not None:
        refs["request:runner_context"] = EvidenceReference("request:runner_context", EvidenceProvenance.USER_REPORT)
    weekly_entries = recent + ((open_evidence,) if open_evidence is not None else ())
    if background is not None:
        weekly_entries += background.zero_run_weeks + background.observations
    for week in weekly_entries:
        refs[week.reference] = EvidenceReference(week.reference, week.provenance)
    for kind, changes in (
        ("distance_absolute", distance_changes), ("distance_percentage", distance_percentages),
        ("activity_count_absolute", count_changes), ("moving_time_absolute", time_changes),
    ):
        for change in changes:
            reference = f"trend:{kind}:{change.previous_week_start_date}:{change.current_week_start_date}"
            refs[reference] = EvidenceReference(reference, EvidenceProvenance.DETERMINISTIC)
    for insight in increases + decreases + observed_running:
        endpoint = insight.running_week_date if isinstance(insight, ObservedRunningAfterZeroRunWeeks) else insight.end_week_date
        reference = insight_reference(insight)
        refs[reference] = EvidenceReference(
            reference, EvidenceProvenance.DETERMINISTIC,
            "latest_completed_week" if endpoint == latest_completed else "earlier_in_recent_window",
        )

    return CoachContext(
        goal=request.goal, constraints=request.constraints, runner_context=request.context,
        reference_datetime=reference_datetime, athlete_timezone=athlete_timezone,
        reference_local_date=local_date, recent_window_start=recent_start,
        recent_window_end_exclusive=current_monday,
        recommendation_start=current_monday + _WEEK,
        recommendation_end_exclusive=current_monday + 2 * _WEEK,
        days_until_target_date=(request.goal.target_date - local_date).days,
        source_metadata=metadata, recent_weeks=recent, missing_recent_week_dates=missing,
        open_week=open_evidence, distance_changes=distance_changes,
        distance_percentage_changes=distance_percentages, activity_count_changes=count_changes,
        moving_time_changes=time_changes, distance_increase_insights=increases,
        distance_decrease_insights=decreases, observed_running_insights=observed_running,
        pre_interruption_background=background,
        evidence_references=tuple(refs[key] for key in sorted(refs)), limitations=tuple(limitations),
    )
