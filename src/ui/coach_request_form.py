"""Minimal Streamlit intake page for a validated, session-only CoachRequest."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.models.coach_request import coach_request_from_input


REQUEST_SESSION_KEY = "validated_coach_request"
FORM_WIDGET_KEYS = (
    "target_date",
    "available_training_days",
    "athlete_timezone",
    "runner_context",
)


def _clear_request_form(session_state) -> None:
    """Clear the validated request and form values before Streamlit reruns."""
    session_state.pop(REQUEST_SESSION_KEY, None)
    for key in FORM_WIDGET_KEYS:
        session_state.pop(key, None)


def render_request_page(ui=None) -> None:
    """Collect and validate request input without generating advice or fetching data."""
    if ui is None:
        import streamlit as ui

    ui.title("Strava AI Coach")
    ui.write("This page collects a training request. It does not generate advice or access Strava.")

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
        "Clear form",
        key="clear_request_form",
        on_click=_clear_request_form,
        args=(ui.session_state,),
    )

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
        ui.info("No training advice has been generated, and no Strava data has been accessed.")
