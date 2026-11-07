"""Fictional dashboard, plan navigation and session detail UI."""

from datetime import date, timedelta


DASHBOARD_VIEW_KEY = "dashboard_view"
NAVIGATION_KEY = "dashboard_navigation"
AGENDA_WEEK_KEY = "dashboard_agenda_week"
PLAN_WEEK_KEY = "dashboard_plan_week"
PLAN_OPEN_KEY = "dashboard_plan_open"
DETAIL_SESSION_KEY = "dashboard_detail_session"
RETURN_VIEW_KEY = "dashboard_return_view"

NAVIGATION_VIEWS = ("Inicio", "Mi plan", "Estadísticas", "Coach")
WEEK_OPTIONS = ("previous", "current", "next")


def set_dashboard_view(session_state, view: str) -> None:
    if view == "Detalle":
        session_state[DASHBOARD_VIEW_KEY] = view
        session_state[NAVIGATION_KEY] = "Mi plan"
        return
    if view not in NAVIGATION_VIEWS:
        return
    session_state[DASHBOARD_VIEW_KEY] = view
    session_state[NAVIGATION_KEY] = view


def _open_session(session_state, week: str, session_id: str) -> None:
    session_state[DETAIL_SESSION_KEY] = (week, session_id)
    session_state[RETURN_VIEW_KEY] = "Mi plan"
    session_state[PLAN_OPEN_KEY] = True
    set_dashboard_view(session_state, "Detalle")


def _return_to_plan(session_state, week: str) -> None:
    session_state[PLAN_WEEK_KEY] = week
    session_state[PLAN_OPEN_KEY] = True
    set_dashboard_view(session_state, "Mi plan")


def render_sidebar(ui, *, view: str) -> str:
    """Render accessible navigation using Streamlit's keyboard-operable radio."""
    with ui.sidebar:
        ui.markdown("### ↗ Strava AI Coach")
        ui.caption("Datos ficticios · solo demostración")
        selected_view = view if view in NAVIGATION_VIEWS else "Mi plan"
        return ui.radio(
            "Navegación principal",
            options=NAVIGATION_VIEWS,
            index=NAVIGATION_VIEWS.index(selected_view),
            key=NAVIGATION_KEY,
            label_visibility="collapsed",
        )


def _week_start(reference: date | None = None) -> date:
    current = reference or date.today()
    return current - timedelta(days=current.weekday())


def _week_interval(week: str, reference: date | None = None) -> tuple[date, date]:
    monday = _week_start(reference)
    offset = {"previous": -7, "current": 0, "next": 7}.get(week, 0)
    start = monday + timedelta(days=offset)
    return start, start + timedelta(days=6)


def _week_label(week: str) -> str:
    start, end = _week_interval(week)
    labels = {"previous": "Semana anterior", "current": "Semana actual", "next": "Semana siguiente"}
    return f"{labels.get(week, labels['current'])} · {start:%-d %b}–{end:%-d %b}"


def _agenda_week_label(week: str) -> str:
    start, end = _week_interval(week)
    labels = {"previous": "Anterior", "current": "Actual", "next": "Siguiente"}
    return f"{labels.get(week, labels['current'])} · {start:%-d}–{end:%-d %b}"


def _sample_sessions(week: str) -> list[dict[str, object]]:
    start, _ = _week_interval(week)
    definitions = {
        "previous": (
            (1, "Rodaje suave", "6 km suaves", "6,4 km en 38 min"),
            (3, "Series", "5 × 800 m con 2 min de recuperación", None),
            (6, "Tirada larga", "10 km suaves", "10,2 km en 59 min"),
        ),
        "current": (
            (1, "Rodaje suave", "7 km suaves", "6,8 km en 41 min"),
            (3, "Carrera continua", "25 min a ritmo sostenido", "24 min · 4,6 km"),
            (6, "Tirada larga", "11 km suaves", None),
        ),
        "next": (
            (1, "Rodaje suave", "7 km suaves", None),
            (3, "Series", "6 × 800 m con 2 min de recuperación", None),
            (6, "Tirada larga", "12 km suaves", None),
        ),
    }
    rows = []
    today = date.today()
    for day_offset, name, planned, actual in definitions.get(week, definitions["current"]):
        session_date = start + timedelta(days=day_offset)
        done = actual is not None and session_date <= today
        rows.append({
            "id": f"{week}-{day_offset}",
            "date": session_date,
            "name": name,
            "planned": planned,
            "actual": actual if done else None,
            "done": done,
        })
    return rows


def _date_label(day: date, *, compact: bool = False) -> str:
    weekdays = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")
    if compact:
        return f"{weekdays[day.weekday()]} {day:%d}"
    months = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
    return f"{weekdays[day.weekday()]} {day.day} {months[day.month - 1]}"


def render_dashboard_styles(ui) -> None:
    ui.markdown(
        """<style>
        @import url("https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap");
        .stApp { background: #e1e4e5; color: #171d1e; }
        [data-testid="stSidebar"] { background: #f7f9f9; }
        section.main > div[data-testid="stMainBlockContainer"] {
            max-width: none !important; width: 100%; padding: 1.4rem 2rem 3rem;
        }
        .st-key-dashboard-progress, .st-key-dashboard-pace, .st-key-dashboard-training,
        .st-key-dashboard-agenda, .st-key-dashboard-performance, .st-key-plan-panel,
        .st-key-detail-panel {
            background: #f7f9f9; border: 1px solid #fff; border-radius: 20px;
            padding: 1rem 1.2rem; box-shadow: 0 1px 2px #17262818;
            font-family: "Manrope", "Helvetica Neue", system-ui, sans-serif;
        }
        .st-key-dashboard-progress h2, .st-key-dashboard-pace h2,
        .st-key-dashboard-training h2, .st-key-dashboard-agenda h2,
        .st-key-plan-panel h2, .st-key-detail-panel h2 { color: #192629; }
        .dashboard-kicker { color: #52666a; font-size: .72rem; font-weight: 700; letter-spacing: .06em; }
        .dashboard-number { color: #192629; font-size: clamp(1.5rem, 3vw, 2.35rem); font-weight: 800; letter-spacing: -.05em; }
        .dashboard-small { color: #52666a; font-size: .82rem; }
        .dashboard-unit { display:inline-block; margin-left:.3em; letter-spacing:normal; font-size:.82rem; font-weight:600; }
        .dashboard-mock-badge { display:inline-block; padding:.28rem .7rem; border-radius:999px; background:#fff; border:1px solid #cbd2d3; color:#344042; font-size:.75rem; font-weight:700; }
        .dashboard-session { border-top:1px solid #e1e7e9; padding:.7rem 0; }
        .dashboard-session-title { color:#263537; font-weight:700; }
        .dashboard-session-detail { color:#53666b; font-size:.82rem; }
        .dashboard-done { display:inline-grid; place-items:center; width:2rem; height:2rem; border-radius:.55rem; background:#d9f4eb; color:#09664f; font-weight:800; }
        .dashboard-date { display:inline-grid; place-items:center; width:2.5rem; min-height:2rem; border-radius:.55rem; background:#e7f5f6; color:#08646a; font-weight:800; }
        .st-key-coach-preview { background:radial-gradient(ellipse at 96% 95%,#8f3037,#351719 56%,#180f10); color:#fff; }
        .st-key-coach-preview [data-testid="stMarkdownContainer"] p { color:#f2e9e9!important; }
        .st-key-coach-preview button:focus-visible, button:focus-visible, a:focus-visible, select:focus-visible {
            outline:2px solid #00878f!important; outline-offset:2px;
        }
        a { text-decoration:none; }
        a:hover { text-decoration:none; }
        @media(max-width: 900px) {
            .st-key-dashboard-top [data-testid="stHorizontalBlock"],
            .st-key-dashboard-bottom [data-testid="stHorizontalBlock"] { flex-direction:column; }
        }
        @media(max-width: 680px) {
            section.main > div[data-testid="stMainBlockContainer"] { padding-left:.7rem; padding-right:.7rem; }
            .st-key-dashboard-progress, .st-key-dashboard-pace, .st-key-dashboard-training,
            .st-key-dashboard-agenda, .st-key-dashboard-performance, .st-key-plan-panel,
            .st-key-detail-panel { padding:.85rem; }
            .st-key-dashboard-top [data-testid="stHorizontalBlock"] > div,
            .st-key-dashboard-bottom [data-testid="stHorizontalBlock"] > div { width:100%!important; flex:1 1 100%!important; }
        }
        </style>""",
        unsafe_allow_html=True,
    )


def _progress_arc(percent: int) -> str:
    return (
        '<svg viewBox="0 0 120 100" role="img" aria-label="'
        f'{percent} % de la distancia prevista" style="width:118px;max-width:40%;float:right">'
        '<path d="M20 75 A40 40 0 1 1 100 75" fill="none" stroke="#c4ced0" stroke-width="11" stroke-linecap="round"/>'
        '<path d="M20 75 A40 40 0 1 1 100 75" pathLength="100" fill="none" stroke="#12afbc" stroke-width="11" stroke-linecap="round" '
        f'stroke-dasharray="{percent} 100"/><text x="60" y="64" text-anchor="middle" font-size="21" font-weight="700" fill="#192527">{percent}%</text></svg>'
    )


def _render_progress_and_pace(ui) -> None:
    with ui.container(border=True, key="dashboard-progress",):
        ui.markdown('<div class="dashboard-kicker">DATOS FICTICIOS · SEMANA ACTUAL</div>', unsafe_allow_html=True)
        ui.subheader("Progreso semanal")
        ui.markdown(_progress_arc(63), unsafe_allow_html=True)
        ui.markdown(
            '<div class="dashboard-number">11,4 km '
            '<span class="dashboard-unit">/ 18 km</span></div>',
            unsafe_allow_html=True,
        )
        ui.caption("2 de 3 entrenamientos completados")
    with ui.container(border=True, key="dashboard-pace"):
        ui.markdown('<div class="dashboard-kicker">DATOS FICTICIOS</div>', unsafe_allow_html=True)
        ui.subheader("Ritmo medio")
        ui.markdown('<div class="dashboard-number">5:42 <span class="dashboard-small">/km</span></div>', unsafe_allow_html=True)
        bars = (48, 73, 51, 92, 54, 74, 32)
        ui.markdown(
            '<div role="img" aria-label="Ritmos ficticios de ejemplo" style="height:44px;display:flex;align-items:end;gap:5px">'
            + "".join(f'<span style="height:{height}%;width:10%;background:#f28ba6;border-radius:3px"></span>' for height in bars)
            + '</div>',
            unsafe_allow_html=True,
        )


def _render_training(ui) -> None:
    with ui.container(border=True, key="dashboard-training"):
        ui.markdown('<div class="dashboard-kicker">DATOS FICTICIOS</div>', unsafe_allow_html=True)
        ui.subheader("Entrenamientos")
        for session in _sample_sessions("current"):
            with ui.container(key=f"training-{session['id']}"):
                first, second = ui.columns([1, 5])
                with first:
                    if session["done"]:
                        ui.markdown('<span class="dashboard-done" aria-label="Completado">✓</span>', unsafe_allow_html=True)
                    else:
                        ui.markdown(f'<span class="dashboard-date">{session["date"]:%d}</span>', unsafe_allow_html=True)
                with second:
                    ui.markdown(f'<span class="dashboard-session-title">{session["name"]}</span>', unsafe_allow_html=True)
                    if session["done"]:
                        detail = f"{session['planned']} previstos · {session['actual']} hechos"
                    else:
                        detail = f"{session['planned']} previstos · Próxima"
                    ui.markdown(f'<div class="dashboard-session-detail">{detail}</div>', unsafe_allow_html=True)


def _render_agenda(ui) -> None:
    ui.session_state.setdefault(AGENDA_WEEK_KEY, "current")
    with ui.container(border=True, key="dashboard-agenda"):
        heading, week_select = ui.columns([2, 1])
        with heading:
            ui.subheader("Agenda semanal")
        with week_select:
            ui.selectbox(
                "Semana de la agenda",
                options=WEEK_OPTIONS,
                format_func=_agenda_week_label,
                key=AGENDA_WEEK_KEY,
                label_visibility="collapsed",
            )
        ui.caption("Agenda · datos ficticios")
        _, end = _week_interval(ui.session_state.get(AGENDA_WEEK_KEY, "current"))
        selected_week = ui.session_state.get(AGENDA_WEEK_KEY, "current")
        sessions = _sample_sessions(selected_week)
        columns = ui.columns([1] * len(sessions))
        for column, session in zip(columns, sessions):
            with column:
                ui.markdown(f'<div class="dashboard-kicker">{_date_label(session["date"]).upper()}</div>', unsafe_allow_html=True)
                ui.markdown(f'<div class="dashboard-session-title">{session["name"]}</div>', unsafe_allow_html=True)
                target = session["actual"] or session["planned"]
                status = "Realizado" if session["done"] else ("Próxima" if session["date"] >= date.today() else "Sin actividad vinculada")
                ui.caption(f"{target} · {status}")
        ui.caption(f"Semana de agenda: {end:%d %b}. El progreso semanal permanece en la semana actual.")


def _render_plan_sessions(ui, week: str) -> None:
    for session in _sample_sessions(week):
        date_text = _date_label(session["date"])
        if session["actual"] is not None:
            actual = session["actual"]
        elif session["date"] < date.today():
            actual = "Sin actividad vinculada"
        else:
            actual = "Próxima sesión"
        detail_col, planned_col, actual_col = ui.columns([2, 2, 2])
        with detail_col:
            ui.button(
                f"{date_text} · {session['name']}",
                key=f"open-session-{session['id']}",
                type="tertiary",
                on_click=_open_session,
                args=(ui.session_state, week, session["id"]),
            )
        with planned_col:
            ui.markdown(f"**Previsto** · {session['planned']}")
        with actual_col:
            ui.markdown(f"**Realizado** · {actual}")


def render_dashboard_home(ui) -> None:
    ui.session_state.setdefault(PLAN_WEEK_KEY, "current")
    ui.session_state.setdefault(AGENDA_WEEK_KEY, "current")
    title, badge = ui.columns([3, 1])
    with title:
        ui.caption("Mi dashboard")
        ui.title("Tu entrenamiento esta semana")
    with badge:
        ui.markdown('<span class="dashboard-mock-badge">Vista de ejemplo · datos ficticios</span>', unsafe_allow_html=True)
    current_start, current_end = _week_interval("current")
    ui.caption(f"Semana actual · {current_start:%-d}–{current_end:%-d %b}")

    with ui.container(key="dashboard-top"):
        progress, training, agenda = ui.columns([1.0, .9, 1.45], gap="small")
        with progress:
            _render_progress_and_pace(ui)
        with training:
            _render_training(ui)
        with agenda:
            _render_agenda(ui)

    with ui.expander("Mi plan · ejemplo", expanded=False):
        ui.caption("Plan ficticio. No se guarda ni se vincula con actividades reales.")
        selected_week = ui.selectbox(
            "Semana del plan",
            options=WEEK_OPTIONS,
            format_func=_week_label,
            key=PLAN_WEEK_KEY,
        )
        _render_plan_sessions(ui, selected_week)
        ui.button(
            "Abrir Mi plan",
            key="open-plan-from-dashboard",
            on_click=set_dashboard_view,
            args=(ui.session_state, "Mi plan"),
        )

    with ui.container(key="dashboard-bottom"):
        performance, coach = ui.columns([1.25, 1], gap="small")
        with performance:
            with ui.container(border=True, key="dashboard-performance"):
                ui.markdown('<div class="dashboard-kicker">RENDIMIENTO</div>', unsafe_allow_html=True)
                ui.subheader("En preparación")
                ui.info("Las métricas de rendimiento todavía no están definidas; aquí no se muestran datos del atleta.")
        with coach:
            with ui.container(border=True, key="coach-preview"):
                ui.subheader("Coach")
                ui.caption("Interpreta tu contexto y las observaciones semanales cargadas.")
                ui.warning("Generación experimental · modelo no aceptado. No se generan respuestas automáticamente.")
                ui.button(
                    "Abrir Coach",
                    key="open-coach-from-dashboard",
                    type="primary",
                    on_click=set_dashboard_view,
                    args=(ui.session_state, "Coach"),
                )


def render_training_plan(ui) -> None:
    ui.session_state.setdefault(PLAN_WEEK_KEY, "current")
    selected_week = ui.session_state.get(PLAN_WEEK_KEY, "current")
    start, end = _week_interval(selected_week)
    week_names = {
        "previous": "semana anterior",
        "current": "semana actual",
        "next": "semana siguiente",
    }
    ui.title("Mi plan")
    ui.caption(
        f"Plan de ejemplo · {week_names.get(selected_week, week_names['current'])} "
        f"{start:%-d}–{end:%-d %b} · no persistido"
    )
    with ui.container(border=True, key="plan-panel"):
        ui.caption("Todos los nombres, sesiones y valores de esta vista son ficticios.")
        ui.selectbox(
            "Semana del plan",
            options=WEEK_OPTIONS,
            format_func=_week_label,
            key=PLAN_WEEK_KEY,
        )
        expanded = bool(ui.session_state.get(PLAN_OPEN_KEY, True))
        with ui.expander(_week_label(selected_week), expanded=expanded):
            _render_plan_sessions(ui, selected_week)


def render_session_detail(ui) -> None:
    selected = ui.session_state.get(DETAIL_SESSION_KEY)
    if not isinstance(selected, tuple) or len(selected) != 2:
        set_dashboard_view(ui.session_state, "Mi plan")
        ui.session_state[PLAN_OPEN_KEY] = True
        ui.rerun()
        return
    week, session_id = selected
    session = next((item for item in _sample_sessions(week) if item["id"] == session_id), None)
    if session is None:
        set_dashboard_view(ui.session_state, "Mi plan")
        ui.session_state[PLAN_OPEN_KEY] = True
        ui.rerun()
        return
    ui.button(
        "← Volver a Mi plan",
        key="back-to-plan",
        on_click=_return_to_plan,
        args=(ui.session_state, week),
    )
    with ui.container(border=True, key="detail-panel"):
        ui.caption("DETALLE DE EJEMPLO · DATOS FICTICIOS")
        ui.title(f"{_date_label(session['date'])} · {session['name']}")
        ui.markdown(f"**Previsto** · {session['planned']}")
        if session["actual"]:
            ui.markdown(f"**Realizado** · {session['actual']}")
        elif session["date"] < date.today():
            ui.info("Sin actividad vinculada")
        else:
            ui.caption("Sesión pendiente")
        ui.info("Este detalle usa solo el plan ficticio. No consulta ni enlaza actividades de Strava.")
