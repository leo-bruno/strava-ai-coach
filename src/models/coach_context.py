"""Immutable request-specific evidence for Coach, without interpretation."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Literal
from zoneinfo import ZoneInfo

from src.models.coach_request import RunnerConstraints, RunnerContext, RunnerGoal
from src.models.observed_running_after_zero_run_weeks import ObservedRunningAfterZeroRunWeeks
from src.models.persistent_weekly_running_distance_decrease import PersistentWeeklyRunningDistanceDecrease
from src.models.persistent_weekly_running_distance_increase import PersistentWeeklyRunningDistanceIncrease
from src.models.training_analysis import TrainingType
from src.models.weekly_running_activity_count_change import WeeklyRunningActivityCountChange
from src.models.weekly_running_distance_change import WeeklyRunningDistanceChange
from src.models.weekly_running_distance_percentage_change import WeeklyRunningDistancePercentageChange
from src.models.weekly_running_moving_time_change import WeeklyRunningMovingTimeChange


class EvidenceProvenance(str, Enum):
    STRAVA_OBSERVATION = "strava_derived_observation"
    DETERMINISTIC = "deterministic_derivation"
    USER_REPORT = "user_report"
    APPROVED_KNOWLEDGE = "approved_training_knowledge"
    COACH_INTERPRETATION = "coach_interpretation"


@dataclass(frozen=True)
class SourceMetadata:
    """Caller-supplied metadata; complete coverage is never inferred.

    partial_week_dates identifies known incomplete observations, including
    older supplied history. A data_as_of before a week's calendar end also
    establishes partiality. None preserves unknown source/as-of information.
    """

    source_name: str | None = None
    data_as_of: datetime | None = None
    coverage: Literal["unknown", "incomplete", "complete"] = "unknown"
    partial_week_dates: tuple[date, ...] = ()


@dataclass(frozen=True)
class WeeklyEvidence:
    """Supplied totals and all six name-based category counts, not effort.

    Each training_type_counts entry is (TrainingType, activity_count) in enum
    order. Per-type distance/time remain in the underlying WeeklyAnalysis.
    A zero observation means no supplied Run activities, not proven inactivity.
    """

    reference: str
    week_start_date: date
    running_distance_meters: float
    running_activity_count: int
    running_moving_time_seconds: int
    training_type_counts: tuple[tuple[TrainingType, int], ...]
    calendar_status: Literal["completed", "open"]
    known_partial: bool
    data_as_of: datetime | None
    provenance: EvidenceProvenance = EvidenceProvenance.STRAVA_OBSERVATION


@dataclass(frozen=True)
class EvidenceReference:
    """Registry for direct evidence and the existing concrete derivations.

    Insight relevance is latest_completed_week or earlier_in_recent_window;
    it describes dates, never current fitness or physiological significance.
    """

    reference: str
    provenance: EvidenceProvenance
    temporal_relevance: str | None = None


@dataclass(frozen=True)
class EvidenceLimitation:
    code: str
    detail: str
    week_dates: tuple[date, ...] = ()


@dataclass(frozen=True)
class PreInterruptionBackground:
    """Observed episode and bounded earlier observations; not a baseline."""

    triggering_insight_reference: str
    zero_run_weeks: tuple[WeeklyEvidence, ...]
    observations: tuple[WeeklyEvidence, ...]


@dataclass(frozen=True)
class CoachContext:
    goal: RunnerGoal
    constraints: RunnerConstraints
    runner_context: RunnerContext
    reference_datetime: datetime
    athlete_timezone: ZoneInfo
    reference_local_date: date
    recent_window_start: date
    recent_window_end_exclusive: date
    recommendation_start: date
    recommendation_end_exclusive: date
    days_until_target_date: int
    source_metadata: SourceMetadata
    recent_weeks: tuple[WeeklyEvidence, ...]
    missing_recent_week_dates: tuple[date, ...]
    open_week: WeeklyEvidence | None
    distance_changes: tuple[WeeklyRunningDistanceChange, ...]
    distance_percentage_changes: tuple[WeeklyRunningDistancePercentageChange, ...]
    activity_count_changes: tuple[WeeklyRunningActivityCountChange, ...]
    moving_time_changes: tuple[WeeklyRunningMovingTimeChange, ...]
    distance_increase_insights: tuple[PersistentWeeklyRunningDistanceIncrease, ...]
    distance_decrease_insights: tuple[PersistentWeeklyRunningDistanceDecrease, ...]
    observed_running_insights: tuple[ObservedRunningAfterZeroRunWeeks, ...]
    pre_interruption_background: PreInterruptionBackground | None
    evidence_references: tuple[EvidenceReference, ...]
    limitations: tuple[EvidenceLimitation, ...]
