"""Route the Strava-backed dashboard, statistics and Coach sections."""

from datetime import datetime, timezone

from src.ui.coach_evidence_context import clear_coach_evidence_context
from src.ui.coach_request_form import REQUEST_SESSION_KEY, render_request_page
from src.ui.dashboard import (
    DASHBOARD_VIEW_KEY,
    NAVIGATION_KEY,
    render_dashboard_home,
    render_dashboard_styles,
    render_sidebar,
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

    ui.set_page_config(page_title="Runner Coach", layout="wide")
    _render_accessible_control_focus_styles(ui)

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
    if DASHBOARD_VIEW_KEY not in ui.session_state:
        set_dashboard_view(ui.session_state, "Inicio")
    current_view = ui.session_state.get(DASHBOARD_VIEW_KEY, "Inicio")
    if current_view not in ("Inicio", "Estadísticas", "Coach"):
        current_view = "Inicio"
        ui.session_state[DASHBOARD_VIEW_KEY] = current_view
    if NAVIGATION_KEY not in ui.session_state:
        ui.session_state[NAVIGATION_KEY] = current_view
    elif ui.session_state.get(NAVIGATION_KEY) not in ("Inicio", "Estadísticas", "Coach"):
        ui.session_state[NAVIGATION_KEY] = current_view
    if current_view == "Inicio":
        render_dashboard_styles(ui)
        render_dashboard_home(ui)
        return

    nav_view = render_sidebar(ui, view=current_view)
    ui.session_state[DASHBOARD_VIEW_KEY] = nav_view
    if nav_view == "Inicio":
        render_dashboard_styles(ui)
        render_dashboard_home(ui)
    elif nav_view == "Estadísticas":
        render_strava_dashboard(ui, callback_status)
    else:
        render_request_page(ui)


def _render_accessible_control_focus_styles(ui) -> None:
    """Keep one high-contrast keyboard focus cue on shared Streamlit controls."""
    ui.html(
        """<style>
        .stApp { --coach-focus-ring: CanvasText; }
        .st-key-dashboard-home {
            --coach-focus-ring: var(--primary-color, CanvasText);
        }
        .stApp [data-testid="stSelectbox"] [role="group"]:focus-within {
            border-color: var(--border-color, #9aa7a9) !important;
            box-shadow: none !important;
        }
        .stApp [data-testid="stSelectbox"] [role="combobox"][data-focus-visible="true"]:focus-visible {
            outline: 2px solid var(--coach-focus-ring) !important;
            outline-offset: 2px;
        }
        .stApp [data-testid="stDateInput"] [data-testid="stDateInputField"]:focus-within {
            border-color: var(--border-color, #9aa7a9) !important;
            box-shadow: none !important;
        }
        .stApp [data-testid="stDateInput"] [role="spinbutton"]:focus-visible {
            outline: 2px solid var(--coach-focus-ring) !important;
            outline-offset: 1px;
        }
        </style>""",
    )
