"""Immutable Coach output; application validation is an explicit boundary."""

from dataclasses import dataclass
from datetime import date
from enum import Enum


class CoachResponseStatus(str, Enum):
    GUIDANCE_AVAILABLE = "guidance_available"
    CLARIFICATION_REQUIRED = "clarification_required"
    INSUFFICIENT_SUPPORT = "insufficient_support"


@dataclass(frozen=True)
class RecommendationPeriod:
    """Copy the context's local dates; end_exclusive is the following Monday."""

    start: date
    end_exclusive: date


@dataclass(frozen=True)
class GroundedStatement:
    """User-facing text with explicit support, never hidden chain-of-thought.

    References identify supplied evidence and exact approved knowledge item
    or application-limitation revisions. Their existence does not prove that
    the wording or applicability is semantically correct.
    """

    text: str
    evidence_references: tuple[str, ...]
    knowledge_references: tuple[str, ...]


@dataclass(frozen=True)
class NextWeekRecommendation:
    overall_direction: GroundedStatement | None
    recommended_running_days: int | None
    training_priorities: tuple[GroundedStatement, ...]
    reasoning: GroundedStatement


@dataclass(frozen=True)
class CoachResponse:
    status: CoachResponseStatus
    recommendation_period: RecommendationPeriod
    current_state: GroundedStatement
    recent_evolution: GroundedStatement
    relevant_evidence: tuple[str, ...]
    next_week_recommendation: NextWeekRecommendation | None
    limitations: tuple[GroundedStatement, ...]
    clarification_questions: tuple[GroundedStatement, ...]
