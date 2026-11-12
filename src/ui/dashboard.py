"""Application navigation and the isolated Stride demonstration home."""

from src.ui.stride_dashboard_component import render_stride_dashboard

DASHBOARD_VIEW_KEY = "dashboard_view"
NAVIGATION_KEY = "dashboard_navigation"
NAVIGATION_OPEN_KEY = "dashboard_navigation_open"
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


def render_dashboard_styles(ui, *, show_sidebar: bool = False) -> None:
    """Show native navigation on demand and otherwise fill the page with demo UI."""
    render_sidebar_visibility_styles(ui, show_sidebar=show_sidebar)
    ui.html(
        f"""<style>
        [data-testid="stMainBlockContainer"] {{
            max-width:none !important;
            padding:0 !important;
        }}
        </style>"""
    )


def render_sidebar_visibility_styles(ui, *, show_sidebar: bool) -> None:
    """Control the native sidebar, including its mobile overlay state."""
    if show_sidebar:
        css = """
            @media (max-width: 768px) {
                [data-testid="stSidebar"] {
                    display:block !important;
                    position:fixed !important;
                    inset:0 auto 0 0 !important;
                    width:min(320px, 84vw) !important;
                    min-width:min(320px, 84vw) !important;
                    transform:translateX(0) !important;
                    visibility:visible !important;
                    z-index:10000 !important;
                }
            }
        """
    else:
        css = """
            [data-testid="stSidebar"],
            [data-testid="stSidebarCollapsedControl"] { display:none !important; }
        """
    ui.html(f"<style>{css}</style>")


def render_dashboard_home(ui, *, on_open_navigation_change) -> None:
    """Mount the prototype-based demo, isolated from Strava and Coach data."""
    render_stride_dashboard(on_open_navigation_change=on_open_navigation_change)
