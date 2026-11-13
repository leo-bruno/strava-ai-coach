"""Application navigation and the isolated Stride demonstration home."""

from datetime import datetime

from src.ui.strava_weekly_overview import (
    WEEKLY_ACTIVITIES_KEY,
    WEEKLY_ANALYSES_KEY,
    WEEKLY_AS_OF_KEY,
    WEEKLY_PERIOD_END_KEY,
    WEEKLY_PERIOD_START_KEY,
)

from src.ui.stride_dashboard_component import render_stride_dashboard

DASHBOARD_VIEW_KEY = "dashboard_view"
NAVIGATION_KEY = "dashboard_navigation"
NAVIGATION_VIEWS = ("Inicio", "Estadísticas", "Coach")
NAVIGATION_ICONS = {"Inicio": "▦", "Estadísticas": "◉", "Coach": "✦"}


def set_dashboard_view(session_state, view: str) -> None:
    if view in NAVIGATION_VIEWS:
        session_state[DASHBOARD_VIEW_KEY] = view
        session_state[NAVIGATION_KEY] = view


def render_sidebar(ui, *, view: str) -> str:
    """Render the native navigation used by the real Strava and Coach sections."""
    with ui.sidebar:
        ui.markdown("### ↗ Runner Coach")
        ui.caption("Tus actividades de Strava")
        selected = view if view in NAVIGATION_VIEWS else "Inicio"
        return ui.radio(
            "Navegación principal",
            options=NAVIGATION_VIEWS,
            format_func=lambda option: f"{NAVIGATION_ICONS[option]}  {option}",
            index=NAVIGATION_VIEWS.index(selected),
            key=NAVIGATION_KEY,
            label_visibility="collapsed",
        )


def render_dashboard_styles(ui) -> None:
    """Hide native navigation and let the prototype demo occupy the page."""
    ui.html(
        """<style>
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"] { display:none !important; }
        [data-testid="stMainBlockContainer"] {
            max-width:none !important;
            padding:0 !important;
        }
        </style>"""
    )


def build_home_dashboard_data(session_state) -> dict:
    """Serialize only the manually loaded weekly overview for the web component."""
    analyses = session_state.get(WEEKLY_ANALYSES_KEY)
    activities = session_state.get(WEEKLY_ACTIVITIES_KEY)
    start = session_state.get(WEEKLY_PERIOD_START_KEY)
    end = session_state.get(WEEKLY_PERIOD_END_KEY)
    as_of = session_state.get(WEEKLY_AS_OF_KEY)
    if not (isinstance(analyses, (tuple, list)) and len(analyses) == 7
            and isinstance(activities, (tuple, list))
            and isinstance(start, datetime) and isinstance(end, datetime)
            and isinstance(as_of, datetime)):
        return {"mode": "empty"}

    return {
        "mode": "weekly",
        "periodStart": start.date().isoformat(),
        "periodEnd": end.date().isoformat(),
        "asOf": as_of.date().isoformat(),
        "weeks": [{
            "weekStart": week.week_start_date.isoformat(),
            "distanceMeters": week.running_distance_meters,
            "activityCount": week.running_activity_count,
            "movingTimeSeconds": week.running_moving_time_seconds,
        } for week in analyses],
        "activities": [{
            "name": activity.name,
            "startDate": activity.start_date.isoformat(),
            "distanceMeters": activity.distance_meters,
            "movingTimeSeconds": activity.moving_time_seconds,
        } for activity in activities],
    }


def render_dashboard_home(ui) -> None:
    """Mount the approved dashboard with the current session's weekly snapshot."""
    render_stride_dashboard(build_home_dashboard_data(ui.session_state))
