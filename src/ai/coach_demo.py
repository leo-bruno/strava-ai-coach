"""Fixed, synthetic Coach demonstration data and pre-recorded response."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from src.ai.coach_context import build_coach_context
from src.ai.coach_response import parse_coach_response
from src.ai.training_knowledge import TrainingKnowledgePackage, load_training_knowledge
from src.models.coach_context import CoachContext, SourceMetadata
from src.models.coach_request import coach_request_from_input
from src.models.coach_response import CoachResponse
from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary, WeeklyAnalysis


_REFERENCE = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)
_TIMEZONE = ZoneInfo("Europe/Madrid")
_KNOWLEDGE = load_training_knowledge()
_EASY_PRIORITY = "TK_EASY_RUNNING_PRIORITY@1.0.0"


def build_offline_demo() -> tuple[CoachContext, CoachResponse, TrainingKnowledgePackage]:
    """Build one deterministic synthetic context and its validated sample output.

    This intentionally uses no provider, Strava client, filesystem data or
    user-entered request. The response text is fixed authored demo content.
    """
    request = coach_request_from_input(
        {
            "goal": {"goal_type": "HALF_MARATHON", "target_date": "2027-04-01"},
            "constraints": {"available_training_days_per_week": 4},
            "runner_context": None,
        },
        reference_datetime=_REFERENCE,
        athlete_timezone=_TIMEZONE,
    )

    distances = (24000, 26000, 28000, 30000)
    moving_times = (10800, 11700, 12600, 13500)
    first_week = date(2026, 9, 7)
    weeks = tuple(
        WeeklyAnalysis(
            week_start_date=first_week + timedelta(weeks=index),
            running_distance_meters=distance,
            running_activity_count=3,
            running_moving_time_seconds=moving_time,
            running_structure_by_type=tuple(
                TrainingTypeSummary(
                    training_type=kind,
                    activity_count=3 if kind is TrainingType.OTHER else 0,
                    distance_meters=distance if kind is TrainingType.OTHER else 0,
                    moving_time_seconds=moving_time if kind is TrainingType.OTHER else 0,
                )
                for kind in TrainingType
            ),
        )
        for index, (distance, moving_time) in enumerate(zip(distances, moving_times))
    )
    context = build_coach_context(
        request,
        weeks,
        reference_datetime=_REFERENCE,
        athlete_timezone=_TIMEZONE,
        source_metadata=SourceMetadata(
            source_name="Synthetic offline demo fixture",
            data_as_of=None,
            coverage="complete",
        ),
    )

    latest_week = "week:2026-09-28"
    trend = "trend:distance_absolute:2026-09-21:2026-09-28"
    sample_response = {
        "status": "guidance_available",
        "recommendation_period": {"start": "2026-10-12", "end_exclusive": "2026-10-19"},
        "current_state": {
            "text": "The synthetic sample includes three recorded Run activities in its latest supplied week.",
            "evidence_references": [latest_week],
            "knowledge_references": [],
        },
        "recent_evolution": {
            "text": "The synthetic weekly distance observations increased between the two cited weeks.",
            "evidence_references": [trend],
            "knowledge_references": [],
        },
        "relevant_evidence": [latest_week, "request:goal", "request:constraints", "temporal:context"],
        "next_week_recommendation": {
            "overall_direction": None,
            "recommended_running_days": None,
            "training_priorities": [
                {
                    "text": "A relaxed, conversational running priority is available as a general qualitative option.",
                    "evidence_references": [latest_week],
                    "knowledge_references": [_EASY_PRIORITY],
                }
            ],
            "reasoning": {
                "text": "This is a general qualitative priority and does not prescribe a volume direction or number of running days.",
                "evidence_references": [latest_week],
                "knowledge_references": [_EASY_PRIORITY],
            },
        },
        "limitations": [],
        "clarification_questions": [],
    }
    response = parse_coach_response(sample_response, context=context, knowledge=_KNOWLEDGE)
    return context, response, _KNOWLEDGE
