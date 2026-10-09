"""Render validated Coach output as plain text, without adding advice."""

from src.ai.coach_context import insight_reference
from src.ai.coach_response import validate_coach_response
from src.ai.training_knowledge import TrainingKnowledgePackage
from src.models.coach_context import CoachContext
from src.models.coach_response import CoachResponse, GroundedStatement


def _evidence_labels(context: CoachContext) -> dict[str, str]:
    labels = {
        "request:goal": f"Runner goal (user-reported): {context.goal.goal_type.value}; target {context.goal.target_date}",
        "request:constraints": f"Runner availability (user-reported maximum): {context.constraints.available_training_days_per_week} days; not a recommended count",
        "temporal:context": f"Local calendar ({context.athlete_timezone.key}): reference {context.reference_local_date}; recent window {context.recent_window_start} to {context.recent_window_end_exclusive} exclusive; {context.days_until_target_date} days until target, without a training-phase inference",
    }
    if context.runner_context.runner_context is not None:
        labels["request:runner_context"] = "RunnerContext (user-reported, unverified): " + context.runner_context.runner_context
    background = context.pre_interruption_background
    historical_dates = {w.week_start_date for w in background.observations} if background is not None else set()
    recent_dates = {w.week_start_date for w in context.recent_weeks}
    weeks = context.recent_weeks
    if context.open_week is not None:
        weeks += (context.open_week,)
    if background is not None:
        weeks += background.observations + background.zero_run_weeks
    for week in weeks:
        if week.calendar_status == "open":
            role = "Open-week Strava-derived observation (partial)"
        elif week.week_start_date in historical_dates:
            role = "Historical pre-interruption Strava observation (not current capacity or a target)"
        elif week.week_start_date not in recent_dates:
            role = "Historical Strava-derived zero-Run episode observation"
        else:
            role = "Recent Strava-derived observation"
        partial = "; known partial data" if week.known_partial else ""
        as_of = str(week.data_as_of) if week.data_as_of is not None else "unknown"
        counts = ", ".join(f"{kind.value}: {count}" for kind, count in week.training_type_counts)
        labels[week.reference] = (
            f"{role}: week {week.week_start_date}; {week.running_distance_meters} m; "
            f"{week.running_activity_count} recorded Run activities (not distinct running days); "
            f"{week.running_moving_time_seconds} moving seconds{partial}; data-as-of {as_of}; "
            f"name-based category counts [{counts}], not measured effort"
        )
    for kind, changes, unit in (
        ("distance_absolute", context.distance_changes, "m"),
        ("distance_percentage", context.distance_percentage_changes, "%"),
        ("activity_count_absolute", context.activity_count_changes, "activities"),
        ("moving_time_absolute", context.moving_time_changes, "seconds"),
    ):
        for change in changes:
            ref = f"trend:{kind}:{change.previous_week_start_date}:{change.current_week_start_date}"
            value = "undefined (previous distance zero)" if change.value is None else f"{change.value} {unit}"
            labels[ref] = f"Deterministic {kind} change, {change.previous_week_start_date} → {change.current_week_start_date}: {value}"
    relevance = {r.reference: r.temporal_relevance for r in context.evidence_references}
    for insight in context.distance_increase_insights + context.distance_decrease_insights:
        ref = insight_reference(insight)
        direction = "increase" if insight in context.distance_increase_insights else "decrease"
        labels[ref] = f"Recorded distance {direction} pattern, {insight.start_week_date} → {insight.end_week_date}; three strict transitions; {relevance[ref]} (date relevance only)"
    for insight in context.observed_running_insights:
        ref = insight_reference(insight)
        labels[ref] = (
            f"Recorded pattern: {insight.observed_zero_week_count} zero-Run observations from "
            f"{insight.first_zero_week_date}, followed by {insight.running_week_activity_count} "
            f"Run activities in week {insight.running_week_date}; {relevance[ref]} (date relevance only); "
            "not proof of an actual training interruption"
        )
    return labels


def _knowledge_labels(knowledge: TrainingKnowledgePackage) -> dict[str, str]:
    sources = {source.id: source for source in knowledge.sources}
    titles = {
        "TK_RETURN_AFTER_REPORTED_INTERRUPTION": "Gradual individualized return after a reported interruption",
        "TK_EASY_RUNNING_PRIORITY": "Qualitative relaxed/conversational running priority",
    }
    labels = {
        item.reference: titles[item.id] + "; " + item.reference + "; reviewed sources: "
        + ", ".join(sources[ref].title for ref in item.source_ids)
        for item in knowledge.actionable_items
    }
    labels.update({
        f"{item.id}@{item.revision}": f"Approved application limitation: {item.topic} (not recommendation authority); {item.id}@{item.revision}"
        for item in knowledge.application_limitations
    })
    return labels


def render_coach_response(
    response: CoachResponse,
    *,
    context: CoachContext,
    knowledge: TrainingKnowledgePackage,
) -> str:
    """Render existing text and factual labels only, without defaults.

    Input must already pass the response boundary. Recheck with the same
    validator to prevent passive dataclass construction or a mismatched context
    bypassing that boundary. This is structural validation, not semantic proof.
    Only used references are resolved; URLs are never opened. Material context
    limitations remain visible even if omitted from generated limitations.
    """
    validate_coach_response(response, context=context, knowledge=knowledge)
    used_evidence = dict.fromkeys(response.relevant_evidence)
    used_knowledge = {}

    def statement_text(statement: GroundedStatement) -> str:
        used_evidence.update(dict.fromkeys(statement.evidence_references))
        used_knowledge.update(dict.fromkeys(statement.knowledge_references))
        refs = statement.evidence_references + statement.knowledge_references
        return statement.text + " [" + "; ".join(refs) + "]"

    period = response.recommendation_period
    lines = [
        f"Recommendation period: {period.start} → {period.end_exclusive} (end-exclusive; {context.athlete_timezone.key})",
        f"Status: {response.status.value}",
        "Current state: " + statement_text(response.current_state),
        "Recent evolution: " + statement_text(response.recent_evolution),
    ]
    recommendation = response.next_week_recommendation
    if recommendation is not None:
        if recommendation.overall_direction is not None:
            lines.append("Next-week direction: " + statement_text(recommendation.overall_direction))
        for priority in recommendation.training_priorities:
            lines.append("Next-week priority: " + statement_text(priority))
        lines.append("Rationale: " + statement_text(recommendation.reasoning))
    for limitation in response.limitations:
        lines.append("Limitation: " + statement_text(limitation))
    for limitation in context.limitations:
        dates = "; weeks: " + ", ".join(map(str, limitation.week_dates)) if limitation.week_dates else ""
        lines.append("Evidence limitation: " + limitation.detail + dates)
    for question in response.clarification_questions:
        lines.append("Clarification: " + statement_text(question))
    evidence_labels = _evidence_labels(context)
    knowledge_labels = _knowledge_labels(knowledge)
    if used_evidence:
        lines.append("Evidence references:")
        lines.extend(f"- {ref}: {evidence_labels[ref]}" for ref in used_evidence)
    if used_knowledge:
        lines.append("Knowledge references:")
        lines.extend(f"- {ref}: {knowledge_labels[ref]}" for ref in used_knowledge)
    return "\n".join(lines)
