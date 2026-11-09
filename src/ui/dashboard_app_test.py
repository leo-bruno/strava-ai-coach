"""Dashboard navigation and fictional planning behavior through AppTest."""

from datetime import date

from streamlit.testing.v1 import AppTest

from src.ui.dashboard import (
    AGENDA_WEEK_KEY,
    DASHBOARD_VIEW_KEY,
    DASHBOARD_REFERENCE_DATE_KEY,
    PLAN_OPEN_KEY,
    PLAN_WEEK_KEY,
    _dashboard_summary,
    _format_derived_pace,
    _format_kilometers,
    _date_label,
    _sample_sessions,
)


def _app(view="Inicio", reference_date=date(2026, 11, 4)):
    app = AppTest.from_file("../../src/main.py")
    app.session_state[DASHBOARD_VIEW_KEY] = view
    app.session_state["dashboard_navigation"] = view
    app.session_state[DASHBOARD_REFERENCE_DATE_KEY] = reference_date
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
    assert "Cómo está tu entrenamiento esta semana" in text
    assert "datos ficticios" in text
    assert "Progreso semanal" in text
    sunday_app = _app(reference_date=date(2026, 11, 8))
    progress_markup = next(
        item.value for item in sunday_app.markdown if "<h2>Progreso semanal</h2>" in str(item.value)
    )
    assert "11,4 km" in progress_markup
    assert "11.4 km" not in progress_markup
    assert 'class="dashboard-unit">/ 18 km' in text
    assert ".stApp {" not in text
    assert 'font-family:"Manrope", "Helvetica Neue", system-ui, sans-serif' in text
    assert ".stApp:has(.st-key-dashboard-home)" in text
    assert "container:dashboard-top / inline-size" in text
    assert "minmax(200px,20fr) minmax(165px,16fr) minmax(270px,27fr) minmax(380px,37fr)" in text
    assert "container:dashboard-lower / inline-size" in text
    assert "class=\"dashboard-mock-badge\"" in text
    assert app.session_state[AGENDA_WEEK_KEY] == "current"
    assert app.session_state[PLAN_WEEK_KEY] == "current"
    assert app.expander[0].proto.expanded is False
    assert "Rendimiento" in text or any("RENDIMIENTO" in str(x.value) for x in app.markdown)
    assert app.selectbox(key=AGENDA_WEEK_KEY).label == "Semana de la agenda"


def test_dashboard_summary_uses_the_same_reference_date_for_sessions_distance_and_arc():
    monday = _dashboard_summary(date(2026, 11, 2))
    midweek = _dashboard_summary(date(2026, 11, 4))
    sunday = _dashboard_summary(date(2026, 11, 8))

    assert (monday["completed_sessions"], monday["completed_distance_km"], monday["progress_percent"]) == (0, 0, 0)
    assert (midweek["completed_sessions"], midweek["completed_distance_km"], midweek["progress_percent"]) == (1, 6.8, 38)
    assert (sunday["completed_sessions"], sunday["completed_distance_km"], sunday["progress_percent"]) == (2, 11.4, 63)
    assert all(summary["planned_sessions"] == 4 and summary["planned_distance_km"] == 18 for summary in (monday, midweek, sunday))
    assert _format_kilometers(sunday["completed_distance_km"]) == "11,4"


def test_pending_training_date_shows_abbreviated_weekday_and_zero_padded_day():
    from src.ui.dashboard import _date_label, _sample_sessions

    pending = next(session for session in _sample_sessions("current", date(2026, 11, 4)) if session["date"].weekday() == 6)
    assert _date_label(pending["date"], compact=True) == "Dom 08"
    assert "Dom 08" in _text(_app(reference_date=date(2026, 11, 4)))


def test_agenda_cards_keep_chronological_session_ordinals_and_dates():
    reference_date = date(2026, 11, 4)
    app = _app(reference_date=reference_date)
    markup = "\n".join(str(item.value) for item in app.markdown)
    sessions = _sample_sessions("current", reference_date)
    for ordinal, session in enumerate(sessions, start=1):
        kicker = f"SESIÓN {ordinal:02d} · {_date_label(session['date']).upper()}"
        assert kicker in markup
        assert session["name"] in markup
    assert [markup.index(f"SESIÓN {ordinal:02d} ·") for ordinal in range(1, 5)] == sorted(
        markup.index(f"SESIÓN {ordinal:02d} ·") for ordinal in range(1, 5)
    )


def test_technique_fixture_has_time_only_and_no_invented_distance_or_pace():
    reference_date = date(2026, 11, 4)
    previous = next(
        session for session in _sample_sessions("previous", reference_date)
        if session["name"] == "Técnica de carrera"
    )
    current = next(
        session for session in _sample_sessions("current", reference_date)
        if session["name"] == "Técnica de carrera"
    )
    following = next(
        session for session in _sample_sessions("next", reference_date)
        if session["name"] == "Técnica de carrera"
    )
    assert (previous["planned"], previous["actual"], previous["actual_distance_km"]) == (
        "20 min de técnica", "18 min", None
    )
    assert previous["actual_duration_min"] == 18
    assert current["actual"] is None and current["planned_distance_km"] is None
    assert following["actual"] is None and following["planned_distance_km"] is None
    assert _format_derived_pace(previous) is None
    completed_run = next(
        session for session in _sample_sessions("current", reference_date)
        if session["name"] == "Rodaje suave"
    )
    assert _format_derived_pace(completed_run) == "6:02 min/km"

    markup = "\n".join(str(item.value) for item in _app(reference_date=reference_date).markdown)
    assert "6:02 min/km · derivado" in markup
    assert "Técnica de carrera" in markup


def test_dashboard_styles_do_not_render_in_coach_section():
    app = _app("Coach")
    assert not app.exception
    text = _text(app)
    text += "\n" + "\n".join(str(item.value) for item in app.html)
    assert ".st-key-dashboard-home button:focus-visible" not in text
    assert '[data-testid="stSelectbox"] [role="group"]:focus-within' in text
    assert '[data-testid="stSelectbox"] [role="combobox"][data-focus-visible="true"]:focus-visible' in text
    assert '[data-testid="stDateInputField"]:focus-within' in text
    assert '[role="spinbutton"]:focus-visible' in text


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
    reference_date = date(2026, 11, 4)
    app = _app("Mi plan", reference_date=reference_date)
    app.selectbox(key=PLAN_WEEK_KEY).set_value("next").run()
    assert not app.exception
    text = _text(app)
    assert "Plan de ejemplo · semana siguiente" in text
    assert all(_date_label(session["date"]) in text for session in _sample_sessions("next", reference_date))
    assert all(_date_label(session["date"]) not in text for session in _sample_sessions("current", reference_date))
