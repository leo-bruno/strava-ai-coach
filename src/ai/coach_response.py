"""Strict output parsing and structural checks, not semantic coaching proof."""

from dataclasses import fields
from datetime import date
import json
import re

from src.ai.coach_context import insight_reference
from src.ai.training_knowledge import TrainingKnowledgePackage, load_training_knowledge
from src.models.coach_context import CoachContext
from src.models.coach_response import (
    CoachResponse, CoachResponseStatus, GroundedStatement,
    NextWeekRecommendation, RecommendationPeriod,
)


_RETURN_ITEM = "TK_RETURN_AFTER_REPORTED_INTERRUPTION@1.0.0"


def _object(value: object, model: type, label: str) -> dict:
    if not isinstance(value, dict) or set(value) != {field.name for field in fields(model)}:
        raise ValueError(f"{label} must contain exactly the expected fields.")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonblank text.")
    return value


def _strings(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list of text references.")
    return tuple(_text(entry, label) for entry in value)


def _date(value: object) -> date:
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ValueError("Period dates must use YYYY-MM-DD.")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError("Period dates must be valid YYYY-MM-DD dates.") from None


def _statement(value: object) -> GroundedStatement:
    data = _object(value, GroundedStatement, "Statement")
    return GroundedStatement(
        _text(data["text"], "Statement text"),
        _strings(data["evidence_references"], "Evidence references"),
        _strings(data["knowledge_references"], "Knowledge references"),
    )


def _statements(value: object) -> tuple[GroundedStatement, ...]:
    if not isinstance(value, list):
        raise ValueError("Statement sections must be lists.")
    return tuple(_statement(entry) for entry in value)


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}.")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"Nonstandard JSON constant: {value}.")


def parse_coach_response(
    data: str | dict[str, object],
    *,
    context: CoachContext,
    knowledge: TrainingKnowledgePackage,
) -> CoachResponse:
    """Parse the exact schema and validate, or raise ValueError.

    Nullable fields must be explicitly null; list sections may be empty where
    status permits. No coercion, field dropping, repair or fallback response.
    There is no provider call. Source text is retained without summarization.
    """
    if isinstance(data, str):
        try:
            data = json.loads(data, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        except ValueError as error:
            raise ValueError(f"Invalid CoachResponse JSON: {error}") from error
    data = _object(data, CoachResponse, "CoachResponse")
    try:
        status = CoachResponseStatus(_text(data["status"], "Status"))
    except ValueError:
        raise ValueError("Unsupported CoachResponse status.") from None
    period = _object(data["recommendation_period"], RecommendationPeriod, "Recommendation period")
    recommendation = None
    if data["next_week_recommendation"] is not None:
        raw = _object(data["next_week_recommendation"], NextWeekRecommendation, "Recommendation")
        recommendation = NextWeekRecommendation(
            _statement(raw["overall_direction"]) if raw["overall_direction"] is not None else None,
            raw["recommended_running_days"], _statements(raw["training_priorities"]),
            _statement(raw["reasoning"]),
        )
    response = CoachResponse(
        status, RecommendationPeriod(_date(period["start"]), _date(period["end_exclusive"])),
        _statement(data["current_state"]), _statement(data["recent_evolution"]),
        _strings(data["relevant_evidence"], "Relevant evidence"), recommendation,
        _statements(data["limitations"]), _statements(data["clarification_questions"]),
    )
    return validate_coach_response(response, context=context, knowledge=knowledge)


def _references(values: object, allowed: set[str], label: str) -> None:
    if not isinstance(values, tuple):
        raise ValueError(f"{label} must be an immutable tuple.")
    for value in values:
        _text(value, label)
        if value not in allowed:
            raise ValueError(f"Unknown {label}: {value}.")
    if len(set(values)) != len(values):
        raise ValueError(f"Duplicate {label}.")


def _validate_statement(statement: object, evidence: set[str], knowledge: set[str]) -> None:
    if not isinstance(statement, GroundedStatement):
        raise ValueError("Expected a GroundedStatement.")
    _text(statement.text, "Statement text")
    _references(statement.evidence_references, evidence, "evidence reference")
    _references(statement.knowledge_references, knowledge, "knowledge reference")
    if not statement.evidence_references and not statement.knowledge_references:
        raise ValueError("Statements require explicit evidence or knowledge references.")


def _recommendation_authority(
    statement: GroundedStatement,
    *,
    actionable: set[str],
    return_evidence: set[str],
) -> None:
    if not statement.knowledge_references or not set(statement.knowledge_references) <= actionable:
        raise ValueError("Recommendations require actionable knowledge; application limitations are not authority.")
    if not statement.evidence_references:
        raise ValueError("Recommendations require supplied evidence references.")
    if _RETURN_ITEM in statement.knowledge_references:
        if "request:runner_context" not in statement.evidence_references or not return_evidence.intersection(statement.evidence_references):
            raise ValueError("Return guidance requires references to a recent qualifying Insight and RunnerContext.")


def validate_coach_response(
    response: CoachResponse,
    *,
    context: CoachContext,
    knowledge: TrainingKnowledgePackage,
) -> CoachResponse:
    """Validate handcrafted or parsed models against the actual context/package.

    Presence of an attributed report cannot prove that it confirms a break.
    Wording, actual applicability, forbidden prescriptions hidden in prose,
    whether questions can resolve an ambiguity, and completeness of reasoning
    remain semantic evaluation responsibilities. No keyword rule engine.
    """
    if not isinstance(response, CoachResponse) or not isinstance(response.status, CoachResponseStatus):
        raise ValueError("Expected CoachResponse with an allowed status enum.")
    if knowledge != load_training_knowledge():
        raise ValueError("Response validation requires the pinned approved knowledge package.")
    period = response.recommendation_period
    if (
        not isinstance(period, RecommendationPeriod)
        or type(period.start) is not date or type(period.end_exclusive) is not date
        or period.start != context.recommendation_start
        or period.end_exclusive != context.recommendation_end_exclusive
    ):
        raise ValueError("Recommendation period must match CoachContext exactly.")
    evidence = {ref.reference for ref in context.evidence_references}
    actionable = {item.reference for item in knowledge.actionable_items}
    all_knowledge = set(actionable)
    all_knowledge.update(f"{item.id}@{item.revision}" for item in knowledge.application_limitations)
    _validate_statement(response.current_state, evidence, all_knowledge)
    _validate_statement(response.recent_evolution, evidence, all_knowledge)
    _references(response.relevant_evidence, evidence, "relevant evidence reference")
    for section in (response.limitations, response.clarification_questions):
        if not isinstance(section, tuple):
            raise ValueError("Statement sections must be immutable tuples.")
        for statement in section:
            _validate_statement(statement, evidence, all_knowledge)

    recommendation = response.next_week_recommendation
    if response.status is CoachResponseStatus.GUIDANCE_AVAILABLE:
        if not isinstance(recommendation, NextWeekRecommendation) or response.clarification_questions:
            raise ValueError("guidance_available requires a recommendation and no clarification questions.")
    elif response.status is CoachResponseStatus.CLARIFICATION_REQUIRED:
        if recommendation is not None or not response.clarification_questions:
            raise ValueError("clarification_required needs questions and withholds recommendations.")
        for question in response.clarification_questions:
            if not actionable.intersection(question.knowledge_references):
                raise ValueError("Clarification must identify approved actionable knowledge it could enable.")
    else:
        if recommendation is not None or response.clarification_questions or not response.limitations:
            raise ValueError("insufficient_support requires a material limitation, no recommendation and no questions.")
    if recommendation is not None:
        days = recommendation.recommended_running_days
        if days is not None:
            if type(days) is not int or not 0 <= days <= 7 or days > context.constraints.available_training_days_per_week:
                raise ValueError("Running-day count must be an integer within availability (0–7).")
            raise ValueError("The current knowledge package supports no running-day count; leave it unset.")
        if context.constraints.available_training_days_per_week == 0:
            raise ValueError("Zero availability precludes an actionable running recommendation.")
        if not isinstance(recommendation.training_priorities, tuple):
            raise ValueError("Training priorities must be an immutable tuple.")
        if recommendation.overall_direction is None and not recommendation.training_priorities:
            raise ValueError("A recommendation needs direction or at least one training priority.")
        material = recommendation.training_priorities + (recommendation.reasoning,)
        if recommendation.overall_direction is not None:
            material += (recommendation.overall_direction,)
        return_evidence = {insight_reference(insight) for insight in context.observed_running_insights}
        for statement in material:
            _validate_statement(statement, evidence, all_knowledge)
            _recommendation_authority(statement, actionable=actionable, return_evidence=return_evidence)
        if recommendation.overall_direction is not None and _RETURN_ITEM not in recommendation.overall_direction.knowledge_references:
            raise ValueError("Easy-running priority alone does not support an overall direction.")
    return response
