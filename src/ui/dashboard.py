"""Application navigation and the isolated Stride demonstration home."""

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
        ui.markdown("### ↗ Strava AI Coach")
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
    """Let the source rail occupy the page without Streamlit's unused sidebar."""
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


def render_dashboard_home(ui, *, on_route_change=None) -> None:
    """Mount the prototype-based demo, isolated from Strava and Coach data."""
    render_stride_dashboard(on_route_change=on_route_change)
