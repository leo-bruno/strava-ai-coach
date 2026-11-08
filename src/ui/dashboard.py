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
NAVIGATION_ICONS = {"Inicio": "▦", "Mi plan": "▤", "Estadísticas": "◉", "Coach": "✦"}
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
        if view == "Inicio":
            ui.markdown(
                '<div class="dashboard-brand"><span aria-hidden="true">↗</span>'
                '<strong>Strava AI Coach</strong></div>',
                unsafe_allow_html=True,
            )
        else:
            ui.markdown("### ↗ Strava AI Coach")
        ui.caption("Datos ficticios · solo demostración")
        selected_view = view if view in NAVIGATION_VIEWS else "Mi plan"
        return ui.radio(
            "Navegación principal",
            options=NAVIGATION_VIEWS,
            format_func=lambda option: (
                f"{NAVIGATION_ICONS[option]}  {option}" if view == "Inicio" else option
            ),
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
        .stApp:has(.st-key-dashboard-home) { background:#e1e4e5; color:#171d1e; }
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] {
            width:clamp(154px,16vw,250px) !important; min-width:clamp(154px,16vw,250px) !important;
            background:#f7f9f9; border-radius:24px; margin:20px 0 20px 20px;
            min-height:calc(100vh - 40px); box-shadow:0 1px 2px #17262820;
        }
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] > div:first-child { background:transparent; }
        .stApp:has(.st-key-dashboard-home) [data-testid="stMainBlockContainer"] {
            max-width:1800px; padding:44px 20px 48px;
        }
        .st-key-dashboard-home {
            box-sizing:border-box; width:100%; max-width:1800px; margin:0 auto;
            padding:0; color:#171d1e;
            font-family:"Manrope", "Helvetica Neue", system-ui, sans-serif;
            font-size:16px;
        }
        .st-key-dashboard-home *, .st-key-dashboard-home *::before, .st-key-dashboard-home *::after,
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] * {
            font-family:"Manrope", "Helvetica Neue", system-ui, sans-serif !important;
        }
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { margin:0; }
        .stApp:has(.st-key-dashboard-home) .dashboard-brand { display:flex; align-items:center; gap:9px; font-size:1rem; font-weight:800; letter-spacing:-.045em; }
        .stApp:has(.st-key-dashboard-home) .dashboard-brand span { display:grid; place-items:center; width:36px; height:36px; color:white; font-size:24px; border-radius:9px; background:linear-gradient(#fc382a,#ef0063); }
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] [data-testid="stRadio"] > div { gap:8px; }
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] label[data-testid="stRadioOption"] {
            position:relative; display:flex; align-items:center; gap:8px;
            min-height:40px; padding:8px 10px; border-radius:9px; color:#344042; font-weight:600;
        }
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child { display:none; }
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"] { background:#171d1e; color:white; }
        .st-key-dashboard-home .st-key-dashboard-progress,
        .st-key-dashboard-home .st-key-dashboard-pace,
        .st-key-dashboard-home .st-key-dashboard-training,
        .st-key-dashboard-home .st-key-dashboard-agenda,
        .st-key-dashboard-home .st-key-dashboard-performance,
        .st-key-dashboard-home .st-key-coach-preview {
            box-sizing: border-box; min-width: 0; height: 100%;
            background:#f7f9f9; color:#171d1e;
            border:1px solid #fff; border-radius:20px; padding:16px 20px;
            box-shadow:0 1px 2px #17262818;
            font-family: inherit;
        }
        .st-key-dashboard-home .st-key-dashboard-summary {
            display: flex; flex-direction: column; gap: .8rem; min-width: 0;
        }
        .st-key-dashboard-home .st-key-dashboard-top > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns:minmax(0, 30fr) minmax(0, 24fr) minmax(0, 46fr);
            gap:14px;
        }
        .st-key-dashboard-home .st-key-dashboard-top > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            box-sizing: border-box; width: auto !important; min-width: 0; flex: none !important;
        }
        .st-key-dashboard-home .st-key-dashboard-bottom > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {
            display:grid !important; grid-template-columns:minmax(0, 1.25fr) minmax(0, 1fr); gap:14px;
        }
        .st-key-dashboard-home .st-key-dashboard-bottom > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            width: auto !important; min-width: 0; flex: none !important;
        }
        .st-key-dashboard-home .dashboard-kicker { color:#52666a; font-size:.72rem; font-weight:700; letter-spacing:.06em; }
        .st-key-dashboard-home .dashboard-number { color:#192629; font-size:clamp(23px,2.5vw,38px); font-weight:700; letter-spacing:-.05em; font-variant-numeric:tabular-nums; }
        .st-key-dashboard-home .st-key-dashboard-progress .dashboard-number { font-size:clamp(22px,2.2vw,32px); white-space:nowrap; }
        .st-key-dashboard-home .dashboard-small { color: var(--text-color, inherit); font-size: .82rem; letter-spacing: normal; }
        .st-key-dashboard-home .dashboard-unit { display:inline-block; margin-left:.35em; letter-spacing:normal; font-size:.82rem; font-weight:600; }
        .st-key-dashboard-home .dashboard-mock-badge { display:inline-block; padding:7px 12px; border-radius:999px; background:#fafcfc; border:1px solid #cbd2d3; color:#344042; font-size:.78rem; font-weight:700; white-space:nowrap; }
        .st-key-dashboard-home .dashboard-session-title { color:var(--text-color, inherit); font-weight:700; }
        .st-key-dashboard-home .dashboard-session-detail { color:var(--text-color, inherit); font-size:.88rem; }
        .st-key-dashboard-home .dashboard-done { display:inline-grid; place-items:center; width:2rem; height:2rem; border-radius:.55rem; background:#d9f4eb; color:#09664f; font-weight:800; }
        .st-key-dashboard-home .dashboard-date { display:inline-grid; place-items:center; width:2.5rem; min-height:2rem; border-radius:.55rem; background:#e7f5f6; color:#08646a; font-weight:800; }
        .st-key-dashboard-home h1 { margin:4px 0; font-size:clamp(24px,2.6vw,38px); line-height:1.2; font-weight:600; letter-spacing:-.045em; }
        .st-key-dashboard-home h2 { margin:0 0 12px; font-size:clamp(16px,1.4vw,23px); line-height:1.25; font-weight:600; letter-spacing:-.035em; }
        .st-key-dashboard-home .st-key-dashboard-progress h2,
        .st-key-dashboard-home .st-key-dashboard-pace h2 { font-size:1.12rem; margin:0 0 9px; }
        .st-key-dashboard-home .st-key-dashboard-training h2,
        .st-key-dashboard-home .st-key-dashboard-training h3,
        .st-key-dashboard-home .st-key-dashboard-performance h3 { font-size:1.12rem; margin:0 0 12px; font-weight:600; letter-spacing:-.035em; }
        .st-key-dashboard-home .st-key-dashboard-training h3 { font-size:1rem; white-space:nowrap; }
        .st-key-dashboard-home .st-key-coach-preview h3 { font-size:1.2rem; margin:0 0 10px; }
        .st-key-dashboard-home .st-key-dashboard-progress,
        .st-key-dashboard-home .st-key-dashboard-pace { position:relative; overflow:hidden; min-height:138px; }
        .st-key-dashboard-home .st-key-dashboard-summary { display:grid; grid-template-columns:1fr; gap:14px; }
        .st-key-dashboard-home .st-key-dashboard-home-header > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] { align-items:center; }
        .st-key-dashboard-home .dashboard-header-label { font-size:1.15rem; font-weight:600; letter-spacing:-.035em; }
        .st-key-dashboard-home .st-key-dashboard-intro { margin:8px 0 20px; }
        .st-key-dashboard-home .st-key-dashboard-intro p { margin:6px 0 0; color:#4c6166; font-size:.9rem; font-weight:500; }
        .st-key-dashboard-home .dashboard-progress-row,
        .st-key-dashboard-home .dashboard-pace-row { position:relative; min-height:62px; display:flex; align-items:center; }
        .st-key-dashboard-home .dashboard-progress-copy { max-width:70%; position:relative; z-index:1; }
        .st-key-dashboard-home .dashboard-progress-copy p { margin:5px 0 0; color:#52666a; font-size:.78rem; }
        .st-key-dashboard-home .dashboard-arc { position:absolute; right:5px; bottom:3px; width:35%; max-width:130px; height:auto; }
        .st-key-dashboard-home .dashboard-pace-bars { position:absolute; right:0; bottom:4px; width:43%; height:54px; display:flex; align-items:end; gap:5px; }
        .st-key-dashboard-home .dashboard-pace-bars span { width:12%; height:var(--h); min-width:4px; border-radius:3px; background:repeating-linear-gradient(to top,#f5a7bb 0 6px,transparent 6px 8px); }
        .st-key-dashboard-home .dashboard-pace-bars span:nth-child(4) { background:repeating-linear-gradient(to top,#f32c59 0 6px,transparent 6px 8px); }
        .st-key-dashboard-home .st-key-dashboard-training [class*="st-key-training-"] { padding:12px 0; border-bottom:1px solid #e5ecee; }
        .st-key-dashboard-home .st-key-dashboard-training [class*="st-key-training-"]:last-child { border-bottom:0; padding-bottom:0; }
        .st-key-dashboard-home .st-key-dashboard-agenda .dashboard-timeline-labels { display:flex; justify-content:space-between; gap:8px; margin:18px 0 8px; color:#52666a; font-size:.7rem; }
        .st-key-dashboard-home .st-key-dashboard-agenda .st-key-agenda-items > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {
            display:grid !important; grid-template-columns:repeat(5,minmax(0,1fr)); gap:0; min-height:190px;
            padding:8px; border-radius:10px; background:repeating-linear-gradient(90deg,#edf8f9 0 19.8%,#fff 19.8% 20%);
        }
        .st-key-dashboard-home .st-key-dashboard-agenda .st-key-agenda-items [data-testid="stColumn"] { width:auto !important; min-width:0; flex:none !important; }
        .st-key-dashboard-home .st-key-dashboard-agenda .st-key-agenda-items [data-testid="stColumn"] > div {
            min-height:74px; padding:0; background:transparent; border-radius:0; box-shadow:none;
        }
        .st-key-dashboard-home .st-key-dashboard-agenda .agenda-card { min-height:74px; padding:7px 9px; display:grid; align-content:start; gap:3px; background:#fff; border-radius:10px; box-shadow:0 2px 6px #24485014; }
        .st-key-dashboard-home .st-key-dashboard-agenda .agenda-card .agenda-status { font-size:.75rem; color:#52666a; }
        .st-key-dashboard-home .st-key-dashboard-agenda .agenda-card .agenda-status-done { color:#09664f; }
        .st-key-dashboard-home .st-key-dashboard-agenda .agenda-card .agenda-status-done::before { content:"✓ "; font-weight:800; }
        .st-key-dashboard-home .st-key-dashboard-agenda .agenda-card .agenda-status-next { color:#08646a; }
        .st-key-dashboard-home .st-key-dashboard-agenda .agenda-card .agenda-status-next::before { content:"◷ "; font-weight:800; }
        .st-key-dashboard-home .st-key-dashboard-agenda .st-key-agenda-items [data-testid="stColumn"]:nth-child(1) { grid-column:span 3; }
        .st-key-dashboard-home .st-key-dashboard-agenda .st-key-agenda-items [data-testid="stColumn"]:nth-child(2) { grid-column:3 / 6; }
        .st-key-dashboard-home .st-key-dashboard-agenda .st-key-agenda-items [data-testid="stColumn"]:nth-child(3) { grid-column:2 / 5; }
        .st-key-dashboard-home .st-key-dashboard-agenda .dashboard-kicker { font-size:.7rem; }
        .st-key-dashboard-home .st-key-dashboard-agenda .dashboard-session-title { font-size:.88rem; }
        .st-key-dashboard-home .st-key-dashboard-agenda [data-testid="stCaptionContainer"] p { font-size:.75rem; }
        .st-key-dashboard-home .st-key-dashboard-agenda .st-key-agenda-heading > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] { align-items:center; }
        .st-key-dashboard-home .st-key-dashboard-agenda .st-key-agenda-heading h2 { margin:0; }
        .st-key-dashboard-home .st-key-dashboard-agenda .st-key-agenda-heading [data-testid="stSelectbox"] { min-width:150px; }
        .st-key-dashboard-home .st-key-dashboard-agenda [data-testid="stSelectbox"] [role="combobox"] { border-radius:999px; font-size:.75rem; font-weight:600; }
        .st-key-dashboard-home .st-key-dashboard-agenda [data-testid="stCaptionContainer"] p { color:#52666a; }
        .st-key-dashboard-home .st-key-dashboard-performance { min-height:250px; }
        .st-key-dashboard-home [data-testid="stExpander"] { background:#f7f9f9; border:1px solid #fff; border-radius:16px; box-shadow:0 1px 2px #17262818; }
        .st-key-dashboard-home .st-key-dashboard-performance [data-testid="stAlertContainer"] { background:#eef7f7; border:1px solid #dce8ea; border-radius:10px; }
        .st-key-dashboard-home .st-key-dashboard-performance [data-testid="stAlertContainer"] p { color:#52666a; }
        .st-key-dashboard-home .st-key-coach-preview { background:radial-gradient(ellipse at 96% 95%,#a8272a,#351516 55%,#180f10); color:white; }
        .st-key-dashboard-home .st-key-coach-preview h2,
        .st-key-dashboard-home .st-key-coach-preview p { color:#fff; }
        .st-key-dashboard-home .st-key-coach-preview [data-testid="stAlertContainer"] { background:#ffffff18; border:1px solid #ffffff38; border-radius:10px; }
        .st-key-dashboard-home .st-key-coach-preview [data-testid="stAlertContainer"] p,
        .st-key-dashboard-home .st-key-coach-preview [data-testid^="stAlertContent"] { color:#fff !important; }
        .st-key-dashboard-home .st-key-coach-preview button { background:#ffffff24; color:#fff; border:1px solid #ffffff55; }
        .st-key-dashboard-home [data-testid="stIconMaterial"],
        .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] [data-testid="stIconMaterial"] { font-family:"Material Symbols Rounded" !important; }
        .st-key-dashboard-home .st-key-coach-preview [data-testid="stMarkdownContainer"] p { color:var(--text-color, inherit); }
        .st-key-dashboard-home button:focus-visible,
        .st-key-dashboard-home a:focus-visible,
        .st-key-dashboard-home input:focus-visible,
        .st-key-dashboard-home [role="combobox"]:focus-visible {
            outline: 2px solid var(--primary-color, currentColor) !important; outline-offset: 2px;
        }
        .st-key-dashboard-home .st-key-coach-preview button { margin-top:.25rem; }
        .st-key-dashboard-home a, .st-key-dashboard-home a:hover { text-decoration:none; }
        .st-key-dashboard-home h1 { overflow-wrap: normal; word-break: normal; hyphens: none; }
        @media(max-width: 1000px) {
            .st-key-dashboard-home .st-key-dashboard-top > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {
                grid-template-columns:minmax(0,1fr) minmax(0,1fr);
            }
            .st-key-dashboard-home .st-key-dashboard-top > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) {
                grid-column: 1 / -1;
            }
        }
        @media(max-width: 680px) {
            .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] { margin:6px; min-height:auto; }
            .stApp:has(.st-key-dashboard-home) [data-testid="stSidebar"] [data-testid="stRadio"] > div { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); }
            .stApp:has(.st-key-dashboard-home) [data-testid="stMainBlockContainer"] { padding:60px 12px 32px; }
            .st-key-dashboard-home { padding:0; }
            .st-key-dashboard-home h1 { font-size:clamp(24px,7.5vw,32px); line-height:1.12; }
            .st-key-dashboard-home .st-key-dashboard-bottom > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] { grid-template-columns:minmax(0,1fr); }
            .st-key-dashboard-home .st-key-dashboard-top > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"],
            .st-key-dashboard-home .st-key-dashboard-bottom > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {
                grid-template-columns: minmax(0, 1fr);
            }
            .st-key-dashboard-home .st-key-dashboard-top > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) {
                grid-column: auto;
            }
            .st-key-dashboard-home .st-key-dashboard-progress,
            .st-key-dashboard-home .st-key-dashboard-pace,
            .st-key-dashboard-home .st-key-dashboard-training,
            .st-key-dashboard-home .st-key-dashboard-agenda,
            .st-key-dashboard-home .st-key-dashboard-performance,
            .st-key-dashboard-home .st-key-coach-preview { padding:.9rem; }
        }
        @media(max-width:390px) {
            .st-key-dashboard-home .st-key-dashboard-agenda .st-key-agenda-items > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {
                grid-template-columns:minmax(0,1fr); gap:6px; padding:0; background:none;
            }
            .st-key-dashboard-home .st-key-dashboard-agenda .st-key-agenda-items [data-testid="stColumn"]:nth-child(n) { grid-column:auto; }
        .st-key-dashboard-home .st-key-dashboard-agenda .agenda-card { min-height:0; }
            .st-key-dashboard-home .st-key-dashboard-agenda .st-key-agenda-heading > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] { gap:6px; }
            .st-key-dashboard-home .st-key-dashboard-agenda .st-key-agenda-heading [data-testid="stSelectbox"] { min-width:0; }
        }
        </style>""",
        unsafe_allow_html=True,
    )


def _progress_arc(percent: int) -> str:
    return (
        '<svg class="dashboard-arc" viewBox="0 0 110 94" role="img" aria-label="'
        f'{percent} % de la distancia prevista">'
        '<path d="M20.36 75 A40 40 0 1 1 89.64 75" fill="none" stroke="#c4ced0" stroke-width="12" stroke-linecap="round"/>'
        '<path d="M20.36 75 A40 40 0 1 1 89.64 75" pathLength="100" fill="none" stroke="#12afbc" stroke-width="12" stroke-linecap="round" '
        f'stroke-dasharray="{percent} 100"/><text x="55" y="63" text-anchor="middle" font-size="24" font-weight="700" fill="#192527">{percent}<tspan font-size="12">%</tspan></text></svg>'
    )


def _render_progress_and_pace(ui) -> None:
    with ui.container(key="dashboard-summary"):
        with ui.container(border=True, key="dashboard-progress"):
            ui.markdown('<div class="dashboard-kicker">DATOS FICTICIOS · SEMANA ACTUAL</div>', unsafe_allow_html=True)
            ui.markdown(
                '<h2>Progreso semanal</h2><div class="dashboard-progress-row">'
                '<div class="dashboard-progress-copy"><div class="dashboard-number">11,4 km '
                '<span class="dashboard-unit">/ 18 km</span></div>'
                '<p>2 de 3 entrenamientos</p></div>' + _progress_arc(63) + '</div>',
                unsafe_allow_html=True,
            )
        with ui.container(border=True, key="dashboard-pace"):
            ui.markdown('<div class="dashboard-kicker">DATOS FICTICIOS</div>', unsafe_allow_html=True)
            bars = (48, 73, 51, 92, 54, 74, 32)
            ui.markdown(
                '<h2>Ritmo medio</h2><div class="dashboard-pace-row"><div class="dashboard-number">'
                '5:42 <span class="dashboard-small">/km</span></div>'
                '<div class="dashboard-pace-bars" role="img" aria-label="Ritmos ficticios de ejemplo">'
                + "".join(f'<span style="--h:{height}%"></span>' for height in bars)
                + '</div></div>',
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
        with ui.container(key="agenda-heading"):
            heading, week_select = ui.columns([1.4, 1], gap="small")
            with heading:
                ui.markdown('<h2>Agenda semanal</h2>', unsafe_allow_html=True)
            with week_select:
                ui.selectbox(
                    "Semana de la agenda",
                    options=WEEK_OPTIONS,
                    format_func=_agenda_week_label,
                    key=AGENDA_WEEK_KEY,
                    label_visibility="collapsed",
                )
        ui.caption("Agenda · datos ficticios")
        ui.markdown(
            '<div class="dashboard-timeline-labels"><span>Día</span><span>Sesión 01</span>'
            '<span>Sesión 02</span><span>Sesión 03</span></div>',
            unsafe_allow_html=True,
        )
        _, end = _week_interval(ui.session_state.get(AGENDA_WEEK_KEY, "current"))
        selected_week = ui.session_state.get(AGENDA_WEEK_KEY, "current")
        sessions = _sample_sessions(selected_week)
        with ui.container(key="agenda-items"):
            columns = ui.columns([1] * len(sessions))
            for column, session in zip(columns, sessions):
                with column:
                    target = session["actual"] or session["planned"]
                    status = "Realizado" if session["done"] else ("Próxima" if session["date"] >= date.today() else "Sin actividad vinculada")
                    status_class = "done" if session["done"] else ("next" if session["date"] >= date.today() else "unlinked")
                    ui.markdown(
                        f'<div class="agenda-card"><div class="dashboard-kicker">{_date_label(session["date"]).upper()}</div>'
                        f'<div class="dashboard-session-title">{session["name"]}</div>'
                        f'<div class="agenda-status agenda-status-{status_class}">{target} · {status}</div></div>',
                        unsafe_allow_html=True,
                    )
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


def _render_dashboard_home_content(ui) -> None:
    ui.session_state.setdefault(PLAN_WEEK_KEY, "current")
    ui.session_state.setdefault(AGENDA_WEEK_KEY, "current")
    with ui.container(key="dashboard-home-header"):
        title, badge = ui.columns([1, 0.7], gap="small")
        with title:
            ui.markdown('<div class="dashboard-header-label">Mi dashboard</div>', unsafe_allow_html=True)
        with badge:
            ui.markdown('<span class="dashboard-mock-badge">Vista de ejemplo · datos ficticios</span>', unsafe_allow_html=True)
    current_start, current_end = _week_interval("current")
    with ui.container(key="dashboard-intro",):
        ui.title("Tu entrenamiento esta semana")
        ui.markdown(f"<p>2 de 3 sesiones completadas · {current_start:%-d}–{current_end:%-d %b}</p>", unsafe_allow_html=True)

    with ui.container(key="dashboard-top"):
        progress, training, agenda = ui.columns([30, 24, 46], gap="small")
        with progress:
            _render_progress_and_pace(ui)
        with training:
            _render_training(ui)
        with agenda:
            _render_agenda(ui)

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


def render_dashboard_home(ui) -> None:
    with ui.container(key="dashboard-home"):
        _render_dashboard_home_content(ui)


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
