"""Request input boundaries, without clocks, services or persistence."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from src.models.coach_request import (
    GoalType, RunnerContext, coach_request_from_input,
)


REFERENCE = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)
MADRID = ZoneInfo("Europe/Madrid")


def request_input():
    return {
        "goal": {"goal_type": "HALF_MARATHON", "target_date": "2026-10-09"},
        "constraints": {"available_training_days_per_week": 4},
    }


def build(data):
    return coach_request_from_input(data, reference_datetime=REFERENCE, athlete_timezone=MADRID)


@pytest.mark.parametrize("days", range(8))
def test_accepts_every_availability_without_converting_it_to_a_recommendation(days):
    data = request_input()
    data["constraints"]["available_training_days_per_week"] = days
    original = deepcopy(data)
    request = build(data)
    assert request.goal.goal_type is GoalType.HALF_MARATHON
    assert request.goal.target_date == date(2026, 10, 9)
    assert request.constraints.available_training_days_per_week == days
    assert request.context == RunnerContext(None)
    assert data == original


@pytest.mark.parametrize("value", [None, True, False, -1, 8, 3.5, 4.0, "4", [], {}])
def test_rejects_noninteger_or_out_of_range_availability(value):
    data = request_input()
    data["constraints"]["available_training_days_per_week"] = value
    with pytest.raises(ValueError, match="integer from 0 through 7"):
        build(data)


@pytest.mark.parametrize("value", [None, "MARATHON", "half_marathon", "", 1, True, []])
def test_only_half_marathon_is_supported(value):
    data = request_input()
    data["goal"]["goal_type"] = value
    with pytest.raises(ValueError, match="HALF_MARATHON"):
        build(data)


@pytest.mark.parametrize("value", [
    None, 20261009, date(2026, 10, 9), "", "20261009", "2026-1-09",
    "2026-10-9", "2026-W41-5", "2026-10-09T12:00:00Z", "2026-02-29",
    "2026-13-01", "0000-01-01", "2026-10-09\n", " 2026-10-09",
    "２０２６-１０-０９",
])
def test_requires_a_real_date_in_exact_text_format(value):
    data = request_input()
    data["goal"]["target_date"] = value
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        build(data)


@pytest.mark.parametrize("value", ["2026-10-08", "2026-10-07", "2020-01-01"])
def test_rejects_today_and_past_dates(value):
    data = request_input()
    data["goal"]["target_date"] = value
    with pytest.raises(ValueError, match="strictly after"):
        build(data)


@pytest.mark.parametrize("value", ["2026-10-09", "2028-02-29", "9999-12-31"])
def test_has_no_minimum_preparation_period_or_maximum_horizon(value):
    data = request_input()
    data["goal"]["target_date"] = value
    assert build(data).goal.target_date == date.fromisoformat(value)


@pytest.mark.parametrize("zone,target,valid", [
    ("Europe/Madrid", "2026-10-09", False),
    ("Europe/Madrid", "2026-10-10", True),
    ("America/Los_Angeles", "2026-10-09", True),
])
def test_date_comparison_uses_athlete_local_date_not_utc(zone, target, valid):
    data = request_input()
    data["goal"]["target_date"] = target
    kwargs = {
        "reference_datetime": datetime(2026, 10, 8, 23, 30, tzinfo=timezone.utc),
        "athlete_timezone": ZoneInfo(zone),
    }
    if valid:
        assert coach_request_from_input(data, **kwargs).goal.target_date == date.fromisoformat(target)
    else:
        with pytest.raises(ValueError, match="strictly after"):
            coach_request_from_input(data, **kwargs)


@pytest.mark.parametrize("reference", [
    datetime(2026, 3, 29, 0, 30, tzinfo=timezone.utc),
    datetime(2026, 3, 29, 1, 30, tzinfo=timezone.utc),
])
def test_spring_dst_transition_uses_the_same_local_calendar_date(reference):
    data = request_input()
    data["goal"]["target_date"] = "2026-03-30"
    assert coach_request_from_input(data, reference_datetime=reference, athlete_timezone=MADRID).goal.target_date == date(2026, 3, 30)


@pytest.mark.parametrize("reference", [None, "2026-10-08", datetime(2026, 10, 8)])
def test_reference_datetime_must_be_explicit_and_aware(reference):
    with pytest.raises(ValueError, match="timezone-aware"):
        coach_request_from_input(request_input(), reference_datetime=reference, athlete_timezone=MADRID)


@pytest.mark.parametrize("zone", [None, "Europe/Madrid", timezone.utc])
def test_timezone_boundary_follows_existing_explicit_zoneinfo_convention(zone):
    with pytest.raises(ValueError, match="ZoneInfo"):
        coach_request_from_input(request_input(), reference_datetime=REFERENCE, athlete_timezone=zone)


@pytest.mark.parametrize("section,field", [
    (None, "goal"), (None, "constraints"), ("goal", "goal_type"),
    ("goal", "target_date"), ("constraints", "available_training_days_per_week"),
])
def test_rejects_missing_required_data(section, field):
    data = request_input()
    del (data if section is None else data[section])[field]
    with pytest.raises(ValueError):
        build(data)


@pytest.mark.parametrize("section", ["goal", "constraints"])
@pytest.mark.parametrize("value", [None, [], "", 4])
def test_required_sections_must_be_objects(section, value):
    data = request_input()
    data[section] = value
    with pytest.raises(ValueError):
        build(data)


@pytest.mark.parametrize("section,field", [
    (None, "age"), ("goal", "target_time"), ("constraints", "recommended_running_days"),
])
def test_rejects_fields_outside_the_narrow_request_contract(section, field):
    data = request_input()
    (data if section is None else data[section])[field] = "unexpected"
    with pytest.raises(ValueError):
        build(data)


@pytest.mark.parametrize("data", [None, [], "request"])
def test_input_must_be_an_object(data):
    with pytest.raises(ValueError, match="Request"):
        build(data)


@pytest.mark.parametrize("value", [None, "", " \t\n", "\u2003\u00a0", " " * 2000])
def test_null_empty_and_whitespace_only_mean_no_context(value):
    data = request_input()
    data["runner_context"] = value
    assert build(data).context.runner_context is None


@pytest.mark.parametrize("value", [
    "  I returned after vacation.\n", "Estoy cansado 🏃🏽", "e\u0301", "é",
    "🏃" * 2000, " " + "a" * 1998 + "\n",
])
def test_preserves_original_unicode_wording_and_whitespace(value):
    data = request_input()
    data["runner_context"] = value
    assert build(data).context.runner_context == value
    assert data["runner_context"] == value


@pytest.mark.parametrize("value", ["a" * 2001, "🏃" * 2001, " " * 2001, " " + "a" * 2000])
def test_oversized_context_is_rejected_including_blank_input(value):
    data = request_input()
    data["runner_context"] = value
    with pytest.raises(ValueError, match="2,000"):
        build(data)


@pytest.mark.parametrize("value", [False, 2, [], {"injury": True}])
def test_context_cannot_be_preprocessed_structured_input(value):
    data = request_input()
    data["runner_context"] = value
    with pytest.raises(ValueError, match="text or null"):
        build(data)


def test_a_later_request_does_not_reuse_context():
    first = request_input()
    first["runner_context"] = "I stopped running."
    assert build(first).context.runner_context == first["runner_context"]
    assert build(request_input()).context.runner_context is None


@pytest.mark.parametrize("section,field,value", [
    (None, "context", RunnerContext("replacement")),
    ("goal", "target_date", date(2026, 12, 1)),
    ("constraints", "available_training_days_per_week", 2),
    ("context", "runner_context", "replacement"),
])
def test_request_and_its_parts_are_immutable(section, field, value):
    request = build(request_input())
    with pytest.raises(FrozenInstanceError):
        setattr(request if section is None else getattr(request, section), field, value)
