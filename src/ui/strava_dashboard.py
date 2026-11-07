"""Strava OAuth, weekly overview and activity detail section."""

import os

from src.ui.strava_connection import (
    ACCESS_TOKEN_KEY,
    ACTIVITY_PREVIEW_KEY,
    ATHLETE_PREVIEW_KEY,
    EXPIRES_AT_KEY,
    SCOPES_KEY,
    SELECTED_ACTIVITY_ID_KEY,
    TRAINING_ANALYSIS_KEY,
    clear_activity_analysis,
    disconnect_from_strava,
    load_first_page_preview,
    load_selected_activity_analysis,
    start_authorization,
)
from src.ui.coach_evidence_context import clear_coach_evidence_context
from src.ui.strava_weekly_overview import (
    WEEKLY_ACTIVITIES_KEY,
    WEEKLY_ANALYSES_KEY,
    WEEKLY_AS_OF_KEY,
    WEEKLY_INSIGHTS_KEY,
    WEEKLY_PAGE_COUNT_KEY,
    WEEKLY_PERIOD_END_KEY,
    WEEKLY_PERIOD_START_KEY,
    clear_weekly_overview,
    load_recent_weekly_overview,
)
from src.ui.coach_request_form import GENERATED_COACH_OUTPUT_KEY
from src.ui.timezone_preference import (
    ATHLETE_TIMEZONE_KEY,
    IANA_TIMEZONE_OPTIONS,
)

DISCONNECT_STATUS_KEY = "strava_disconnect_status"


def _render_callback_status(ui, callback_status: str | None) -> None:
    if callback_status is None:
        return
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


def _render_weekly_overview(ui) -> None:
    weekly_analyses = ui.session_state.get(WEEKLY_ANALYSES_KEY)
    if weekly_analyses is None:
        return
    period_start = ui.session_state[WEEKLY_PERIOD_START_KEY]
    period_end = ui.session_state[WEEKLY_PERIOD_END_KEY]
    as_of = ui.session_state[WEEKLY_AS_OF_KEY]
    ui.caption(
        f"Local interval: [{period_start.isoformat()}, {period_end.isoformat()}) · "
        f"As of {as_of.isoformat()} · Pages fetched: {ui.session_state[WEEKLY_PAGE_COUNT_KEY]}"
    )
    ui.info(
        "A zero Run count means no Run records were returned for that week. It does not establish "
        "inactivity, rest, a return to running, or the completeness of Strava history. Insights describe "
        "only these returned records."
    )
    ui.table(
        [
            {
                "Local week starting Monday": week.week_start_date.isoformat(),
                "Run records returned": week.running_activity_count,
                "Distance (meters)": week.running_distance_meters,
                "Moving time (seconds)": week.running_moving_time_seconds,
            }
            for week in weekly_analyses
        ],
        hide_index=True,
        alt="Seven complete local weeks of returned Strava Run activity totals",
    )
    insights = ui.session_state[WEEKLY_INSIGHTS_KEY]
    for key, label in (
        ("distance_increases", "Persistent weekly running distance increase"),
        ("distance_decreases", "Persistent weekly running distance decrease"),
    ):
        ui.write(label)
        results = insights[key]
        if results:
            ui.json(
                [
                    {
                        "start_week_date": result.start_week_date.isoformat(),
                        "end_week_date": result.end_week_date.isoformat(),
                        "weekly_distances_meters": result.weekly_distances_meters,
                        "weekly_activity_counts": result.weekly_activity_counts,
                        "distance_changes": [
                            {
                                "previous_week_start_date": change.previous_week_start_date.isoformat(),
                                "current_week_start_date": change.current_week_start_date.isoformat(),
                                "distance_change_meters": change.value,
                            }
                            for change in result.distance_changes
                        ],
                    }
                    for result in results
                ]
            )
        else:
            ui.caption("No detector output in the returned seven-week data.")
    ui.write("Observed running after zero-Run weeks")
    observed_results = insights["observed_running_after_zero_weeks"]
    if observed_results:
        ui.json(
            [
                {
                    "first_zero_week_date": result.first_zero_week_date.isoformat(),
                    "observed_zero_week_count": result.observed_zero_week_count,
                    "running_week_date": result.running_week_date.isoformat(),
                    "running_week_activity_count": result.running_week_activity_count,
                    "running_week_distance_meters": result.running_week_distance_meters,
                }
                for result in observed_results
            ]
        )
    else:
        ui.caption("No detector output in the returned seven-week data.")


def _render_activity_preview(ui) -> None:
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
    ui.subheader("Optional activity detail")
    ui.caption("Inspecting an activity is optional and is not required to load the weekly overview.")

    if not ui.session_state.get(ACCESS_TOKEN_KEY):
        return
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
    if athlete_preview is None:
        return
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

    run_activities = [activity for activity in activity_preview if activity.get("sport_type") == "Run"]
    if not run_activities:
        ui.info("The loaded first page contains no Run activities to analyze.")
        return
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
        try:
            load_selected_activity_analysis(
                ui.session_state, ui.session_state.get(SELECTED_ACTIVITY_ID_KEY)
            )
        except ValueError as error:
            ui.error(str(error))
        except RuntimeError:
            ui.error("Could not retrieve or analyze the selected Strava activity.")

    analysis = ui.session_state.get(TRAINING_ANALYSIS_KEY)
    if analysis is None or analysis.activity.id != ui.session_state.get(SELECTED_ACTIVITY_ID_KEY):
        return
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


def render_strava_dashboard(ui, callback_status: str | None = None) -> None:
    ui.title("Estadísticas")
    ui.caption("Acciones Strava manuales. Los datos solo se guardan en esta sesión.")
    _render_callback_status(ui, callback_status)
    with ui.form("strava_dashboard_form"):
        timezone_name = ui.selectbox(
            "Your time zone",
            options=IANA_TIMEZONE_OPTIONS,
            index=None,
            placeholder="Select an IANA time zone",
            key=ATHLETE_TIMEZONE_KEY,
        )
        authorization_submitted = ui.form_submit_button(
            "Prepare Strava authorization", key="prepare_strava_authorization", type="primary"
        )
        weekly_submitted = (
            ui.form_submit_button(
                "Load seven completed local weeks",
                key="load_weekly_strava_overview",
                type="secondary",
            )
            if ui.session_state.get(ACCESS_TOKEN_KEY)
            else False
        )
    authorization_url = None
    authorization_error = False
    weekly_load_error = False
    if authorization_submitted:
        try:
            authorization_url = start_authorization(
                environ=os.environ,
                timezone_preference=ui.session_state.get(ATHLETE_TIMEZONE_KEY),
            )
        except RuntimeError:
            authorization_error = True
    elif weekly_submitted:
        clear_coach_evidence_context(ui.session_state)
        ui.session_state.pop(GENERATED_COACH_OUTPUT_KEY, None)
        selected_timezone = ui.session_state.get(ATHLETE_TIMEZONE_KEY)
        if selected_timezone is None:
            clear_weekly_overview(ui.session_state)
            ui.error("Select an IANA time zone before loading weekly Strava data.")
        else:
            try:
                load_recent_weekly_overview(ui.session_state, selected_timezone)
            except ValueError as error:
                ui.error(str(error))
            except RuntimeError:
                weekly_load_error = True
    if authorization_error:
        ui.error(
            "Configure STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET and STRAVA_REDIRECT_URI before starting. "
            "The redirect URI must be the local callback URL registered with Strava."
        )
    elif authorization_url is not None:
        ui.caption("Open the link in the new tab, approve the requested scopes, then return to this app.")
        ui.link_button("Open Strava authorization", authorization_url, key="open_strava_authorization")
    if weekly_load_error:
        ui.error("Could not load all weekly Strava activity pages. No partial result was kept.")

    if ui.session_state.get(ACCESS_TOKEN_KEY) and ui.button("Disconnect Strava", key="disconnect_strava"):
        ui.session_state.pop(GENERATED_COACH_OUTPUT_KEY, None)
        ui.session_state[DISCONNECT_STATUS_KEY] = disconnect_from_strava(
            ui.session_state, environ=os.environ
        )
        ui.rerun()

    disconnect_status = ui.session_state.pop(DISCONNECT_STATUS_KEY, None)
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
    elif disconnect_status == "local_only":
        ui.info("The local Strava session is clear.")

    ui.header("Weekly overview")
    ui.write(
        "Load the seven most recent completed local calendar weeks. This requests activity summaries only; "
        "it does not request activity details or laps."
    )
    _render_weekly_overview(ui)
    _render_activity_preview(ui)
