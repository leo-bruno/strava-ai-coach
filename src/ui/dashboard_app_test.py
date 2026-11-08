"""Dashboard navigation and fictional planning behavior through AppTest."""

from streamlit.testing.v1 import AppTest

from src.ui.dashboard import (
    AGENDA_WEEK_KEY,
    DASHBOARD_VIEW_KEY,
    PLAN_OPEN_KEY,
    PLAN_WEEK_KEY,
    _date_label,
    _sample_sessions,
)


def _app(view="Inicio"):
    app = AppTest.from_file("../../src/main.py")
    app.session_state[DASHBOARD_VIEW_KEY] = view
    app.session_state["dashboard_navigation"] = view
    return app.run()


def _text(app):
    text = [
        str(item.value)
        for group in (app.title, app.subheader, app.markdown, app.caption, app.info)
        for item in group
    ]
    text.extend(button.label for button in app.button)
    return "\n".join(text)


def test_home_is_fictional_and_dashboard_plan_starts_collapsed():
    app = _app()
    assert not app.exception
    text = _text(app)
    assert "Tu entrenamiento esta semana" in text
    assert "datos ficticios" in text
    assert "Progreso semanal" in text
    assert 'class="dashboard-unit">/ 18 km' in text
    assert ".stApp {" not in text
    assert 'font-family:"Manrope", "Helvetica Neue", system-ui, sans-serif' in text
    assert ".stApp:has(.st-key-dashboard-home)" in text
    assert "grid-template-columns:minmax(0, 30fr) minmax(0, 24fr) minmax(0, 46fr)" in text
    assert "class=\"dashboard-mock-badge\"" in text
    assert app.session_state[AGENDA_WEEK_KEY] == "current"
    assert app.session_state[PLAN_WEEK_KEY] == "current"
    assert app.expander[0].proto.expanded is False
    assert "Rendimiento" in text or any("RENDIMIENTO" in str(x.value) for x in app.markdown)
    assert app.selectbox(key=AGENDA_WEEK_KEY).label == "Semana de la agenda"


def test_dashboard_styles_do_not_render_in_coach_section():
    app = _app("Coach")
    assert not app.exception
    assert "st-key-dashboard-home" not in _text(app)


def test_agenda_week_is_independent_from_current_week_progress():
    app = _app()
    app.selectbox(key=AGENDA_WEEK_KEY).set_value("next").run()
    assert not app.exception
    assert app.session_state[AGENDA_WEEK_KEY] == "next"
    assert "SEMANA ACTUAL" in _text(app)


def test_plan_route_opens_with_current_week():
    app = _app("Mi plan")
    assert not app.exception
    assert app.session_state[PLAN_WEEK_KEY] == "current"
    assert app.session_state[PLAN_OPEN_KEY] is True
    assert "Plan de ejemplo" in _text(app)


def test_plan_week_selector_updates_heading_and_session_dates_together():
    app = _app("Mi plan")
    app.selectbox(key=PLAN_WEEK_KEY).set_value("next").run()
    assert not app.exception
    text = _text(app)
    assert "Plan de ejemplo · semana siguiente" in text
    assert all(_date_label(session["date"]) in text for session in _sample_sessions("next"))
    assert all(_date_label(session["date"]) not in text for session in _sample_sessions("current"))
