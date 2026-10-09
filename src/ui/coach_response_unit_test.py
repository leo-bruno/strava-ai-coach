"""Rendering handcrafted validated responses without inventing guidance."""

from dataclasses import replace

import pytest

from src.ai.coach_context import insight_reference
from src.ai.coach_response import parse_coach_response
from src.ai.coach_response_fixtures_test import (
    EASY, RETURN, FREQUENCY_LIMIT, LAST_WEEK,
    context_fixture, response_fixture, statement,
)
from src.ai.training_knowledge import load_training_knowledge
from src.ui.coach_response import render_coach_response


def render(data, context):
    knowledge = load_training_knowledge()
    response = parse_coach_response(data, context=context, knowledge=knowledge)
    return render_coach_response(response, context=context, knowledge=knowledge)


def test_easy_priority_and_reasoning_are_rendered_verbatim_without_new_advice():
    data = response_fixture()
    output = render(data, context_fixture())
    assert "2026-10-12 → 2026-10-19 (end-exclusive; Europe/Madrid)" in output
    priority = data["next_week_recommendation"]["training_priorities"][0]["text"]
    assert output.count(priority) == 1
    assert data["next_week_recommendation"]["reasoning"]["text"] in output
    assert "Next-week direction:" not in output
    assert "Running days:" not in output
    assert "longer run" not in output
    assert "quality session" not in output
    assert "Strava-derived observation" in output
    assert "not distinct running days" in output
    assert "name-based category counts" in output
    assert "Simplifying the running jargon: Training pace" in output
    assert "Evidence limitation:" not in output
    assert "prerequisites" not in output  # No knowledge-package dump.


def test_historical_evidence_and_user_report_are_explicitly_attributed():
    report = "  I stopped training on vacation and returned last week.\n"
    context = context_fixture(vacation=True, report=report)
    data = response_fixture()
    background_ref = context.pre_interruption_background.observations[0].reference
    insight_ref = insight_reference(context.observed_running_insights[-1])
    return_refs = [insight_ref, "request:runner_context"]
    data["current_state"] = statement("Earlier recorded weekly volume is historical context.", [background_ref])
    data["next_week_recommendation"]["overall_direction"] = statement("Resume gradually and individually.", return_refs, [RETURN])
    data["next_week_recommendation"]["reasoning"] = statement("Your reported return provides context for the recorded episode.", return_refs, [RETURN])
    output = render(data, context)
    assert "Historical pre-interruption Strava observation (not current capacity or a target)" in output
    assert "32000 m" in output
    assert "RunnerContext (user-reported, unverified): " + report in output
    assert "not proof of an actual training interruption" in output
    assert "Next-week direction: Resume gradually and individually." in output
    assert "Gradual individualized return after a reported interruption" in output


@pytest.mark.parametrize("status", ["clarification_required", "insufficient_support"])
def test_withheld_recommendation_does_not_turn_into_a_default(status):
    output = render(response_fixture(status), context_fixture())
    assert "Next-week" not in output
    assert "Rationale:" not in output
    assert ("Clarification:" in output) == (status == "clarification_required")
    assert ("Limitation:" in output) == (status == "insufficient_support")
    if status == "insufficient_support":
        assert "Approved application limitation: Running-day frequency (not recommendation authority)" in output


def test_open_week_and_unavailable_source_metadata_remain_explicit():
    context = context_fixture(open_week=True, metadata=False)
    data = response_fixture()
    data["relevant_evidence"].append(context.open_week.reference)
    output = render(data, context)
    assert "Open-week Strava-derived observation (partial)" in output
    assert "data-as-of unknown" in output
    assert "Supplied source coverage is unknown" in output
    assert "Current-week evidence is partial" in output


def test_zero_base_percentage_is_undefined_not_missing_or_zero_percent():
    context = context_fixture(vacation=True)
    data = response_fixture()
    data["relevant_evidence"] += [
        "trend:distance_percentage:2026-09-21:2026-09-28",
        "trend:activity_count_absolute:2026-09-21:2026-09-28",
        "trend:moving_time_absolute:2026-09-21:2026-09-28",
    ]
    output = render(data, context)
    assert "undefined (previous distance zero)" in output
    assert "1 activities" in output
    assert "300 seconds" in output


@pytest.mark.parametrize("decreasing,kind", [(False, "increase"), (True, "decrease")])
def test_concrete_insight_label_is_factual_and_keeps_endpoint_relevance(decreasing, kind):
    context = context_fixture(decreasing=decreasing)
    insights = context.distance_decrease_insights if decreasing else context.distance_increase_insights
    data = response_fixture()
    data["relevant_evidence"].append(insight_reference(insights[0]))
    output = render(data, context)
    assert f"Recorded distance {kind} pattern" in output
    assert "latest_completed_week (date relevance only)" in output


def test_long_zero_episode_outside_recent_window_is_labelled_historical():
    context = context_fixture(vacation=True, zero_weeks=4)
    oldest_zero = context.pre_interruption_background.zero_run_weeks[0]
    data = response_fixture()
    data["relevant_evidence"].append(oldest_zero.reference)
    output = render(data, context)
    assert "Historical Strava-derived zero-Run episode observation" in output


def test_unused_reference_categories_are_omitted_without_fabricated_citations():
    data = response_fixture("insufficient_support")
    data["relevant_evidence"] = []
    data["current_state"] = statement("The package has no frequency prescription.", knowledge=[FREQUENCY_LIMIT])
    data["recent_evolution"] = statement("Recorded changes cannot supply a day count.", knowledge=[FREQUENCY_LIMIT])
    data["limitations"] = [statement("No approved count-selection rule exists.", knowledge=[FREQUENCY_LIMIT])]
    output = render(data, context_fixture())
    assert "Evidence references:" not in output
    assert "Knowledge references:" in output
    data["current_state"] = statement("The latest week contains supplied Run records.", [LAST_WEEK])
    data["recent_evolution"] = statement("These records alone cannot support the requested guidance.", [LAST_WEEK])
    data["limitations"] = [statement("No distinct-day distribution is established by activity counts.", [LAST_WEEK])]
    output = render(data, context_fixture())
    assert "Evidence references:" in output
    assert "Knowledge references:" not in output


def test_renderer_rejects_unvalidated_or_context_mismatched_models():
    context = context_fixture()
    knowledge = load_training_knowledge()
    response = parse_coach_response(response_fixture(), context=context, knowledge=knowledge)
    with pytest.raises(ValueError, match="supports no running-day count"):
        render_coach_response(
            replace(response, next_week_recommendation=replace(response.next_week_recommendation, recommended_running_days=3)),
            context=context, knowledge=knowledge,
        )
    with pytest.raises(ValueError, match="match CoachContext"):
        render_coach_response(response, context=replace(context, recommendation_start=context.recommendation_end_exclusive), knowledge=knowledge)
