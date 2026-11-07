"""Route the dashboard, training plan and existing Coach/Strava sections."""

from datetime import datetime, timezone

from src.ui.coach_evidence_context import clear_coach_evidence_context
from src.ui.coach_request_form import REQUEST_SESSION_KEY, render_request_page
from src.ui.dashboard import (
    DASHBOARD_VIEW_KEY,
    NAVIGATION_KEY,
    PLAN_OPEN_KEY,
    render_dashboard_home,
    render_dashboard_styles,
    render_session_detail,
    render_sidebar,
    render_training_plan,
    set_dashboard_view,
)
from src.ui.strava_connection import clear_expired_activity_analysis, consume_oauth_callback
from src.ui.strava_dashboard import render_strava_dashboard
from src.ui.strava_weekly_overview import clear_expired_weekly_overview
from src.ui.timezone_preference import (
    ATHLETE_TIMEZONE_KEY,
    ATHLETE_TIMEZONE_LAST_APPLIED_KEY,
    detect_local_iana_timezone,
)
from src.ui.coach_request_form import GENERATED_COACH_OUTPUT_KEY


def render_app(ui=None) -> None:
    if ui is None:
        import streamlit as ui

    ui.set_page_config(page_title="Strava AI Coach", layout="wide")

    query_params = getattr(ui, "query_params", None)
    callback_status = (
        consume_oauth_callback(ui.session_state, query_params)
        if query_params is not None
        else None
    )
    clear_expired_activity_analysis(ui.session_state)
    clear_expired_weekly_overview(ui.session_state)
    if ATHLETE_TIMEZONE_KEY not in ui.session_state:
        ui.session_state[ATHLETE_TIMEZONE_KEY] = detect_local_iana_timezone()
    if ATHLETE_TIMEZONE_LAST_APPLIED_KEY not in ui.session_state:
        ui.session_state[ATHLETE_TIMEZONE_LAST_APPLIED_KEY] = ui.session_state.get(
            ATHLETE_TIMEZONE_KEY
        )
    elif ui.session_state.get(ATHLETE_TIMEZONE_KEY) != ui.session_state.get(
        ATHLETE_TIMEZONE_LAST_APPLIED_KEY
    ):
        ui.session_state.pop(REQUEST_SESSION_KEY, None)
        ui.session_state.pop(GENERATED_COACH_OUTPUT_KEY, None)
        clear_coach_evidence_context(ui.session_state)
        from src.ui.strava_weekly_overview import clear_weekly_overview

        clear_weekly_overview(ui.session_state)
        ui.session_state[ATHLETE_TIMEZONE_LAST_APPLIED_KEY] = ui.session_state.get(
            ATHLETE_TIMEZONE_KEY
        )
    if callback_status is not None:
        set_dashboard_view(ui.session_state, "Estadísticas")
    render_dashboard_styles(ui)
    current_view = ui.session_state.get(DASHBOARD_VIEW_KEY, "Inicio")
    if NAVIGATION_KEY not in ui.session_state:
        ui.session_state[NAVIGATION_KEY] = "Mi plan" if current_view == "Detalle" else current_view
    nav_view = render_sidebar(
        ui,
        view="Mi plan" if current_view == "Detalle" else current_view,
    )
    if current_view == "Detalle" and nav_view == "Mi plan":
        render_session_detail(ui)
        return
    # Radio interaction has already written NAVIGATION_KEY; only update the
    # independent route state here to avoid mutating a rendered widget key.
    ui.session_state[DASHBOARD_VIEW_KEY] = nav_view

    if nav_view == "Inicio":
        render_dashboard_home(ui)
    elif nav_view == "Mi plan":
        ui.session_state[PLAN_OPEN_KEY] = True
        render_training_plan(ui)
    elif nav_view == "Estadísticas":
        render_strava_dashboard(ui, callback_status)
    elif nav_view == "Coach":
        render_request_page(ui)
    else:
        set_dashboard_view(ui.session_state, "Inicio")
        render_dashboard_home(ui)
