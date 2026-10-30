"""Exercise the request page through Streamlit's real in-process app runner."""

from datetime import date, datetime, time, timedelta, timezone
import json
from urllib.parse import parse_qs, urlparse
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from src.models.coach_request import CoachRequest
from src.ui.coach_request_form import DEMO_SESSION_KEY, REQUEST_SESSION_KEY
from src.ui.strava_connection import (
    ACCESS_TOKEN_KEY,
    ACTIVITY_PREVIEW_KEY,
    ATHLETE_PREVIEW_KEY,
    EXPIRES_AT_KEY,
    SCOPES_KEY,
    SELECTED_ACTIVITY_ID_KEY,
    TRAINING_ANALYSIS_KEY,
    get_oauth_state_store,
)
from src.ui.strava_weekly_overview import (
    WEEKLY_ACTIVITIES_KEY,
    WEEKLY_ANALYSES_KEY,
    WEEKLY_AS_OF_KEY,
    WEEKLY_INSIGHTS_KEY,
    WEEKLY_PAGE_COUNT_KEY,
    WEEKLY_PERIOD_END_KEY,
    WEEKLY_PERIOD_START_KEY,
    WEEKLY_TIMEZONE_KEY,
)


APP_ENTRYPOINT = "../../src/main.py"


def run_app() -> AppTest:
    return AppTest.from_file(APP_ENTRYPOINT).run()


def visible_text(app: AppTest) -> str:
    display_element_lists = (
        app.title,
        app.subheader,
        app.markdown,
        app.text,
        app.success,
        app.info,
        app.caption,
        app.warning,
        app.error,
    )
    return "\n".join(
        str(element.value)
        for elements in display_element_lists
        for element in elements
    )


def submit_valid_request(app: AppTest, runner_context: str) -> date:
    target_date = date.today() + timedelta(days=45)
    app.date_input(key="target_date").set_value(target_date)
    app.number_input(key="available_training_days").set_value(4)
    app.text_input(key="athlete_timezone").set_value("Europe/Madrid")
    app.text_area(key="runner_context").set_value(runner_context)
    app.form_submit_button[0].click().run()
    return target_date


def seed_valid_weekly_overview(session_state) -> None:
    from datetime import time
    from zoneinfo import ZoneInfo

    from src.analytics.weekly_analysis import weekly_analysis_from_activities
    from src.ui.strava_weekly_overview import (
        WEEKLY_ACTIVITIES_KEY,
        WEEKLY_ANALYSES_KEY,
        WEEKLY_AS_OF_KEY,
        WEEKLY_INSIGHTS_KEY,
        WEEKLY_PAGE_COUNT_KEY,
        WEEKLY_PERIOD_END_KEY,
        WEEKLY_PERIOD_START_KEY,
    )

    zone = ZoneInfo("Europe/Madrid")
    as_of = datetime.now(timezone.utc).astimezone(zone)
    end_date = as_of.date() - timedelta(days=as_of.weekday())
    start_date = end_date - timedelta(weeks=7)
    start = datetime.combine(start_date, time.min, tzinfo=zone)
    weeks = tuple(
        weekly_analysis_from_activities(
            [],
            reference_datetime=datetime.combine(
                start_date + timedelta(weeks=offset, days=3),
                time(hour=12),
                tzinfo=zone,
            ),
            athlete_timezone=zone,
        )
        for offset in range(7)
    )
    session_state[WEEKLY_ACTIVITIES_KEY] = ()
    session_state[WEEKLY_ANALYSES_KEY] = weeks
    session_state[WEEKLY_INSIGHTS_KEY] = {
        "distance_increases": (),
        "distance_decreases": (),
        "observed_running_after_zero_weeks": (),
    }
    session_state[WEEKLY_PERIOD_START_KEY] = start
    session_state[WEEKLY_PERIOD_END_KEY] = datetime.combine(end_date, time.min, tzinfo=zone)
    session_state[WEEKLY_PAGE_COUNT_KEY] = 1
    session_state[WEEKLY_AS_OF_KEY] = as_of


def test_entrypoint_initial_render_has_no_streamlit_exception():
    app = run_app()

    assert not app.exception
    assert "Strava AI Coach" in visible_text(app)
    assert "Validating a request does not call the Coach or access Strava." in visible_text(app)
    assert not app.session_state.get(REQUEST_SESSION_KEY)


def test_valid_submission_stores_request_and_keeps_runner_context_private():
    app = run_app()
    private_context = "PRIVATE RUNNER CONTEXT 7f92a"

    target_date = submit_valid_request(app, private_context)

    assert not app.exception
    request = app.session_state[REQUEST_SESSION_KEY]
    assert isinstance(request, CoachRequest)
    assert request.goal.target_date == target_date
    assert request.constraints.available_training_days_per_week == 4
    assert request.context.runner_context == private_context
    assert "Request validated and kept in this session." in visible_text(app)
    assert "Request summary" in visible_text(app)
    assert f"Target date: {target_date.isoformat()}" in visible_text(app)
    assert private_context not in visible_text(app)


def test_invalid_resubmission_clears_previous_valid_request():
    app = run_app()
    submit_valid_request(app, "context retained in request state")
    assert REQUEST_SESSION_KEY in app.session_state

    app.text_input(key="athlete_timezone").set_value("Not/A_Timezone")
    app.form_submit_button[0].click().run()

    assert not app.exception
    assert REQUEST_SESSION_KEY not in app.session_state
    assert app.error
    assert "No time zone found" in visible_text(app)


def assert_default_form_values(app: AppTest) -> None:
    assert app.date_input(key="target_date").value == date.today() + timedelta(days=30)
    assert app.number_input(key="available_training_days").value == 0
    assert app.text_input(key="athlete_timezone").value == ""
    assert app.text_area(key="runner_context").value == ""


def test_clear_form_discards_unsubmitted_draft_and_restores_defaults():
    app = run_app()
    app.date_input(key="target_date").set_value(date.today() + timedelta(days=45))
    app.number_input(key="available_training_days").set_value(4)
    app.text_input(key="athlete_timezone").set_value("Not/A_Timezone")
    app.text_area(key="runner_context").set_value("PRIVATE DRAFT CONTEXT")

    app.button(key="clear_request_form").click().run()

    assert not app.exception
    assert REQUEST_SESSION_KEY not in app.session_state
    assert_default_form_values(app)
    assert "Request summary" not in visible_text(app)
    assert "PRIVATE DRAFT CONTEXT" not in visible_text(app)
    assert not app.success
    assert not app.error
    assert not app.session_state.get("runner_context")


def test_clear_form_removes_validated_request_and_restores_defaults():
    app = run_app()
    private_context = "PRIVATE VALIDATED CONTEXT"
    submit_valid_request(app, private_context)
    assert REQUEST_SESSION_KEY in app.session_state

    app.button(key="clear_request_form").click().run()

    assert not app.exception
    assert REQUEST_SESSION_KEY not in app.session_state
    assert_default_form_values(app)
    assert "Request summary" not in visible_text(app)
    assert private_context not in visible_text(app)
    assert not app.success
    assert not app.error


def test_offline_demo_is_separate_and_uses_its_fixed_synthetic_context():
    app = run_app()
    target_date = submit_valid_request(app, "This request must not be used by the demo.")
    assert app.session_state[REQUEST_SESSION_KEY].goal.target_date == target_date

    app.button(key="show_offline_demo").click().run()

    text = visible_text(app)
    assert not app.exception
    assert DEMO_SESSION_KEY in app.session_state
    assert "Demonstration with synthetic data" in text
    assert "pre-recorded" in text
    assert "does not represent an athlete" in text
    assert "does not evaluate the model" in text
    assert "2026-10-12 → 2026-10-19" in app.session_state[DEMO_SESSION_KEY]
    assert "2026-10-08" in app.session_state[DEMO_SESSION_KEY]
    assert "This request must not be used by the demo." not in text
    assert app.session_state[REQUEST_SESSION_KEY].goal.target_date == target_date


def test_clear_form_also_discards_the_offline_demo():
    app = run_app()
    app.button(key="show_offline_demo").click().run()
    assert DEMO_SESSION_KEY in app.session_state

    app.button(key="clear_request_form").click().run()

    assert not app.exception
    assert DEMO_SESSION_KEY not in app.session_state
    assert "Offline Coach demo" not in visible_text(app)


def test_invalid_demo_response_is_not_partially_displayed(monkeypatch):
    import src.ui.coach_request_form as form

    def invalid_demo():
        raise ValueError("invalid fixture")

    monkeypatch.setattr(form, "_offline_demo_output", invalid_demo)
    app = run_app()
    app.button(key="show_offline_demo").click().run()

    assert not app.exception
    assert DEMO_SESSION_KEY not in app.session_state
    assert app.error
    assert "No response was displayed" in visible_text(app)
    assert "Offline Coach demo" not in visible_text(app)


def test_initial_render_makes_no_strava_requests(monkeypatch):
    get_oauth_state_store.clear()
    mock_get = Mock()
    mock_post = Mock()
    monkeypatch.setattr("src.strava.client.requests.get", mock_get)
    monkeypatch.setattr("src.strava.auth.requests.post", mock_post)

    app = run_app()

    assert not app.exception
    mock_get.assert_not_called()
    mock_post.assert_not_called()
    assert "activity:read_all" in visible_text(app)
    assert "documentary confirmation is pending" in visible_text(app)
    assert "does not state that Strava published or verified an exception" in visible_text(app)


def test_oauth_callback_completes_in_second_streamlit_session_and_clears_url(monkeypatch):
    get_oauth_state_store.clear()
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("STRAVA_REDIRECT_URI", "http://localhost:8501")
    exchange = Mock(return_value={
        "access_token": "short-lived-access-token",
        "refresh_token": "refresh-token-must-not-be-stored",
        "expires_at": 2_100_000_000,
        "scope": "read activity:read_all",
    })
    monkeypatch.setattr("src.ui.strava_connection.exchange_authorization_code", exchange)

    first_session = run_app()
    first_session.button(key="prepare_strava_authorization").click().run(timeout=10)

    assert not first_session.exception
    authorization_url = first_session.link_button[0].url
    state = parse_qs(urlparse(authorization_url).query)["state"][0]
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8501" in authorization_url
    assert all(state not in str(value) for value in first_session.session_state.values())

    callback_session = AppTest.from_file(APP_ENTRYPOINT)
    callback_session.query_params["code"] = "one-time-authorization-code"
    callback_session.query_params["state"] = state
    callback_session.query_params["scope"] = "read,activity:read_all"
    callback_session.run(timeout=10)

    assert not callback_session.exception
    assert callback_session.query_params == {}
    assert callback_session.session_state[ACCESS_TOKEN_KEY] == "short-lived-access-token"
    assert callback_session.session_state[EXPIRES_AT_KEY] == 2_100_000_000
    assert callback_session.session_state[SCOPES_KEY] == ("read", "activity:read_all")
    assert "refresh-token-must-not-be-stored" not in str(callback_session.session_state)
    assert "one-time-authorization-code" not in str(callback_session.session_state)
    assert ATHLETE_PREVIEW_KEY not in callback_session.session_state
    exchange.assert_called_once_with("one-time-authorization-code")


def test_strava_preview_loads_only_after_click_and_requests_first_page(monkeypatch):
    from src.models.activity import Activity

    calls = []

    class FakeClient:
        def __init__(self, *, access_token):
            calls.append(("client", access_token))

        def get_athlete(self):
            calls.append(("athlete",))
            return {
                "id": 42,
                "firstname": "Runner",
                "lastname": "Example",
                "username": "runner",
                "weight": 62.0,
            }

        def get_activities(self, *, page, per_page):
            calls.append(("activities", page, per_page))
            return [
                Activity(1, "Morning run", "Run", datetime(2026, 10, 20, tzinfo=timezone.utc), 5000, 1500),
                Activity(2, "Commute", "Ride", datetime(2026, 10, 19, tzinfo=timezone.utc), 8000, 1200),
            ]

        def get_activity(self, activity_id):
            calls.append(("detail", activity_id))
            return {
                "id": activity_id,
                "name": "Morning run",
                "sport_type": "Run",
                "start_date": "2026-10-20T08:00:00Z",
                "distance": 5000,
                "moving_time": 1500,
                "laps": [{"distance": 5000, "moving_time": 1500}],
            }

    monkeypatch.setattr("src.ui.strava_connection.StravaClient", FakeClient)
    app = AppTest.from_file(APP_ENTRYPOINT)
    app.session_state[ACCESS_TOKEN_KEY] = "access-token"
    app.session_state[EXPIRES_AT_KEY] = 2_100_000_000
    app.session_state[SCOPES_KEY] = ("read", "activity:read_all")
    app.run(timeout=10)

    assert not app.exception
    assert not calls
    app.button(key="load_strava_preview").click().run(timeout=10)

    assert not app.exception
    assert calls == [("client", "access-token"), ("athlete",), ("activities", 1, 30)]
    assert app.session_state[ATHLETE_PREVIEW_KEY] == {
        "id": 42, "firstname": "Runner", "lastname": "Example", "username": "runner",
    }
    assert len(app.session_state[ACTIVITY_PREVIEW_KEY]) == 2
    text = visible_text(app)
    assert "First activity page fields" in text
    assert "partial" in text
    assert "not synchronized" in text
    assert "weight" not in text
    assert not any(call[0] == "detail" for call in calls)
    assert list(app.selectbox(key=SELECTED_ACTIVITY_ID_KEY).options) == [
        "2026-10-20T00:00:00+00:00: Morning run (id 1)"
    ]

    app.selectbox(key=SELECTED_ACTIVITY_ID_KEY).select(1).run(timeout=10)
    assert not app.exception
    assert not any(call[0] == "detail" for call in calls)

    app.button(key="analyze_selected_run").click().run(timeout=10)
    assert not app.exception
    assert calls.count(("detail", 1)) == 1
    analysis = app.session_state[TRAINING_ANALYSIS_KEY]
    assert analysis.activity.id == 1
    assert analysis.average_heart_rate_bpm is None
    assert analysis.laps[0].average_heart_rate_bpm is None
    rendered_analysis = json.loads(app.json[-1].value)
    assert rendered_analysis["average_heart_rate_bpm"] is None
    assert rendered_analysis["laps"][0]["average_heart_rate_bpm"] is None


def test_selecting_another_run_hides_old_result_and_preview_refresh_clears_analysis(monkeypatch):
    from src.models.activity import Activity

    class FakeClient:
        def __init__(self, *, access_token):
            pass

        def get_athlete(self):
            return {"id": 42}

        def get_activities(self, *, page, per_page):
            return [
                Activity(1, "First Run", "Run", datetime(2026, 10, 20, tzinfo=timezone.utc), 5000, 1500),
                Activity(2, "Second Run", "Run", datetime(2026, 10, 21, tzinfo=timezone.utc), 7000, 2100),
            ]

        def get_activity(self, activity_id):
            return {
                "id": activity_id,
                "name": f"Run {activity_id}",
                "sport_type": "Run",
                "start_date": "2026-10-20T08:00:00Z",
                "distance": 5000,
                "moving_time": 1500,
            }

    monkeypatch.setattr("src.ui.strava_connection.StravaClient", FakeClient)
    app = AppTest.from_file(APP_ENTRYPOINT)
    app.session_state[ACCESS_TOKEN_KEY] = "access-token"
    app.session_state[EXPIRES_AT_KEY] = 2_100_000_000
    app.session_state[SCOPES_KEY] = ("read", "activity:read_all")
    app.run(timeout=10)
    app.button(key="load_strava_preview").click().run(timeout=10)
    app.selectbox(key=SELECTED_ACTIVITY_ID_KEY).select(1).run(timeout=10)
    app.button(key="analyze_selected_run").click().run(timeout=10)
    assert TRAINING_ANALYSIS_KEY in app.session_state

    app.selectbox(key=SELECTED_ACTIVITY_ID_KEY).select(2).run(timeout=10)
    assert not app.exception
    assert TRAINING_ANALYSIS_KEY not in app.session_state
    assert "Selected Run analysis" not in visible_text(app)

    app.button(key="analyze_selected_run").click().run(timeout=10)
    assert TRAINING_ANALYSIS_KEY in app.session_state
    app.button(key="load_strava_preview").click().run(timeout=10)
    assert TRAINING_ANALYSIS_KEY not in app.session_state
    assert app.session_state[SELECTED_ACTIVITY_ID_KEY] is None


def test_failed_detail_request_does_not_leave_previous_analysis(monkeypatch):
    from src.models.activity import Activity

    class FakeClient:
        def __init__(self, *, access_token):
            pass

        def get_athlete(self):
            return {"id": 42}

        def get_activities(self, *, page, per_page):
            return [Activity(1, "Run", "Run", datetime(2026, 10, 20, tzinfo=timezone.utc), 5000, 1500)]

        def get_activity(self, _activity_id):
            raise RuntimeError("private provider diagnostic")

    monkeypatch.setattr("src.ui.strava_connection.StravaClient", FakeClient)
    app = AppTest.from_file(APP_ENTRYPOINT)
    app.session_state[ACCESS_TOKEN_KEY] = "access-token"
    app.session_state[EXPIRES_AT_KEY] = 2_100_000_000
    app.session_state[SCOPES_KEY] = ("read", "activity:read_all")
    app.run(timeout=10)
    app.button(key="load_strava_preview").click().run(timeout=10)
    app.selectbox(key=SELECTED_ACTIVITY_ID_KEY).select(1).run(timeout=10)
    app.session_state[TRAINING_ANALYSIS_KEY] = "stale-result"
    app.button(key="analyze_selected_run").click().run(timeout=10)

    assert not app.exception
    assert TRAINING_ANALYSIS_KEY not in app.session_state
    assert "private provider diagnostic" not in visible_text(app)
    assert "Selected Run analysis" not in visible_text(app)


def test_expired_session_hides_stored_activity_analysis_on_render():
    app = AppTest.from_file(APP_ENTRYPOINT)
    app.session_state[ACCESS_TOKEN_KEY] = "expired-access-token"
    app.session_state[EXPIRES_AT_KEY] = 1
    app.session_state[SCOPES_KEY] = ("read", "activity:read_all")
    app.session_state[ACTIVITY_PREVIEW_KEY] = [{
        "id": 1,
        "name": "Morning Run",
        "sport_type": "Run",
        "start_date": "2026-10-20T08:00:00+00:00",
        "distance_meters": 5000,
        "moving_time_seconds": 1500,
    }]
    app.session_state[TRAINING_ANALYSIS_KEY] = "stale-result"

    app.run(timeout=10)

    assert not app.exception
    assert TRAINING_ANALYSIS_KEY not in app.session_state
    assert "Selected Run analysis" not in visible_text(app)


def test_weekly_overview_loads_only_after_click_and_renders_seven_weeks_and_three_insights(monkeypatch):
    from src.ui.strava_weekly_overview import DEFAULT_ACTIVITIES_PAGE_SIZE

    requests = []

    class FakeClient:
        def __init__(self, *, access_token):
            assert access_token == "session-token"

        def get_activities(self, **kwargs):
            requests.append(kwargs)
            return []

    monkeypatch.setattr("src.ui.strava_weekly_overview.StravaClient", FakeClient)
    app = AppTest.from_file(APP_ENTRYPOINT)
    app.session_state[ACCESS_TOKEN_KEY] = "session-token"
    app.session_state[EXPIRES_AT_KEY] = 2_100_000_000
    app.session_state[SCOPES_KEY] = ("read", "activity:read_all")
    app.session_state[WEEKLY_TIMEZONE_KEY] = "Europe/Madrid"
    app.run(timeout=10)

    assert not app.exception
    assert not requests
    app.button(key="load_weekly_strava_overview").click().run(timeout=10)

    assert not app.exception
    assert len(requests) == 1
    assert requests[0]["page"] == 1
    assert requests[0]["per_page"] == DEFAULT_ACTIVITIES_PAGE_SIZE
    assert requests[0]["after"] < requests[0]["before"]
    assert len(app.session_state[WEEKLY_ANALYSES_KEY]) == 7
    assert app.session_state[WEEKLY_PERIOD_START_KEY].weekday() == 0
    assert app.session_state[WEEKLY_PERIOD_END_KEY].weekday() == 0
    assert app.session_state[WEEKLY_AS_OF_KEY].tzinfo is not None
    assert app.session_state[WEEKLY_PAGE_COUNT_KEY] == 1
    assert app.session_state[WEEKLY_ACTIVITIES_KEY] == ()
    assert set(app.session_state[WEEKLY_INSIGHTS_KEY]) == {
        "distance_increases", "distance_decreases", "observed_running_after_zero_weeks",
    }
    text = visible_text(app)
    assert "Local interval:" in text
    assert "Pages fetched: 1" in text
    assert "A zero Run count means no Run records were returned" in text
    assert "Persistent weekly running distance increase" in text
    assert "Persistent weekly running distance decrease" in text
    assert "Observed running after zero-Run weeks" in text
    assert "No detector output in the returned seven-week data." in text

    app.run(timeout=10)
    assert not app.exception
    assert len(requests) == 1


@pytest.mark.parametrize(
    ("weekly_distances", "expected_insight", "expected_field"),
    [
        ((5000, 6000, 7000, 8000, 0, 0, 0), "distance_increases", "distance_change_meters"),
        ((8000, 7000, 6000, 5000, 0, 0, 0), "distance_decreases", "distance_change_meters"),
        ((0, 0, 5000, 0, 0, 0, 0), "observed_running_after_zero_weeks", "observed_zero_week_count"),
    ],
)
def test_weekly_overview_renders_each_existing_insight_shape(
    monkeypatch, weekly_distances, expected_insight, expected_field
):
    from zoneinfo import ZoneInfo

    from src.models.activity import Activity

    zone = ZoneInfo("Europe/Madrid")
    local_now = datetime.now(timezone.utc).astimezone(zone)
    end_date = local_now.date() - timedelta(days=local_now.weekday())
    first_week_date = end_date - timedelta(weeks=7)
    activities = [
        Activity(
            id=index + 1,
            name="Morning Run",
            sport_type="Run",
            start_date=datetime.combine(
                first_week_date + timedelta(weeks=index, days=1),
                time(hour=9),
                tzinfo=zone,
            ).astimezone(timezone.utc),
            distance_meters=float(distance),
            moving_time_seconds=1500,
        )
        for index, distance in enumerate(weekly_distances)
        if distance > 0
    ]

    class FakeClient:
        def __init__(self, *, access_token):
            assert access_token == "session-token"

        def get_activities(self, **_kwargs):
            return activities

    monkeypatch.setattr("src.ui.strava_weekly_overview.StravaClient", FakeClient)
    app = AppTest.from_file(APP_ENTRYPOINT)
    app.session_state[ACCESS_TOKEN_KEY] = "session-token"
    app.session_state[EXPIRES_AT_KEY] = 2_100_000_000
    app.session_state[SCOPES_KEY] = ("read", "activity:read_all")
    app.session_state[WEEKLY_TIMEZONE_KEY] = "Europe/Madrid"
    app.run(timeout=10)

    app.button(key="load_weekly_strava_overview").click().run(timeout=10)

    assert not app.exception
    insights = app.session_state[WEEKLY_INSIGHTS_KEY]
    assert insights[expected_insight]
    rendered_json = [json.loads(element.value) for element in app.json]
    assert expected_field in str(rendered_json)
    text = visible_text(app)
    assert "Persistent weekly running distance increase" in text
    assert "Persistent weekly running distance decrease" in text
    assert "Observed running after zero-Run weeks" in text


def test_weekly_timezone_change_clears_old_output_without_fetching(monkeypatch):
    client = Mock()
    monkeypatch.setattr("src.ui.strava_weekly_overview.StravaClient", client)
    app = AppTest.from_file(APP_ENTRYPOINT)
    app.session_state[ACCESS_TOKEN_KEY] = "session-token"
    app.session_state[EXPIRES_AT_KEY] = 2_100_000_000
    app.session_state[SCOPES_KEY] = ("read", "activity:read_all")
    app.session_state[WEEKLY_TIMEZONE_KEY] = "Europe/Madrid"
    app.run(timeout=10)

    app.session_state[WEEKLY_ANALYSES_KEY] = "stale-analysis"
    app.session_state[WEEKLY_ACTIVITIES_KEY] = "stale-activities"
    app.text_input(key=WEEKLY_TIMEZONE_KEY).set_value("UTC").run(timeout=10)

    assert not app.exception
    assert WEEKLY_ANALYSES_KEY not in app.session_state
    assert WEEKLY_ACTIVITIES_KEY not in app.session_state
    assert "Local interval:" not in visible_text(app)
    client.assert_not_called()


def test_invalid_weekly_timezone_click_clears_old_output_without_strava_call(monkeypatch):
    client = Mock()
    monkeypatch.setattr("src.ui.strava_weekly_overview.StravaClient", client)
    app = AppTest.from_file(APP_ENTRYPOINT)
    app.session_state[ACCESS_TOKEN_KEY] = "session-token"
    app.session_state[EXPIRES_AT_KEY] = 2_100_000_000
    app.session_state[SCOPES_KEY] = ("read", "activity:read_all")
    app.session_state[WEEKLY_TIMEZONE_KEY] = "Not/A_Zone"
    app.run(timeout=10)

    app.session_state[WEEKLY_ANALYSES_KEY] = "stale-analysis"
    app.button(key="load_weekly_strava_overview").click().run(timeout=10)

    assert not app.exception
    assert WEEKLY_ANALYSES_KEY not in app.session_state
    assert client.call_count == 0
    assert "valid IANA time zone" in visible_text(app)


def test_weekly_expiry_on_rerun_hides_prior_output_without_fetching(monkeypatch):
    client = Mock()
    monkeypatch.setattr("src.ui.strava_weekly_overview.StravaClient", client)
    app = AppTest.from_file(APP_ENTRYPOINT)
    app.session_state[ACCESS_TOKEN_KEY] = "expired-session-token"
    app.session_state[EXPIRES_AT_KEY] = 1
    app.session_state[SCOPES_KEY] = ("read", "activity:read_all")
    app.session_state[WEEKLY_TIMEZONE_KEY] = "Europe/Madrid"
    app.session_state[WEEKLY_ANALYSES_KEY] = "stale-analysis"
    app.session_state[WEEKLY_ACTIVITIES_KEY] = "stale-activities"

    app.run(timeout=10)

    assert not app.exception
    assert WEEKLY_ANALYSES_KEY not in app.session_state
    assert WEEKLY_ACTIVITIES_KEY not in app.session_state
    assert "Local interval:" not in visible_text(app)
    client.assert_not_called()


def test_mid_pagination_ui_failure_discards_stale_and_partial_results(monkeypatch):
    from src.models.activity import Activity
    from src.ui.strava_weekly_overview import DEFAULT_ACTIVITIES_PAGE_SIZE

    class FakeClient:
        def __init__(self, *, access_token):
            pass

        def get_activities(self, *, page, **_kwargs):
            if page == 1:
                return [
                    Activity(
                        index,
                        "Run",
                        "Run",
                        datetime.now(timezone.utc),
                        5000,
                        1500,
                    )
                    for index in range(DEFAULT_ACTIVITIES_PAGE_SIZE)
                ]
            raise RuntimeError("private provider diagnostic")

    monkeypatch.setattr("src.ui.strava_weekly_overview.StravaClient", FakeClient)
    app = AppTest.from_file(APP_ENTRYPOINT)
    app.session_state[ACCESS_TOKEN_KEY] = "session-token"
    app.session_state[EXPIRES_AT_KEY] = 2_100_000_000
    app.session_state[SCOPES_KEY] = ("read", "activity:read_all")
    app.session_state[WEEKLY_TIMEZONE_KEY] = "Europe/Madrid"
    app.run(timeout=10)

    app.session_state[WEEKLY_ANALYSES_KEY] = "stale-analysis"
    app.session_state[WEEKLY_ACTIVITIES_KEY] = "stale-activities"
    app.button(key="load_weekly_strava_overview").click().run(timeout=10)

    assert not app.exception
    assert WEEKLY_ANALYSES_KEY not in app.session_state
    assert WEEKLY_ACTIVITIES_KEY not in app.session_state
    assert "private provider diagnostic" not in visible_text(app)
    assert "No partial result was kept" in visible_text(app)


def test_disconnect_clears_session_data_and_uses_best_effort_revocation(monkeypatch):
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test-client-secret")
    revoke = Mock()
    monkeypatch.setattr("src.ui.strava_connection.revoke_access_token", revoke)
    app = AppTest.from_file(APP_ENTRYPOINT)
    app.session_state[ACCESS_TOKEN_KEY] = "access-token"
    app.session_state[EXPIRES_AT_KEY] = 2_100_000_000
    app.session_state[SCOPES_KEY] = ("read", "activity:read_all")
    app.session_state[ATHLETE_PREVIEW_KEY] = {"id": 42}
    app.session_state[ACTIVITY_PREVIEW_KEY] = [{"id": 1}]
    app.session_state[TRAINING_ANALYSIS_KEY] = "stored-analysis"
    app.run()

    seed_valid_weekly_overview(app.session_state)

    app.button(key="disconnect_strava").click().run(timeout=10)

    assert not app.exception
    assert ACCESS_TOKEN_KEY not in app.session_state
    assert EXPIRES_AT_KEY not in app.session_state
    assert SCOPES_KEY not in app.session_state
    assert ATHLETE_PREVIEW_KEY not in app.session_state
    assert ACTIVITY_PREVIEW_KEY not in app.session_state
    assert TRAINING_ANALYSIS_KEY not in app.session_state
    assert WEEKLY_ANALYSES_KEY not in app.session_state
    assert WEEKLY_ACTIVITIES_KEY not in app.session_state
    assert "Local interval:" not in visible_text(app)
    assert revoke.call_args.args == ("access-token",)
    assert "cannot be independently verified" in visible_text(app)
