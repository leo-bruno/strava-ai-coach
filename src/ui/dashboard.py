"""Strava-backed home dashboard and application navigation."""

from datetime import date, datetime, timezone
from html import escape

import altair as alt

from src.analytics.pace import moving_pace
from src.models.activity import Activity
from src.ui.strava_connection import ACCESS_TOKEN_KEY, EXPIRES_AT_KEY
from src.ui.strava_weekly_overview import (
    WEEKLY_ACTIVITIES_KEY,
    WEEKLY_ANALYSES_KEY,
    WEEKLY_AS_OF_KEY,
    WEEKLY_PAGE_COUNT_KEY,
    WEEKLY_PERIOD_END_KEY,
    WEEKLY_PERIOD_START_KEY,
    load_recent_weekly_overview,
)
from src.ui.timezone_preference import ATHLETE_TIMEZONE_KEY

DASHBOARD_VIEW_KEY = "dashboard_view"
NAVIGATION_KEY = "dashboard_navigation"
NAVIGATION_VIEWS = ("Inicio", "Estadísticas", "Coach")
NAVIGATION_ICONS = {"Inicio": "▦", "Estadísticas": "◉", "Coach": "✦"}


def set_dashboard_view(session_state, view: str) -> None:
    if view in NAVIGATION_VIEWS:
        session_state[DASHBOARD_VIEW_KEY] = view
        session_state[NAVIGATION_KEY] = view


def render_sidebar(ui, *, view: str) -> str:
    """Render keyboard-operable navigation for real application sections."""
    with ui.sidebar:
        if view == "Inicio":
            ui.markdown(
                '<div class="dashboard-brand"><span aria-hidden="true">↗</span>'
                '<strong>Strava AI Coach</strong></div>',
                unsafe_allow_html=True,
            )
        else:
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
    """Apply the supplied prototype's visual language to native Streamlit UI."""
    ui.html(
        """<style>
        @import url("https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap");
        .stApp:has(.st-key-dashboard-home) { background:color-mix(in srgb,var(--background-color) 75%,#f5f6f8); color:var(--text-color); }
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] { background:var(--secondary-background-color); }
        .stApp:has(.st-key-dashboard-home) [data-testid="stMainBlockContainer"] { max-width:1600px; padding-top:2rem; }
        .st-key-dashboard-home { font-family:Manrope,"Helvetica Neue",system-ui,sans-serif; }
        .st-key-dashboard-home h1,.st-key-dashboard-home h2,.st-key-dashboard-home h3 { letter-spacing:-.035em; }
        .st-key-dashboard-home .dashboard-header h1::after { content:" ↗"; color:#3849e8; }
        .st-key-dashboard-home .dashboard-brand { display:flex; align-items:center; gap:9px; font-weight:800; letter-spacing:-.045em; }
        .st-key-dashboard-home .dashboard-brand span { display:grid; place-items:center; width:36px; height:36px; color:white; font-size:24px; border-radius:9px; background:#3849e8; }
        .st-key-dashboard-home .dashboard-intro { color:var(--text-color); opacity:.75; margin-top:-.4rem; }
        .st-key-dashboard-home [data-testid="stVerticalBlockBorderWrapper"] { border-radius:16px; background:var(--secondary-background-color); }
        .st-key-dashboard-home .st-key-dashboard-summary [data-testid="stVerticalBlockBorderWrapper"] { min-width:180px; }
        .st-key-dashboard-home .st-key-dashboard-goal { background:#3849e8 !important; border:1px solid #3849e8; border-radius:16px; padding:18px 22px; color:#fff; }
        .st-key-dashboard-home .st-key-dashboard-goal .dashboard-kicker,
        .st-key-dashboard-home .st-key-dashboard-goal .dashboard-muted { color:#fff; opacity:.82; }
        .st-key-dashboard-home .st-key-dashboard-goal .dashboard-big { margin-top:12px; }
        .st-key-dashboard-home .st-key-dashboard-goal [data-testid="stMarkdownContainer"] p { color:#fff; }
        .st-key-dashboard-home .dashboard-kicker { font-size:.72rem; font-weight:700; letter-spacing:.08em; color:var(--text-color); opacity:.75; }
        .st-key-dashboard-home .dashboard-big { font-size:clamp(1.65rem,3vw,2.35rem); font-weight:750; letter-spacing:-.055em; line-height:1.15; font-variant-numeric:tabular-nums; }
        .st-key-dashboard-home .dashboard-unit { font-size:.85rem; font-weight:600; letter-spacing:0; }
        .st-key-dashboard-home .dashboard-activity { display:grid; grid-template-columns:38px minmax(0,1fr) auto; align-items:center; gap:12px; padding:12px 0; border-bottom:1px solid var(--border-color); }
        .st-key-dashboard-home .dashboard-activity:last-child { border-bottom:0; }
        .st-key-dashboard-home .dashboard-route { display:grid; place-items:center; width:36px; height:36px; border-radius:10px; background:var(--secondary-background-color); color:var(--primary-color); font-weight:800; }
        .st-key-dashboard-home .dashboard-activity-name { font-weight:700; overflow-wrap:anywhere; }
        .st-key-dashboard-home .dashboard-muted { color:var(--text-color); opacity:.75; font-size:.82rem; }
        .st-key-dashboard-home .dashboard-activity-value { text-align:right; white-space:nowrap; font-weight:700; font-variant-numeric:tabular-nums; }
        .st-key-dashboard-home [data-testid="stBaseButton-primary"] { background:#3849e8 !important; border-color:#3849e8 !important; color:#fff !important; }
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child { display:none; }
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"],
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] label[data-testid="stRadioOption"][data-checked="true"],
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] label[data-testid="stRadioOption"][aria-checked="true"] { background:#3849e8 !important; color:#fff !important; border-radius:10px; }
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"] *,
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] label[data-testid="stRadioOption"][data-checked="true"] *,
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] label[data-testid="stRadioOption"][aria-checked="true"] * { color:#fff !important; }
        .st-key-dashboard-home button:focus-visible, .st-key-dashboard-home [role="combobox"]:focus-visible { outline:2px solid #3849e8; outline-offset:2px; }
        @media(max-width:700px) {
            .st-key-dashboard-home .dashboard-header h1::after { content:none; }
            .st-key-dashboard-home .dashboard-activity { grid-template-columns:34px minmax(0,1fr); }
            .st-key-dashboard-home .dashboard-activity-value { grid-column:2; text-align:left; }
            .st-key-dashboard-home .st-key-dashboard-summary [data-testid="stVerticalBlockBorderWrapper"] { min-width:calc(50% - 8px); }
            .st-key-dashboard-home .st-key-dashboard-header > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] { display:grid !important; grid-template-columns:minmax(0,1fr) !important; gap:8px; }
            .st-key-dashboard-home .st-key-dashboard-header > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { width:auto !important; min-width:0; }
        }
        </style>"""
    )


def _format_kilometers(meters: float) -> str:
    value = meters / 1000
    return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    return f"{hours} h {minutes} min" if hours else f"{minutes} min"


def _format_pace(seconds_per_km: float | None) -> str:
    if seconds_per_km is None:
        return "Sin datos de ritmo"
    seconds = round(seconds_per_km)
    return f"{seconds // 60}:{seconds % 60:02d} min/km · derivado"


def _week_label(start: date, end: date) -> str:
    months = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
    final_day = end.fromordinal(end.toordinal() - 1)
    return f"{start.day} {months[start.month - 1]}–{final_day.day} {months[final_day.month - 1]} {start.year}"


def _render_activities(ui, activities: tuple[Activity, ...]) -> None:
    runs = sorted(
        (activity for activity in activities if activity.sport_type == "Run"),
        key=lambda activity: activity.start_date,
        reverse=True,
    )
    if not runs:
        ui.info("No se devolvieron carreras de tipo Run en las siete semanas cargadas.")
        return
    for activity in runs[:5]:
        date_label = activity.start_date.strftime("%d/%m/%Y · %H:%M")
        pace = moving_pace(activity.distance_meters, activity.moving_time_seconds)
        markup = (
            '<div class="dashboard-activity">'
            '<span class="dashboard-route" aria-hidden="true">↗</span>'
            f'<div><div class="dashboard-activity-name">{escape(activity.name)}</div>'
            f'<div class="dashboard-muted">{escape(date_label)} · {_format_pace(pace)}</div></div>'
            f'<div class="dashboard-activity-value">{_format_kilometers(activity.distance_meters)} km'
            f'<div class="dashboard-muted">{_format_duration(activity.moving_time_seconds)}</div></div></div>'
        )
        ui.markdown(markup, unsafe_allow_html=True)


def _load_dashboard_overview(ui) -> None:
    from src.ui.coach_evidence_context import clear_coach_evidence_context
    from src.ui.coach_request_form import GENERATED_COACH_OUTPUT_KEY

    timezone_name = ui.session_state.get(ATHLETE_TIMEZONE_KEY)
    if not timezone_name:
        ui.error("Selecciona una zona horaria en Estadísticas antes de cargar los datos semanales.")
        return
    clear_coach_evidence_context(ui.session_state)
    ui.session_state.pop(GENERATED_COACH_OUTPUT_KEY, None)
    try:
        load_recent_weekly_overview(ui.session_state, timezone_name)
    except ValueError as error:
        ui.error(str(error))
    except RuntimeError:
        ui.error("No se pudieron cargar todas las páginas de Strava. No se conservó un resultado parcial.")


def render_dashboard_home(ui) -> None:
    with ui.container(key="dashboard-home"):
        access_token = ui.session_state.get(ACCESS_TOKEN_KEY)
        expires_at = ui.session_state.get(EXPIRES_AT_KEY)
        connected = isinstance(access_token, str) and bool(access_token.strip())
        expired = type(expires_at) is not int or expires_at <= datetime.now(timezone.utc).timestamp()
        valid_connection = connected and not expired
        loaded = ui.session_state.get(WEEKLY_ANALYSES_KEY)
        weeks = tuple(loaded) if isinstance(loaded, (tuple, list)) else ()
        weekly_data_loaded = bool(weeks)
        with ui.container(key="dashboard-header"):
            heading, action = ui.columns((3, 1), vertical_alignment="center", gap="medium")
            with heading:
                ui.markdown(
                    '<div class="dashboard-kicker">TU ESPACIO / INICIO</div>'
                    '<h1>Vamos paso a paso</h1>'
                    '<p class="dashboard-intro">Cada entrenamiento cuenta. Aquí tienes el resumen de tus carreras.</p>',
                    unsafe_allow_html=True,
                )
            with action:
                if valid_connection:
                    if ui.button(
                        "Actualizar datos de Strava",
                        key="dashboard-refresh-strava",
                        type="primary",
                        width="stretch",
                    ):
                        _load_dashboard_overview(ui)
                elif connected:
                    ui.button(
                        "Reconectar Strava",
                        key="dashboard-reconnect-strava",
                        type="primary",
                        width="stretch",
                        on_click=set_dashboard_view,
                        args=(ui.session_state, "Estadísticas"),
                    )
                    ui.caption("La sesión de Strava venció.")
                else:
                    ui.button(
                        "Conectar Strava",
                        key="dashboard-connect-strava",
                        type="primary",
                        width="stretch",
                        on_click=set_dashboard_view,
                        args=(ui.session_state, "Estadísticas"),
                    )

        activities = ui.session_state.get(WEEKLY_ACTIVITIES_KEY, ())
        start = ui.session_state.get(WEEKLY_PERIOD_START_KEY)
        end = ui.session_state.get(WEEKLY_PERIOD_END_KEY)
        as_of = ui.session_state.get(WEEKLY_AS_OF_KEY)
        pages = ui.session_state.get(WEEKLY_PAGE_COUNT_KEY, 0)
        context_complete = (
            isinstance(start, datetime)
            and isinstance(end, datetime)
            and isinstance(as_of, datetime)
            and type(pages) is int
        )
        total_distance = sum(week.running_distance_meters for week in weeks)
        total_time = sum(week.running_moving_time_seconds for week in weeks)
        total_runs = sum(week.running_activity_count for week in weeks)
        overall_pace = moving_pace(total_distance, total_time) if weekly_data_loaded else None

        with ui.container(horizontal=True, key="dashboard-summary"):
            with ui.container(border=True, key="dashboard-goal"):
                ui.markdown('<div class="dashboard-kicker">OBJETIVO SEMANAL</div>', unsafe_allow_html=True)
                ui.markdown('<div class="dashboard-big">Sin objetivo</div>', unsafe_allow_html=True)
                ui.markdown('<div class="dashboard-muted">No hay una meta configurada</div>', unsafe_allow_html=True)
            for label, value, unit, note in (
                (
                    "Distancia total",
                    _format_kilometers(total_distance) if weekly_data_loaded else "—",
                    "km",
                    "En las siete semanas cargadas" if weekly_data_loaded else "Carga datos de Strava",
                ),
                (
                    "Ritmo medio",
                    _format_pace(overall_pace).split()[0] if overall_pace is not None else "—",
                    "min/km",
                    "Derivado de tiempo y distancia" if overall_pace is not None else "Sin mediciones disponibles",
                ),
                (
                    "Tiempo en movimiento",
                    _format_duration(total_time) if weekly_data_loaded else "—",
                    "",
                    f"{total_runs} carreras Run" if weekly_data_loaded else "— carreras Run",
                ),
            ):
                with ui.container(border=True):
                    ui.markdown(f'<div class="dashboard-kicker">{label.upper()}</div>', unsafe_allow_html=True)
                    ui.markdown(
                        f'<div class="dashboard-big">{escape(value)} '
                        f'<span class="dashboard-unit">{unit}</span></div>',
                        unsafe_allow_html=True,
                    )
                    ui.markdown(f'<div class="dashboard-muted">{note}</div>', unsafe_allow_html=True)

        if weekly_data_loaded and context_complete:
            ui.caption(
                f"Siete semanas calendario completas · {_week_label(start.date(), end.date())} · "
                f"consultado {as_of:%d/%m/%Y %H:%M %Z} · {pages} páginas · solo actividades devueltas por Strava"
            )

        chart_column, plan_column = ui.columns((1.15, 1), gap="medium")
        with chart_column:
            with ui.container(border=True, key="dashboard-performance"):
                ui.subheader("Tu progreso")
                ui.caption("Distancia Run por semana · siete semanas calendario completas")
                if weekly_data_loaded:
                    week_labels = [
                        f"{week.week_start_date.day:02d}/{week.week_start_date.month:02d}"
                        for week in weeks
                    ]
                    chart = (
                        alt.Chart(
                            alt.Data(
                                values=[
                                    {
                                        "Semana": label,
                                        "Distancia (km)": week.running_distance_meters / 1000,
                                    }
                                    for label, week in zip(week_labels, weeks)
                                ]
                            )
                        )
                        .mark_line(point=True, color="#3849e8", strokeWidth=3)
                        .encode(
                            x=alt.X("Semana:N", sort=week_labels, title="Semana (lunes)"),
                            y=alt.Y("Distancia (km):Q", title="Kilómetros", scale=alt.Scale(zero=True)),
                            tooltip=["Semana:N", alt.Tooltip("Distancia (km):Q", format=".1f")],
                        )
                    )
                    ui.altair_chart(
                        chart,
                        alt="Distancia de carrera en cada una de las siete semanas completas cargadas",
                    )
                else:
                    ui.info("Carga tus siete semanas de Strava para mostrar la evolución. No hay puntos de ejemplo.")
                if weekly_data_loaded and not context_complete:
                    ui.warning("Faltan fechas o datos de cobertura; esta gráfica solo refleja el resumen disponible.")
        with plan_column:
            with ui.container(border=True, key="dashboard-weekly-plan"):
                ui.subheader("Tu entrenamiento")
                ui.markdown('<span class="dashboard-kicker">PLAN DE ENTRENAMIENTO</span>', unsafe_allow_html=True)
                ui.markdown('<div class="dashboard-big">No hay un plan conectado</div>', unsafe_allow_html=True)
                ui.caption("Las sesiones planificadas y los objetivos semanales aún no están disponibles.")
                if weekly_data_loaded and not context_complete:
                    ui.warning("El contexto del resumen está incompleto; no se puede asociar a un plan.")

        activity_column, coach_column = ui.columns((1, 1), gap="medium")
        with activity_column:
            with ui.container(border=True, key="dashboard-recent-activities"):
                ui.subheader("Últimas carreras")
                if weekly_data_loaded:
                    if context_complete:
                        _render_activities(ui, activities)
                    else:
                        ui.warning("La cobertura temporal está incompleta. Las filas visibles solo incluyen registros recibidos.")
                        _render_activities(ui, activities)
                elif valid_connection:
                    ui.info("Actualiza los datos para ver las carreras del intervalo.")
                else:
                    ui.info("Conecta Strava para consultar tus carreras recientes.")
        with coach_column:
            with ui.container(border=True, key="dashboard-coach"):
                ui.markdown('<div class="dashboard-kicker">✦ TU COACH</div>', unsafe_allow_html=True)
                ui.subheader("Entrenar mejor empieza con una buena pregunta.")
                ui.caption("Consulta tu solicitud y las evidencias disponibles en el espacio de Coach.")
                ui.button(
                    "Abrir Coach ↗",
                    key="dashboard-open-coach",
                    type="primary",
                    on_click=set_dashboard_view,
                    args=(ui.session_state, "Coach"),
                )
                ui.markdown('<div class="dashboard-muted">Las respuestas experimentales requieren una acción explícita en Coach.</div>', unsafe_allow_html=True)

        if weekly_data_loaded:
            if context_complete:
                ui.caption(
                    "La cobertura se limita al intervalo y a los registros devueltos por Strava; "
                    "un cero no demuestra inactividad ni descanso. No hay objetivos semanales configurados."
                )
            else:
                ui.warning("El resumen está incompleto; interpreta las métricas solo dentro de las limitaciones mostradas.")
