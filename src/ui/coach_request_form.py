"""Minimal Streamlit intake page for a validated, session-only CoachRequest."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.ai.coach_demo import build_offline_demo
from src.models.coach_request import coach_request_from_input
from src.ui.coach_response import render_coach_response


REQUEST_SESSION_KEY = "validated_coach_request"
DEMO_SESSION_KEY = "offline_coach_demo_output"
FORM_WIDGET_KEYS = (
    "target_date",
    "available_training_days",
    "athlete_timezone",
    "runner_context",
)


def _clear_request_form(session_state) -> None:
    """Clear the request, demo result and form values before rerunning."""
    session_state.pop(REQUEST_SESSION_KEY, None)
    session_state.pop(DEMO_SESSION_KEY, None)
    for key in FORM_WIDGET_KEYS:
        session_state.pop(key, None)


def _offline_demo_output() -> str:
    """Return a fully parsed, domain-validated and rendered demo result."""
    context, response, knowledge = build_offline_demo()
    return render_coach_response(response, context=context, knowledge=knowledge)


def render_request_page(ui=None) -> None:
    """Collect and validate request input without generating advice or fetching data."""
    if ui is None:
        import streamlit as ui

    ui.title("Strava AI Coach")
    ui.write(
        "Validating a request does not call the Coach or access Strava. "
        "The separate offline demo displays a pre-recorded synthetic response."
    )

    with ui.form("coach_request_form"):
        ui.text_input("Goal", value="Half marathon", disabled=True)
        target_date = ui.date_input(
            "Target date",
            value=date.today() + timedelta(days=30),
            key="target_date",
        )
        available_days = ui.number_input(
            "Available training days per week",
            min_value=0,
            max_value=7,
            value=0,
            step=1,
            key="available_training_days",
        )
        timezone_name = ui.text_input(
            "Your time zone (IANA name)",
            placeholder="For example, Europe/Madrid",
            key="athlete_timezone",
        )
        runner_context = ui.text_area(
            "Optional context for the Coach",
            max_chars=2000,
            help="Up to 2,000 characters. This text is not shown in the confirmation.",
            key="runner_context",
        )
        submitted = ui.form_submit_button("Validate request")

    ui.button(
        "Clear form and demo",
        key="clear_request_form",
        on_click=_clear_request_form,
        args=(ui.session_state,),
    )

    if ui.button("Show offline demo", key="show_offline_demo"):
        ui.session_state.pop(DEMO_SESSION_KEY, None)
        try:
            rendered_demo = _offline_demo_output()
        except ValueError:
            ui.error("The offline demo response could not be validated. No response was displayed.")
        else:
            ui.session_state[DEMO_SESSION_KEY] = rendered_demo

    if submitted:
        ui.session_state.pop(REQUEST_SESSION_KEY, None)
        try:
            if not timezone_name.strip():
                raise ValueError("Enter an IANA time zone, such as Europe/Madrid.")
            athlete_timezone = ZoneInfo(timezone_name.strip())
            request = coach_request_from_input(
                {
                    "goal": {
                        "goal_type": "HALF_MARATHON",
                        "target_date": target_date.isoformat(),
                    },
                    "constraints": {
                        "available_training_days_per_week": available_days,
                    },
                    "runner_context": runner_context,
                },
                reference_datetime=datetime.now(timezone.utc),
                athlete_timezone=athlete_timezone,
            )
        except (ValueError, ZoneInfoNotFoundError) as error:
            ui.error(str(error))
        else:
            ui.session_state[REQUEST_SESSION_KEY] = request
            ui.success("Request validated and kept in this session.")

    request = ui.session_state.get(REQUEST_SESSION_KEY)
    if request is not None:
        ui.subheader("Request summary")
        ui.write(f"Goal: {request.goal.goal_type.value.replace('_', ' ').title()}")
        ui.write(f"Target date: {request.goal.target_date.isoformat()}")
        ui.write(
            "Available training days per week: "
            f"{request.constraints.available_training_days_per_week}"
        )
        ui.info(
            "No training advice has been generated for this validated request, and no Strava data has been "
            "accessed. It remains separate from the offline demo."
        )

    demo_output = ui.session_state.get(DEMO_SESSION_KEY)
    if demo_output is not None:
        ui.subheader("Offline Coach demo")
        ui.info(
            "Demonstration with synthetic data; the response is pre-recorded, does not represent an athlete, "
            "and does not evaluate the model."
        )
        ui.text(demo_output)
