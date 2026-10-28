"""Exercise the request page through Streamlit's real in-process app runner."""

from datetime import date, timedelta

from streamlit.testing.v1 import AppTest

from src.models.coach_request import CoachRequest
from src.ui.coach_request_form import REQUEST_SESSION_KEY


APP_ENTRYPOINT = "../../src/main.py"


def run_app() -> AppTest:
    return AppTest.from_file(APP_ENTRYPOINT).run()


def visible_text(app: AppTest) -> str:
    display_element_lists = (
        app.title,
        app.subheader,
        app.markdown,
        app.success,
        app.info,
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


def test_entrypoint_initial_render_has_no_streamlit_exception():
    app = run_app()

    assert not app.exception
    assert "Strava AI Coach" in visible_text(app)
    assert "It does not generate advice or access Strava." in visible_text(app)
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
