"""Calendar evidence selection using real domain fixtures and utilities."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from src.ai.coach_context import build_coach_context, insight_reference
from src.models.coach_context import EvidenceProvenance, SourceMetadata
from src.models.coach_request import coach_request_from_input
from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary, WeeklyAnalysis


REFERENCE = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)
ZONE = ZoneInfo("Europe/Madrid")
MONDAY = date(2026, 10, 5)
WEEK = timedelta(days=7)
COMPLETE = SourceMetadata("supplied Strava snapshot", REFERENCE, "complete")


def week(offset, distance=1000.0, count=1, moving_time=300):
    return WeeklyAnalysis(
        MONDAY + offset * WEEK, distance, count, moving_time,
        tuple(TrainingTypeSummary(kind, count if kind is TrainingType.EASY else 0,
                                  distance if kind is TrainingType.EASY else 0.0,
                                  moving_time if kind is TrainingType.EASY else 0)
              for kind in TrainingType),
    )


def request(reference=REFERENCE, zone=ZONE, context=None):
    return coach_request_from_input({
        "goal": {"goal_type": "HALF_MARATHON", "target_date": "2027-04-01"},
        "constraints": {"available_training_days_per_week": 4},
        "runner_context": context,
    }, reference_datetime=reference, athlete_timezone=zone)


def build(weeks=(), metadata=COMPLETE, context=None):
    return build_coach_context(request(context=context), weeks,
                               reference_datetime=REFERENCE, athlete_timezone=ZONE,
                               source_metadata=metadata)


def codes(context):
    return {limitation.code for limitation in context.limitations}


def vacation_history():
    return [week(-8, 32000), week(-7, 35000), week(-6, 37000), week(-5, 36000),
            week(-4, 0, 0, 0), week(-3, 0, 0, 0), week(-2, 0, 0, 0), week(-1, 8000)]


def test_exact_four_calendar_weeks_and_temporal_facts_without_backfill():
    context = build([week(i) for i in range(-6, 1)])
    assert [w.week_start_date for w in context.recent_weeks] == [MONDAY + i * WEEK for i in range(-4, 0)]
    assert context.recent_window_start == date(2026, 9, 7)
    assert context.recent_window_end_exclusive == MONDAY
    assert context.recommendation_start == date(2026, 10, 12)
    assert context.recommendation_end_exclusive == date(2026, 10, 19)
    assert context.reference_datetime == REFERENCE
    assert context.athlete_timezone == ZONE
    assert context.reference_local_date == date(2026, 10, 8)
    assert context.days_until_target_date == 175
    assert len(context.distance_changes) == 3


@pytest.mark.parametrize("reference,zone,current", [
    ("2026-10-04T21:59:59+00:00", "Europe/Madrid", "2026-09-28"),
    ("2026-10-04T22:00:00+00:00", "Europe/Madrid", "2026-10-05"),
    ("2026-10-05T00:00:00+00:00", "America/Los_Angeles", "2026-09-28"),
    ("2026-03-29T01:30:00+00:00", "Europe/Madrid", "2026-03-23"),
    ("2026-03-29T22:00:00+00:00", "Europe/Madrid", "2026-03-30"),
    ("2026-10-25T01:30:00+00:00", "Europe/Madrid", "2026-10-19"),
    ("2026-12-31T23:30:00+00:00", "Europe/Madrid", "2026-12-28"),
])
def test_local_monday_timezone_dst_and_year_boundaries(reference, zone, current):
    ref = datetime.fromisoformat(reference)
    tz = ZoneInfo(zone)
    context = build_coach_context(request(ref, tz), (), reference_datetime=ref, athlete_timezone=tz)
    monday = date.fromisoformat(current)
    assert context.recent_window_start == monday - 4 * WEEK
    assert context.recent_window_end_exclusive == monday
    assert context.recommendation_start == monday + WEEK
    assert context.recommendation_end_exclusive == monday + 2 * WEEK


def test_gaps_are_missing_not_zero_and_never_backfilled_or_bridged():
    context = build([week(-5), week(-4, 1000), week(-2, 3000), week(-1, 4000)])
    assert context.missing_recent_week_dates == (MONDAY - 3 * WEEK,)
    assert len(context.recent_weeks) == 3
    assert "MISSING_RECENT_WEEKS" in codes(context)
    assert [(c.previous_week_start_date, c.current_week_start_date) for c in context.distance_changes] == [(MONDAY - 2 * WEEK, MONDAY - WEEK)]


def test_zero_observations_and_undefined_percentages_are_retained():
    context = build([week(-4, 1000), week(-3, 0, 0, 0), week(-2, 0, 0, 0), week(-1, 8000)])
    assert [w.running_activity_count for w in context.recent_weeks] == [1, 0, 0, 1]
    assert [c.value for c in context.distance_changes] == [-1000, 0, 8000]
    assert [c.value for c in context.distance_percentage_changes] == [-100, None, None]
    assert [c.value for c in context.activity_count_changes] == [-1, 0, 1]
    assert [c.value for c in context.moving_time_changes] == [-300, 0, 300]
    assert len(context.observed_running_insights) == 1


def test_known_partial_completed_week_is_visible_but_breaks_all_comparisons():
    metadata = SourceMetadata("snapshot", REFERENCE, "complete", (MONDAY - 2 * WEEK,))
    context = build([week(i, (i + 5) * 1000) for i in range(-4, 0)], metadata)
    assert [w.known_partial for w in context.recent_weeks] == [False, False, True, False]
    assert len(context.distance_changes) == 1
    assert len(context.activity_count_changes) == 1
    assert len(context.moving_time_changes) == 1
    assert len(context.distance_percentage_changes) == 1
    assert context.distance_increase_insights == ()
    assert context.missing_recent_week_dates == ()
    assert "PARTIAL_COMPLETED_WEEKS" in codes(context)


def test_as_of_before_calendar_end_marks_completed_observation_partial():
    as_of = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    context = build([week(i) for i in range(-4, 1)], SourceMetadata("snapshot", as_of, "incomplete"))
    assert context.recent_weeks[-1].known_partial
    assert len(context.distance_changes) == 2
    assert context.open_week.data_as_of == as_of
    assert "SOURCE_COVERAGE_INCOMPLETE" in codes(context)


@pytest.mark.parametrize("as_of,partial", [
    ("2026-03-29T21:59:59+00:00", True),
    ("2026-03-29T22:00:00+00:00", False),
])
def test_data_as_of_uses_actual_local_monday_boundary_across_dst(as_of, partial):
    reference = datetime(2026, 3, 31, 12, tzinfo=timezone.utc)
    supplied = replace(week(-1), week_start_date=date(2026, 3, 23))
    context = build_coach_context(
        request(reference), [supplied], reference_datetime=reference,
        athlete_timezone=ZONE,
        source_metadata=SourceMetadata("snapshot", datetime.fromisoformat(as_of), "complete"),
    )
    assert context.recent_weeks[-1].known_partial is partial


def test_open_week_never_completes_a_pattern_or_return_episode():
    context = build([week(-3, 0, 0, 0), week(-2, 0, 0, 0), week(-1, 0, 0, 0), week(0, 8000)])
    assert context.open_week.calendar_status == "open"
    assert context.open_week.known_partial is True
    assert context.open_week.data_as_of == REFERENCE
    assert context.observed_running_insights == ()
    assert context.pre_interruption_background is None
    assert all(c.current_week_start_date < MONDAY for c in context.distance_changes)
    assert "OPEN_WEEK_PARTIAL" in codes(context)


def test_open_week_cannot_finish_persistent_increase():
    context = build([week(i, (i + 4) * 1000) for i in range(-3, 1)])
    assert context.distance_increase_insights == ()


@pytest.mark.parametrize("direction", [1, -1])
def test_insights_detect_before_window_filter_and_keep_concrete_fields(direction):
    history = [week(i, 10000 + direction * (i + 7) * 1000) for i in range(-7, 0)]
    context = build(history)
    insights = context.distance_increase_insights if direction == 1 else context.distance_decrease_insights
    assert [i.end_week_date for i in insights] == [MONDAY + i * WEEK for i in range(-4, 0)]
    assert insights[0].start_week_date == MONDAY - 7 * WEEK
    assert len(insights[0].weekly_distances_meters) == 4
    assert len(insights[0].distance_changes) == 3
    refs = {r.reference: r for r in context.evidence_references}
    assert refs[insight_reference(insights[-1])].temporal_relevance == "latest_completed_week"
    assert refs[insight_reference(insights[0])].temporal_relevance == "earlier_in_recent_window"


def test_old_insights_are_excluded_without_promoting_earlier_recent_endpoints():
    context = build([week(i, (i + 9) * 1000) for i in range(-8, -1)])
    assert all(i.end_week_date >= context.recent_window_start for i in context.distance_increase_insights)
    assert all(r.temporal_relevance != "latest_completed_week" for r in context.evidence_references)
    assert context.missing_recent_week_dates == (MONDAY - WEEK,)


def test_vacation_background_is_chronological_historical_and_bounded():
    context = build(vacation_history(), context="I was on vacation and returned last week.")
    background = context.pre_interruption_background
    assert [w.running_distance_meters for w in context.recent_weeks] == [0, 0, 0, 8000]
    assert [w.running_distance_meters for w in background.observations] == [32000, 35000, 37000, 36000]
    assert len(background.zero_run_weeks) == 3
    assert background.triggering_insight_reference == insight_reference(context.observed_running_insights[-1])


def test_maximal_zero_episode_extends_before_recent_window():
    context = build([week(-9)] + [week(i, 0, 0, 0) for i in range(-8, -1)] + [week(-1)])
    assert context.observed_running_insights[0].observed_zero_week_count == 7
    assert len(context.pre_interruption_background.zero_run_weeks) == 7
    assert context.pre_interruption_background.observations[0].week_start_date == MONDAY - 9 * WEEK


@pytest.mark.parametrize("stop", ["gap", "zero", "partial", "boundary", "limit"])
def test_background_stops_without_skipping_unsuitable_weeks(stop):
    history = vacation_history()
    metadata = COMPLETE
    if stop == "gap":
        history = [w for w in history if w.week_start_date != MONDAY - 7 * WEEK]
    elif stop == "zero":
        history[1] = week(-7, 0, 0, 0)
    elif stop == "partial":
        metadata = SourceMetadata("snapshot", REFERENCE, "complete", (MONDAY - 7 * WEEK,))
    elif stop == "boundary":
        history = history[2:]
    else:
        history = [week(-10), week(-9)] + history
    background = build(history, metadata).pre_interruption_background
    expected = [MONDAY - 6 * WEEK, MONDAY - 5 * WEEK] if stop != "limit" else [MONDAY + i * WEEK for i in range(-8, -4)]
    assert [w.week_start_date for w in background.observations] == expected


@pytest.mark.parametrize("stop", ["gap", "partial", "boundary"])
def test_unavailable_background_is_an_explicit_limitation(stop):
    history = vacation_history()
    metadata = COMPLETE
    if stop == "partial":
        metadata = SourceMetadata("snapshot", REFERENCE, "complete", (MONDAY - 5 * WEEK,))
    elif stop == "gap":
        history = [w for w in history if w.week_start_date != MONDAY - 5 * WEEK]
    else:
        history = history[4:]
    context = build(history, metadata)
    assert context.pre_interruption_background.observations == ()
    assert "PRE_INTERRUPTION_BACKGROUND_UNAVAILABLE" in codes(context)


def test_background_uses_only_most_recent_qualifying_episode():
    history = [week(-9), week(-8, 0, 0, 0), week(-7, 0, 0, 0), week(-6),
               week(-5), week(-4, 0, 0, 0), week(-3, 0, 0, 0), week(-2), week(-1)]
    context = build(history)
    assert context.pre_interruption_background.triggering_insight_reference == insight_reference(context.observed_running_insights[-1])
    assert [w.week_start_date for w in context.pre_interruption_background.observations] == [MONDAY - 6 * WEEK, MONDAY - 5 * WEEK]


def test_old_return_episode_does_not_trigger_background():
    context = build([week(-9), week(-8, 0, 0, 0), week(-7, 0, 0, 0), week(-6), week(-1)])
    assert context.observed_running_insights == ()
    assert context.pre_interruption_background is None


def test_two_recent_return_episodes_choose_latest_and_reuse_recent_week_reference():
    context = build([week(-7), week(-6, 0, 0, 0), week(-5, 0, 0, 0), week(-4),
                     week(-3, 0, 0, 0), week(-2, 0, 0, 0), week(-1)])
    assert len(context.observed_running_insights) == 2
    background = context.pre_interruption_background
    assert background.triggering_insight_reference == insight_reference(context.observed_running_insights[-1])
    assert [w.week_start_date for w in background.observations] == [MONDAY - 4 * WEEK]
    assert background.observations[0].reference == context.recent_weeks[0].reference
    assert sum(ref.reference == background.observations[0].reference for ref in context.evidence_references) == 1


def test_older_partial_history_limitations_remain_visible_when_they_break_insights():
    partial = MONDAY - 5 * WEEK
    metadata = SourceMetadata("snapshot", REFERENCE, "complete", (partial,))
    context = build([week(i, (i + 7) * 1000) for i in range(-6, -2)], metadata)
    assert context.distance_increase_insights == ()
    limitation = next(l for l in context.limitations if l.code == "PARTIAL_COMPLETED_WEEKS")
    assert limitation.week_dates == (partial,)


def test_known_partial_zero_week_breaks_episode_instead_of_becoming_zero_or_gap_fill():
    metadata = SourceMetadata("snapshot", REFERENCE, "complete", (MONDAY - 3 * WEEK,))
    context = build(vacation_history(), metadata)
    assert context.observed_running_insights == ()
    assert context.pre_interruption_background is None


def test_references_are_stable_deduplicated_and_do_not_change_with_input_order():
    history = vacation_history()
    first = build(history)
    second = build(list(reversed(history)))
    assert first == second
    refs = [r.reference for r in first.evidence_references]
    assert len(refs) == len(set(refs))
    assert "week:2026-09-28" in refs
    assert "trend:distance_absolute:2026-09-21:2026-09-28" in refs
    assert "request:goal" in refs and "request:constraints" in refs
    assert "request:runner_context" not in refs


def test_counts_only_all_six_categories_and_original_runner_context_provenance():
    report = "  I feel tired; I did not actually stop training.\n"
    context = build(vacation_history(), context=report)
    assert context.runner_context.runner_context == report
    assert [kind for kind, _ in context.recent_weeks[-1].training_type_counts] == list(TrainingType)
    assert sum(count for _, count in context.recent_weeks[-1].training_type_counts) == 1
    assert all(r.provenance in {EvidenceProvenance.USER_REPORT, EvidenceProvenance.DETERMINISTIC, EvidenceProvenance.STRAVA_OBSERVATION} for r in context.evidence_references)
    ref = next(r for r in context.evidence_references if r.reference == "request:runner_context")
    assert ref.provenance is EvidenceProvenance.USER_REPORT
    assert context.pre_interruption_background == build(vacation_history()).pre_interruption_background


def test_reuses_request_models_and_never_mutates_input_objects():
    history = vacation_history()
    original = deepcopy(history)
    identities = [id(w) for w in history]
    req = request(context="original")
    context = build_coach_context(req, history, reference_datetime=REFERENCE, athlete_timezone=ZONE)
    assert context.goal is req.goal
    assert context.constraints is req.constraints
    assert context.runner_context is req.context
    assert history == original
    assert [id(w) for w in history] == identities


def test_built_context_cannot_be_changed_into_a_different_recommendation_period():
    context = build(vacation_history())
    with pytest.raises(FrozenInstanceError):
        context.recommendation_start = MONDAY


def test_no_boilerplate_limitations_when_full_recent_evidence_and_metadata_are_supplied():
    assert build([week(i) for i in range(-4, 0)]).limitations == ()


def test_missing_metadata_stays_unknown_and_open_as_of_is_not_invented():
    context = build([week(0)], None)
    assert context.open_week.data_as_of is None
    assert "SOURCE_METADATA_UNAVAILABLE" in codes(context)
    assert "SOURCE_COVERAGE_UNKNOWN" in codes(context)
    assert len(context.missing_recent_week_dates) == 4


@pytest.mark.parametrize("metadata", [
    SourceMetadata(data_as_of=datetime(2026, 10, 8)),
    SourceMetadata(data_as_of=REFERENCE + timedelta(seconds=1)),
    SourceMetadata(coverage="assumed"), SourceMetadata(source_name=" "),
    SourceMetadata(partial_week_dates=(date(2026, 10, 6),)),
    SourceMetadata(partial_week_dates=(MONDAY, MONDAY)),
    SourceMetadata(partial_week_dates=[MONDAY]), "metadata",
])
def test_rejects_invalid_metadata_instead_of_inventing_it(metadata):
    with pytest.raises(ValueError):
        build(metadata=metadata)


def test_rejects_future_week_observations():
    with pytest.raises(ValueError, match="future calendar"):
        build([week(1)])


@pytest.mark.parametrize("history", [[week(-1), week(-1)], [WeeklyAnalysis(date(2026, 9, 29), 0, 0, 0, ())]])
def test_reuses_existing_normalization_errors(history):
    with pytest.raises(ValueError):
        build(history)


@pytest.mark.parametrize("reference,zone", [(datetime(2026, 10, 8), ZONE), (REFERENCE, "Europe/Madrid")])
def test_reference_and_timezone_must_be_explicit_valid_temporal_inputs(reference, zone):
    with pytest.raises(ValueError):
        build_coach_context(request(), (), reference_datetime=reference, athlete_timezone=zone)
