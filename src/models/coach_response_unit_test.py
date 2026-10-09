"""Immutable response models and intentionally unspecified recommendations."""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from src.models.coach_response import (
    CoachResponse, CoachResponseStatus, GroundedStatement,
    NextWeekRecommendation, RecommendationPeriod,
)


STATEMENT = GroundedStatement("Relaxed conversational running.", ("week:2026-09-28",), ("TK_EASY_RUNNING_PRIORITY@1.0.0",))
PERIOD = RecommendationPeriod(date(2026, 10, 12), date(2026, 10, 19))
RECOMMENDATION = NextWeekRecommendation(None, None, (STATEMENT,), STATEMENT)
RESPONSE = CoachResponse(CoachResponseStatus.GUIDANCE_AVAILABLE, PERIOD, STATEMENT,
                         STATEMENT, ("week:2026-09-28",), RECOMMENDATION, (), ())


def test_preserves_exact_status_names():
    assert [status.value for status in CoachResponseStatus] == [
        "guidance_available", "clarification_required", "insufficient_support",
    ]


@pytest.mark.parametrize("record,field,value", [
    (PERIOD, "start", date(2026, 10, 5)),
    (STATEMENT, "text", "changed"),
    (RECOMMENDATION, "recommended_running_days", 3),
    (RESPONSE, "status", CoachResponseStatus.INSUFFICIENT_SUPPORT),
])
def test_models_are_immutable(record, field, value):
    with pytest.raises(FrozenInstanceError):
        setattr(record, field, value)


def test_direction_and_running_days_remain_unspecified_without_defaults():
    assert RECOMMENDATION.overall_direction is None
    assert RECOMMENDATION.recommended_running_days is None
    with pytest.raises(TypeError):
        STATEMENT.knowledge_references[0] = "changed"
