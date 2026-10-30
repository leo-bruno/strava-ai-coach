"""Tests for the deterministic evidence-context UI boundary."""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from src.analytics.weekly_analysis import weekly_analysis_from_activities
from src.models.activity import Activity
from src.ui.coach_evidence_context import (
    coach_evidence_context_is_available,
    coach_evidence_context_guidance,
    prepare_coach_evidence_context,
    render_coach_evidence_context,
)
from src.ui.strava_connection import ACCESS_TOKEN_KEY, EXPIRES_AT_KEY
from src.ui.strava_weekly_overview import (
    WEEKLY_ANALYSES_KEY,
    WEEKLY_AS_OF_KEY,
    WEEKLY_QUERY_TIMEZONE_KEY,
)


def _weeks(reference: datetime, zone: ZoneInfo):
    monday = reference.astimezone(zone).date() - timedelta(days=reference.astimezone(zone).weekday())
    start = monday - timedelta(weeks=7)
    distances = (0, 0, 0, 5000, 6000, 7000, 8000)
    return tuple(
        weekly_analysis_from_activities(
            [
                Activity(
                    id=index + 1,
                    name="Synthetic test Run",
                    sport_type="Run",
                    start_date=datetime.combine(
                        start + timedelta(weeks=index, days=1), time(hour=9), tzinfo=zone
                    ),
                    distance_meters=float(distances[index]),
                    moving_time_seconds=1500,
                )
            ] if distances[index] else [],
            reference_datetime=datetime.combine(start + timedelta(weeks=index, days=3), datetime.min.time(), tzinfo=zone),
            athlete_timezone=zone,
        )
        for index in range(7)
    )


def _session(reference: datetime, zone_name="Europe/Madrid"):
    zone = ZoneInfo(zone_name)
    session = {
        ACCESS_TOKEN_KEY: "opaque-test-token",
        EXPIRES_AT_KEY: int((reference + timedelta(hours=1)).timestamp()),
        WEEKLY_ANALYSES_KEY: _weeks(reference, zone),
        WEEKLY_AS_OF_KEY: reference - timedelta(minutes=1),
        WEEKLY_QUERY_TIMEZONE_KEY: zone_name,
    }
    return session


def _request_data(reference: datetime, zone: ZoneInfo):
    target = reference.astimezone(zone).date() + timedelta(days=30)
    return {
        "goal": {"goal_type": "HALF_MARATHON", "target_date": target.isoformat()},
        "constraints": {"available_training_days_per_week": 4},
        "runner_context": "PRIVATE CANARY context must not be rendered",
    }


def test_build_uses_one_supplied_reference_and_conservative_source_metadata():
    zone = ZoneInfo("Europe/Madrid")
    reference = datetime(2026, 10, 30, 10, tzinfo=timezone.utc)
    session = _session(reference)

    request, context = prepare_coach_evidence_context(
        session, _request_data(reference, zone), zone.key, reference
    )

    assert request.goal.target_date == context.reference_local_date + timedelta(days=30)
    assert context.reference_datetime is reference
    assert context.athlete_timezone is zone or context.athlete_timezone.key == zone.key
    assert context.source_metadata.source_name == "Strava weekly overview"
    assert context.source_metadata.data_as_of == session[WEEKLY_AS_OF_KEY]
    assert context.source_metadata.coverage == "incomplete"


@pytest.mark.parametrize(
    "mutate, timezone_name, expected",
    [
        (lambda data: data.pop(ACCESS_TOKEN_KEY), "Europe/Madrid", "Connect Strava again"),
        (lambda data: data.update({WEEKLY_QUERY_TIMEZONE_KEY: "UTC"}), "Europe/Madrid", "Reload the weekly overview"),
        (lambda data: data.update({WEEKLY_AS_OF_KEY: datetime(2026, 11, 1, tzinfo=timezone.utc)}), "Europe/Madrid", "Reload the Strava overview"),
        (lambda data: data.update({WEEKLY_ANALYSES_KEY: ()}), "Europe/Madrid", "Load the seven-week Strava overview"),
    ],
)
def test_preconditions_reject_stale_or_missing_evidence(mutate, timezone_name, expected):
    reference = datetime(2026, 10, 30, 10, tzinfo=timezone.utc)
    session = _session(reference)
    mutate(session)

    with pytest.raises(ValueError, match=expected):
        prepare_coach_evidence_context(
            session, _request_data(reference, ZoneInfo("Europe/Madrid")), timezone_name, reference
        )


def test_evidence_action_availability_requires_current_matching_weekly_data_and_token():
    reference = datetime(2026, 10, 30, 10, tzinfo=timezone.utc)
    session = _session(reference)

    assert coach_evidence_context_is_available(session, "Europe/Madrid", reference)
    assert not coach_evidence_context_is_available(session, "UTC", reference)
    session[EXPIRES_AT_KEY] = int(reference.timestamp())
    assert not coach_evidence_context_is_available(session, "Europe/Madrid", reference)


def test_evidence_guidance_distinguishes_disconnected_expired_missing_and_stale_overview():
    reference = datetime(2026, 10, 30, 10, tzinfo=timezone.utc)
    assert "Connect Strava" in coach_evidence_context_guidance({}, "Europe/Madrid", reference)

    session = _session(reference)
    assert "Load the seven completed-week overview" in coach_evidence_context_guidance(
        {ACCESS_TOKEN_KEY: "token", EXPIRES_AT_KEY: int((reference + timedelta(hours=1)).timestamp())},
        "Europe/Madrid",
        reference,
    )
    session[EXPIRES_AT_KEY] = int(reference.timestamp())
    assert "Reconnect Strava" in coach_evidence_context_guidance(session, "Europe/Madrid", reference)
    session[EXPIRES_AT_KEY] = int((reference + timedelta(hours=1)).timestamp())
    session[WEEKLY_QUERY_TIMEZONE_KEY] = "UTC"
    assert "Reload the weekly overview for the selected time zone" in coach_evidence_context_guidance(
        session, "Europe/Madrid", reference
    )
    session[EXPIRES_AT_KEY] = int((reference + timedelta(hours=1)).timestamp())
    session[WEEKLY_AS_OF_KEY] = reference + timedelta(seconds=1)
    assert "Reload the weekly overview for the selected time zone" in coach_evidence_context_guidance(
        session, "Europe/Madrid", reference
    )


class _FakeUI:
    def __init__(self):
        self.rendered = []

    def __getattr__(self, name):
        return lambda *args, **kwargs: self.rendered.append((name, args, kwargs))


def test_renderer_exposes_neutral_observations_without_user_report_or_context_dump():
    zone = ZoneInfo("Europe/Madrid")
    reference = datetime(2026, 10, 30, 10, tzinfo=timezone.utc)
    _, context = prepare_coach_evidence_context(
        _session(reference), _request_data(reference, zone), zone.key, reference
    )
    ui = _FakeUI()

    weeks = _session(reference)[WEEKLY_ANALYSES_KEY]
    render_coach_evidence_context(ui, context, weeks)

    rendered = repr(ui.rendered)
    assert "PRIVATE CANARY" not in rendered
    assert "Coach evidence context" in rendered
    assert "Deterministic evidence for Coach; no advice was generated." in rendered
    assert "coverage: incomplete" in rendered
    assert "Evidence limitations:" in rendered
    assert "Seven loaded weekly Run observations:" in rendered
    assert "Existing deterministic trends:" in rendered
    assert "Persistent weekly running distance increase" in rendered
    assert "Observed Run records after zero-Run records" in rendered
    assert "rest" not in rendered.lower()
    assert "readiness" not in rendered.lower()
