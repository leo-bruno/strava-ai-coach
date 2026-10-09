"""Strict response boundaries; no LLM or semantic evaluator is invoked."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime
import json

import pytest

from src.ai.coach_context import insight_reference
from src.ai.coach_response import parse_coach_response, validate_coach_response
from src.ai.coach_response_fixtures_test import (
    EASY, RETURN, FREQUENCY_LIMIT, LAST_WEEK,
    context_fixture, response_fixture, statement,
)
from src.ai.training_knowledge import load_training_knowledge
from src.models.coach_response import CoachResponseStatus


@pytest.fixture
def context():
    return context_fixture()


@pytest.fixture
def knowledge():
    return load_training_knowledge()


def parse(data, context, knowledge):
    return parse_coach_response(data, context=context, knowledge=knowledge)


@pytest.mark.parametrize("status", [status.value for status in CoachResponseStatus])
def test_each_status_has_a_valid_handcrafted_representation(status, context, knowledge):
    data = response_fixture(status)
    original = deepcopy(data)
    response = parse(data, context, knowledge)
    assert response.status.value == status
    assert data == original
    assert parse(json.dumps(data), context, knowledge) == response
    assert validate_coach_response(response, context=context, knowledge=knowledge) is response


@pytest.mark.parametrize("status", [None, True, 0, "unknown", "GUIDANCE_AVAILABLE"])
def test_invalid_status_is_rejected(status, context, knowledge):
    data = response_fixture()
    data["status"] = status
    with pytest.raises(ValueError, match="status"):
        parse(data, context, knowledge)


@pytest.mark.parametrize("status,recommendation,question,limitation", [
    ("guidance_available", False, False, False),
    ("guidance_available", True, True, False),
    ("clarification_required", True, True, False),
    ("clarification_required", False, False, False),
    ("insufficient_support", True, False, True),
    ("insufficient_support", False, True, True),
    ("insufficient_support", False, False, False),
])
def test_status_section_consistency(status, recommendation, question, limitation, context, knowledge):
    data = response_fixture()
    data["status"] = status
    if not recommendation:
        data["next_week_recommendation"] = None
    data["clarification_questions"] = [statement("Are you running?", ["request:goal"], [EASY])] if question else []
    data["limitations"] = [statement("No count is supported.", ["request:constraints"], [FREQUENCY_LIMIT])] if limitation else []
    with pytest.raises(ValueError):
        parse(data, context, knowledge)


@pytest.mark.parametrize("key,value", [
    ("start", "2026-10-05"), ("end_exclusive", "2026-10-18"),
    ("start", "20261012"), ("start", "2026-02-30"), ("start", None),
    ("start", datetime(2026, 10, 12)), ("end_exclusive", "2026-10-19T00:00:00Z"),
])
def test_exact_period_and_text_date_format(key, value, context, knowledge):
    data = response_fixture()
    data["recommendation_period"][key] = value
    with pytest.raises(ValueError):
        parse(data, context, knowledge)


@pytest.mark.parametrize("path", [
    (), ("recommendation_period",), ("current_state",), ("next_week_recommendation",),
    ("next_week_recommendation", "reasoning"),
])
@pytest.mark.parametrize("operation", ["extra", "missing"])
def test_exact_field_schema_at_every_object_level(path, operation, context, knowledge):
    data = response_fixture()
    record = data
    for part in path:
        record = record[part]
    if operation == "extra":
        record["invented"] = "value"
    else:
        del record[next(iter(record))]
    with pytest.raises(ValueError, match="expected fields"):
        parse(data, context, knowledge)


@pytest.mark.parametrize("value", ["not json", "[]", "null", "{}", '{"status":"a","status":"b"}', '{"value":NaN}', '{"value":Infinity}', None, []])
def test_invalid_output_raises_without_creating_fallback(value, context, knowledge):
    with pytest.raises(ValueError):
        parse(value, context, knowledge)


@pytest.mark.parametrize("field,value", [
    ("text", " "), ("text", 7), ("evidence_references", "week:2026-09-28"),
    ("evidence_references", [True]), ("evidence_references", ["unknown"]),
    ("evidence_references", [LAST_WEEK, LAST_WEEK]), ("knowledge_references", ["TK_UNKNOWN@1.0.0"]),
    ("knowledge_references", [EASY, EASY]), ("knowledge_references", ["TK_EASY_RUNNING_PRIORITY@2.0.0"]),
])
def test_invalid_statement_values_or_references(field, value, context, knowledge):
    data = response_fixture()
    data["current_state"][field] = value
    with pytest.raises(ValueError):
        parse(data, context, knowledge)


@pytest.mark.parametrize("field", ["limitations", "clarification_questions", "relevant_evidence"])
def test_list_sections_require_exact_types(field, context, knowledge):
    data = response_fixture()
    data[field] = None
    with pytest.raises(ValueError):
        parse(data, context, knowledge)


def test_statements_cannot_hide_absent_traceability(context, knowledge):
    data = response_fixture()
    data["current_state"] = statement("Unsupported observation.")
    with pytest.raises(ValueError, match="explicit evidence"):
        parse(data, context, knowledge)


def test_unknown_relevant_evidence_is_rejected(context, knowledge):
    data = response_fixture()
    data["relevant_evidence"] = ["week:1900-01-01"]
    with pytest.raises(ValueError, match="Unknown relevant"):
        parse(data, context, knowledge)


@pytest.mark.parametrize("knowledge_refs", [[], [FREQUENCY_LIMIT], [EASY, FREQUENCY_LIMIT]])
def test_nonactionable_limitations_cannot_authorize_any_recommendation(knowledge_refs, context, knowledge):
    data = response_fixture()
    data["next_week_recommendation"]["training_priorities"][0]["knowledge_references"] = knowledge_refs
    with pytest.raises(ValueError, match="actionable knowledge"):
        parse(data, context, knowledge)


def test_recommendation_authority_needs_evidence_as_well_as_knowledge(context, knowledge):
    data = response_fixture()
    data["next_week_recommendation"]["reasoning"]["evidence_references"] = []
    with pytest.raises(ValueError, match="supplied evidence"):
        parse(data, context, knowledge)


@pytest.mark.parametrize("availability,days", [(4, 0), (4, 3), (4, 4), (7, 7)])
def test_structurally_valid_counts_still_have_no_approved_support(availability, days, knowledge):
    data = response_fixture()
    data["next_week_recommendation"]["recommended_running_days"] = days
    with pytest.raises(ValueError, match="supports no running-day count"):
        parse(data, context_fixture(availability=availability), knowledge)


@pytest.mark.parametrize("availability,days", [(0, 1), (4, 5), (7, 8), (4, -1), (4, True), (4, False), (4, 3.0), (4, 2.5), (4, "3")])
def test_count_types_and_availability_are_also_enforced(availability, days, knowledge):
    data = response_fixture()
    data["next_week_recommendation"]["recommended_running_days"] = days
    with pytest.raises(ValueError, match="integer within availability"):
        parse(data, context_fixture(availability=availability), knowledge)


def test_zero_availability_also_prevents_advice_hidden_behind_unset_count(knowledge):
    with pytest.raises(ValueError, match="Zero availability"):
        parse(response_fixture(), context_fixture(availability=0), knowledge)
    assert parse(response_fixture("insufficient_support"), context_fixture(availability=0), knowledge)


def test_easy_priority_does_not_require_or_authorize_direction(context, knowledge):
    data = response_fixture()
    response = parse(data, context, knowledge)
    assert response.next_week_recommendation.overall_direction is None
    assert response.next_week_recommendation.recommended_running_days is None
    data["next_week_recommendation"]["overall_direction"] = statement("Maintain load.", [LAST_WEEK], [EASY])
    with pytest.raises(ValueError, match="does not support an overall direction"):
        parse(data, context, knowledge)


def return_data(context):
    data = response_fixture()
    evidence = [insight_reference(context.observed_running_insights[-1]), "request:runner_context"]
    data["next_week_recommendation"] = {
        "overall_direction": statement("Resume gradually and individually.", evidence, [RETURN]),
        "recommended_running_days": None, "training_priorities": [],
        "reasoning": statement("Your reported interruption corresponds to the supplied recorded episode.", evidence, [RETURN]),
    }
    return data


def test_confirmed_return_references_report_and_qualifying_recent_insight(knowledge):
    context = context_fixture(report="I stopped training on vacation and resumed last week.", vacation=True)
    response = parse(return_data(context), context, knowledge)
    assert response.next_week_recommendation.overall_direction.knowledge_references == (RETURN,)


@pytest.mark.parametrize("missing", ["report", "insight"])
def test_return_authority_requires_both_structurally_checkable_references(missing, knowledge):
    context = context_fixture(report="I stopped training and resumed.", vacation=True)
    data = return_data(context)
    direction = data["next_week_recommendation"]["overall_direction"]
    direction["evidence_references"] = [direction["evidence_references"][0 if missing == "report" else 1]]
    with pytest.raises(ValueError, match="recent qualifying Insight and RunnerContext"):
        parse(data, context, knowledge)


def test_absent_actual_report_is_rejected_not_inferred_from_zero_weeks(knowledge):
    context = context_fixture(vacation=True)
    with pytest.raises(ValueError, match="Unknown evidence reference"):
        parse(return_data(context), context, knowledge)


def test_report_meaning_is_explicitly_reserved_for_semantic_evaluation(knowledge):
    context = context_fixture(report="I did not stop training; my Strava records are incomplete.", vacation=True)
    # Existence can be checked; genuine confirmation cannot be inferred by Python.
    # This response passes structure but must fail future semantic applicability evaluation.
    assert parse(return_data(context), context, knowledge)


def test_clarification_identifies_actionable_knowledge_not_unapproved_capability(context, knowledge):
    data = response_fixture("clarification_required")
    data["clarification_questions"][0]["knowledge_references"] = [FREQUENCY_LIMIT]
    with pytest.raises(ValueError, match="could enable"):
        parse(data, context, knowledge)


def test_empty_recommendation_is_not_material_guidance(context, knowledge):
    data = response_fixture()
    data["next_week_recommendation"]["training_priorities"] = []
    with pytest.raises(ValueError, match="at least one training priority"):
        parse(data, context, knowledge)


@pytest.mark.parametrize("change", ["root", "status", "period", "references", "statement", "section", "priorities"])
def test_direct_model_construction_cannot_bypass_validation(change, context, knowledge):
    response = parse(response_fixture(), context, knowledge)
    if change == "root":
        response = None
    elif change == "status":
        response = replace(response, status="guidance_available")
    elif change == "period":
        response = replace(response, recommendation_period=replace(response.recommendation_period, start=datetime(2026, 10, 12)))
    elif change == "references":
        response = replace(response, relevant_evidence=[LAST_WEEK])
    elif change == "statement":
        response = replace(response, current_state="not a statement")
    elif change == "section":
        response = replace(response, limitations=[])
    else:
        response = replace(response, next_week_recommendation=replace(response.next_week_recommendation, training_priorities=[]))
    with pytest.raises(ValueError):
        validate_coach_response(response, context=context, knowledge=knowledge)


def test_package_cannot_be_swapped_or_modified_in_memory(context, knowledge):
    modified = replace(knowledge, version="1.0.1")
    with pytest.raises(ValueError, match="pinned approved"):
        parse(response_fixture(), context, modified)
