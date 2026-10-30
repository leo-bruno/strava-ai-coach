"""Minimal Streamlit intake page for a validated, session-only CoachRequest."""

from datetime import date, datetime, timedelta, timezone
import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.ai.coach_demo import build_offline_demo
from src.models.coach_request import coach_request_from_input
from src.ui.coach_response import render_coach_response
from src.ui.strava_connection import (
    ACCESS_TOKEN_KEY,
    ACTIVITY_PREVIEW_KEY,
    ATHLETE_PREVIEW_KEY,
    EXPIRES_AT_KEY,
    SCOPES_KEY,
    SELECTED_ACTIVITY_ID_KEY,
    TRAINING_ANALYSIS_KEY,
    clear_activity_analysis,
    clear_expired_activity_analysis,
    consume_oauth_callback,
    disconnect_from_strava,
    load_first_page_preview,
    load_selected_activity_analysis,
    start_authorization,
)


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

    query_params = getattr(ui, "query_params", None)
    callback_status = (
        consume_oauth_callback(ui.session_state, query_params)
        if query_params is not None
        else None
    )
    clear_expired_activity_analysis(ui.session_state)
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

    ui.subheader("Local Strava preview")
    ui.write(
        "Scopes requested: read (public profile access) and activity:read_all (all activity summaries, including "
        "private activities). The preview displays profile fields id, first name, last name and username, "
        "plus activity fields id, name, sport type, start date, distance in meters and moving time in seconds."
    )
    ui.info(
        "The preview is loaded only after you click the button below. It requests the profile and exactly the first "
        "page of up to 30 activity summaries. It is partial, is not synchronized, and is not sent to Analytics, Coach "
        "or OpenAI. The access token, profile preview and page remain in this browser session only; refresh tokens "
        "and durable activity storage are not used."
    )
    ui.warning(
        "This implementation follows personal-data authorization verbally communicated by the user; documentary "
        "confirmation is pending. This does not state that Strava published or verified an exception."
    )

    if callback_status is not None:
        callback_messages = {
            "connected": (ui.success, "Strava authorization was accepted with the required read scopes."),
            "access_denied": (ui.info, "Strava authorization was declined."),
            "missing_state": (ui.error, "The Strava callback did not include a valid state value. Start again."),
            "state_mismatch": (ui.error, "The Strava callback state did not match a pending authorization. Start again."),
            "expired": (ui.error, "The Strava authorization expired. Start again."),
            "replay": (ui.error, "This Strava callback was already used. Start again."),
            "multiple_state": (ui.error, "The Strava callback had multiple state values and was rejected."),
            "missing_code": (ui.error, "The Strava callback did not include an authorization code."),
            "insufficient_scope": (ui.error, "The granted Strava scopes are insufficient; approve both requested read scopes."),
            "invalid_callback": (ui.error, "The Strava callback parameters were invalid. Start again."),
            "exchange_failed": (ui.error, "Could not exchange the Strava authorization code. Start again."),
            "invalid_token_response": (ui.error, "Strava did not return a valid token with the required scopes."),
            "authorization_failed": (ui.error, "Strava authorization could not be completed. Start again."),
        }
        display, message = callback_messages.get(
            callback_status,
            (ui.error, "The Strava callback could not be validated. Start again."),
        )
        display(message)

    authorization_url = None
    if ui.button("Prepare Strava authorization", key="prepare_strava_authorization"):
        try:
            authorization_url = start_authorization(environ=os.environ)
        except RuntimeError:
            ui.error(
                "Configure STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET and STRAVA_REDIRECT_URI before starting. "
                "The redirect URI must be the local callback URL registered with Strava."
            )
        else:
            ui.caption("Open the link in the new tab, approve the requested scopes, then return to this app.")
    if authorization_url is not None:
        ui.link_button(
            "Open Strava authorization",
            authorization_url,
            key="open_strava_authorization",
        )

    if ui.session_state.get(ACCESS_TOKEN_KEY):
        ui.success("Strava is connected for this browser session.")
        scopes = ui.session_state.get(SCOPES_KEY, ())
        ui.caption(
            "Granted scopes: " + ", ".join(scopes)
            + ". Access token expires at Unix time "
            + str(ui.session_state.get(EXPIRES_AT_KEY, "unknown")) + "."
        )
        if ui.button("Load Strava preview", key="load_strava_preview"):
            clear_activity_analysis(ui.session_state)
            ui.session_state.pop(SELECTED_ACTIVITY_ID_KEY, None)
            ui.session_state.pop(ATHLETE_PREVIEW_KEY, None)
            ui.session_state.pop(ACTIVITY_PREVIEW_KEY, None)
            try:
                load_first_page_preview(ui.session_state)
            except ValueError as error:
                ui.error(str(error))
            except RuntimeError:
                ui.error("Could not load the Strava preview. Reconnect if the access token has expired.")

        athlete_preview = ui.session_state.get(ATHLETE_PREVIEW_KEY)
        if athlete_preview is not None:
            ui.write("Profile fields: id, firstname, lastname, username.")
            ui.json(athlete_preview)
            activity_preview = ui.session_state.get(ACTIVITY_PREVIEW_KEY, [])
            ui.write(
                "First activity page fields: id, name, sport_type, start_date, "
                "distance_meters, moving_time_seconds."
            )
            if activity_preview:
                ui.table(activity_preview)
            else:
                ui.info("No activities were returned on the first page.")

            run_activities = [
                activity
                for activity in activity_preview
                if activity.get("sport_type") == "Run"
            ]
            if run_activities:
                ui.info(
                    "Selecting a Run makes one detailed activity request and builds a single TrainingAnalysis with "
                    "the existing local Analytics logic. The result stays in this session and is not sent to Coach "
                    "or OpenAI."
                )
                run_ids = [activity["id"] for activity in run_activities]
                labels = {
                    activity["id"]: f"{activity['start_date']}: {activity['name']} (id {activity['id']})"
                    for activity in run_activities
                }
                ui.selectbox(
                    "Select a Run from this preview",
                    options=run_ids,
                    index=None,
                    placeholder="Choose a Run",
                    format_func=lambda activity_id: labels[activity_id],
                    key=SELECTED_ACTIVITY_ID_KEY,
                    on_change=clear_activity_analysis,
                    args=(ui.session_state,),
                )
                if ui.button("Analyze selected Run", key="analyze_selected_run"):
                    selected_id = ui.session_state.get(SELECTED_ACTIVITY_ID_KEY)
                    try:
                        load_selected_activity_analysis(ui.session_state, selected_id)
                    except ValueError as error:
                        ui.error(str(error))
                    except RuntimeError:
                        ui.error("Could not retrieve or analyze the selected Strava activity.")

                analysis = ui.session_state.get(TRAINING_ANALYSIS_KEY)
                if analysis is not None and analysis.activity.id == ui.session_state.get(
                    SELECTED_ACTIVITY_ID_KEY
                ):
                    ui.subheader("Selected Run analysis")
                    ui.json(
                        {
                            "activity": {
                                "id": analysis.activity.id,
                                "name": analysis.activity.name,
                                "start_date": analysis.activity.start_date.isoformat(),
                                "distance_meters": analysis.activity.distance_meters,
                                "moving_time_seconds": analysis.activity.moving_time_seconds,
                            },
                            "training_type": analysis.training_type.value,
                            "average_pace_seconds_per_km": analysis.average_pace_seconds_per_km,
                            "average_heart_rate_bpm": analysis.average_heart_rate_bpm,
                            "maximum_heart_rate_bpm": analysis.maximum_heart_rate_bpm,
                            "cadence_steps_per_minute": analysis.cadence_steps_per_minute,
                            "elevation_gain_meters": analysis.elevation_gain_meters,
                            "laps": [
                                {
                                    "distance_meters": lap.distance_meters,
                                    "moving_time_seconds": lap.moving_time_seconds,
                                    "pace_seconds_per_km": lap.pace_seconds_per_km,
                                    "average_heart_rate_bpm": lap.average_heart_rate_bpm,
                                    "maximum_heart_rate_bpm": lap.maximum_heart_rate_bpm,
                                    "cadence_steps_per_minute": lap.cadence_steps_per_minute,
                                }
                                for lap in analysis.laps
                            ],
                        }
                    )
            else:
                ui.info("The loaded first page contains no Run activities to analyze.")

        if ui.button("Disconnect Strava", key="disconnect_strava"):
            disconnect_status = disconnect_from_strava(ui.session_state, environ=os.environ)
            if disconnect_status == "revocation_requested":
                ui.info(
                    "The remote revoke request was accepted, but token revocation cannot be independently verified. "
                    "Check Strava settings to confirm access is removed."
                )
            elif disconnect_status in ("manual_revocation", "revocation_failed"):
                ui.warning(
                    "This browser session was cleared, but remote revocation was not confirmed. "
                    "Remove this app's access in Strava settings to ensure access is withdrawn."
                )
            else:
                ui.info("The local Strava session is clear.")
