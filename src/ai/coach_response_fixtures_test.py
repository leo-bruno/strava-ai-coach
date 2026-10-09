"""Handcrafted shared response fixtures, never imported by production code."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from src.ai.coach_context import build_coach_context
from src.models.coach_context import SourceMetadata
from src.models.coach_request import coach_request_from_input
from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary, WeeklyAnalysis


EASY = "TK_EASY_RUNNING_PRIORITY@1.0.0"
RETURN = "TK_RETURN_AFTER_REPORTED_INTERRUPTION@1.0.0"
FREQUENCY_LIMIT = "LIMIT_RUNNING_DAY_FREQUENCY@1.0.0"
LAST_WEEK = "week:2026-09-28"


def context_fixture(*, report=None, availability=4, vacation=False, open_week=False, metadata=True, decreasing=False, zero_weeks=3):
    reference = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)
    zone = ZoneInfo("Europe/Madrid")
    request = coach_request_from_input({
        "goal": {"goal_type": "HALF_MARATHON", "target_date": "2027-04-01"},
        "constraints": {"available_training_days_per_week": availability},
        "runner_context": report,
    }, reference_datetime=reference, athlete_timezone=zone)
    values = [32000, 35000, 37000, 36000] + [0] * zero_weeks + [8000] if vacation else [8000, 9000, 10000, 11000]
    if decreasing:
        values = list(reversed(values))
    offset = -len(values)
    if open_week:
        values.append(2000)
    weeks = []
    for index, distance in enumerate(values):
        count = 1 if distance else 0
        weeks.append(WeeklyAnalysis(
            date(2026, 10, 5) + timedelta(weeks=offset + index), distance, count, count * 300,
            tuple(TrainingTypeSummary(kind, count if kind is TrainingType.OTHER else 0,
                                      distance if kind is TrainingType.OTHER else 0,
                                      count * 300 if kind is TrainingType.OTHER else 0)
                  for kind in TrainingType),
        ))
    return build_coach_context(
        request, weeks, reference_datetime=reference, athlete_timezone=zone,
        source_metadata=SourceMetadata("Strava fixture", reference, "complete") if metadata else None,
    )


def statement(text, evidence=(), knowledge=()):
    return {"text": text, "evidence_references": list(evidence), "knowledge_references": list(knowledge)}


def response_fixture(status="guidance_available"):
    response = {
        "status": status,
        "recommendation_period": {"start": "2026-10-12", "end_exclusive": "2026-10-19"},
        "current_state": statement("The latest supplied week contains recorded running.", [LAST_WEEK]),
        "recent_evolution": statement("The supplied distance changed between consecutive weeks.", ["trend:distance_absolute:2026-09-21:2026-09-28"]),
        "relevant_evidence": [LAST_WEEK, "request:goal", "request:constraints"],
        "next_week_recommendation": None,
        "limitations": [],
        "clarification_questions": [],
    }
    if status == "guidance_available":
        response["next_week_recommendation"] = {
            "overall_direction": None, "recommended_running_days": None,
            "training_priorities": [statement("Prioritize relaxed running at which comfortable full conversation is possible.", [LAST_WEEK], [EASY])],
            "reasoning": statement("This is a general running priority, not a load-direction prescription.", [LAST_WEEK], [EASY]),
        }
    elif status == "clarification_required":
        response["clarification_questions"] = [statement(
            "Are you currently undertaking running training?", ["request:goal"], [EASY],
        )]
    elif status == "insufficient_support":
        response["limitations"] = [statement(
            "This package cannot select a numeric running-day count.", ["request:constraints"], [FREQUENCY_LIMIT],
        )]
    return response
