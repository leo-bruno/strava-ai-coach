"""Strava-backed dashboard states and explicit loading behavior through AppTest."""

from datetime import date, datetime, timedelta, timezone

from streamlit.testing.v1 import AppTest

from src.models.activity import Activity
from src.models.weekly_analysis import WeeklyAnalysis
from src.ui.dashboard import DASHBOARD_VIEW_KEY
from src.ui.strava_weekly_overview import (
    WEEKLY_ACTIVITIES_KEY,
    WEEKLY_ANALYSES_KEY,
    WEEKLY_AS_OF_KEY,
    WEEKLY_PAGE_COUNT_KEY,
    WEEKLY_PERIOD_END_KEY,
    WEEKLY_PERIOD_START_KEY,
)


def _app(*, data_loaded=False, token=False):
    app = AppTest.from_file("../../src/main.py")
    app.session_state[DASHBOARD_VIEW_KEY] = "Inicio"
    app.session_state["dashboard_navigation"] = "Inicio"
    app.session_state["athlete_timezone"] = "Europe/Madrid"
    if token:
        app.session_state["strava_access_token"] = "dummy-token"
        app.session_state["strava_access_token_expires_at"] = int(
            (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        )
    if data_loaded:
        app.session_state["strava_access_token_expires_at"] = int(
            (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        )
        weeks = tuple(
            WeeklyAnalysis(
                week_start_date=date(2026, 10, 5) + timedelta(weeks=index),
                running_distance_meters=5000.0 + index * 1000,
                running_activity_count=1 + index % 2,
                running_moving_time_seconds=1500 + index * 100,
                running_structure_by_type=(),
            )
            for index in range(7)
        )
        app.session_state[WEEKLY_ANALYSES_KEY] = weeks
        app.session_state[WEEKLY_ACTIVITIES_KEY] = (
            Activity(
                id=10,
                name="Rodaje de prueba",
                sport_type="Run",
                start_date=datetime(2026, 11, 10, 7, tzinfo=timezone.utc),
                distance_meters=6200,
                moving_time_seconds=1860,
            ),
        )
        app.session_state[WEEKLY_PERIOD_START_KEY] = datetime(2026, 10, 5, tzinfo=timezone.utc)
        app.session_state[WEEKLY_PERIOD_END_KEY] = datetime(2026, 11, 23, tzinfo=timezone.utc)
        app.session_state[WEEKLY_AS_OF_KEY] = datetime(2026, 11, 12, tzinfo=timezone.utc)
        app.session_state[WEEKLY_PAGE_COUNT_KEY] = 2
    return app.run()


def _text(app):
    text = "\n".join(
        str(item.value)
        for group in (
            app.title,
            app.header,
            app.subheader,
            app.markdown,
            app.caption,
            app.info,
            app.warning,
            app.error,
        )
        for item in group
    )
    return text + "\n" + "\n".join(button.label for button in app.button)


def _assert_dashboard_composition(text):
    for heading in (
        "OBJETIVO SEMANAL",
        "DISTANCIA TOTAL",
        "RITMO MEDIO",
        "TIEMPO EN MOVIMIENTO",
        "Tu progreso",
        "Tu entrenamiento",
        "Últimas carreras",
        "Entrenar mejor empieza con una buena pregunta.",
    ):
        assert heading in text


def test_dashboard_explains_no_data_without_connecting_or_fetching():
    app = _app()
    assert not app.exception
    text = _text(app)
    assert "Vamos paso a paso" in text
    _assert_dashboard_composition(text)
    assert "Sin objetivo" in text and "No hay una meta configurada" in text
    assert text.count("—") >= 4
    assert "Conecta Strava para consultar tus carreras recientes" in text
    assert "Carga tus siete semanas de Strava para mostrar la evolución" in text
    assert "No hay un plan conectado" in text
    assert "Abrir Coach" in text
    assert all(button.key != "dashboard-refresh-strava" for button in app.button)
    assert "datos ficticios" not in text.lower()


def test_dashboard_renders_loaded_weekly_data_and_real_activity():
    app = _app(data_loaded=True)
    assert not app.exception
    text = _text(app)
    _assert_dashboard_composition(text)
    assert "56,0" in text
    assert "Distancia Run por semana" in text
    assert "10 carreras Run" in text
    assert "Rodaje de prueba" in text
    assert "6,2 km" in text
    assert "5:00 min/km · derivado" in text
    assert "no demuestra inactividad ni descanso" in text
    assert "No hay objetivos semanales configurados" in text
    assert "No hay un plan conectado" in text
    assert "18 km" not in text


def test_dashboard_has_explicit_refresh_and_real_sections_only():
    app = _app(token=True)
    assert not app.exception
    assert app.button(key="dashboard-refresh-strava").label == "Actualizar datos de Strava"
    text = _text(app)
    _assert_dashboard_composition(text)
    assert "Actualiza los datos para ver las carreras del intervalo" in text
    assert "No hay un plan conectado" in text
    assert "Abrir Coach" in text
    assert app.radio[0].options == ["▦  Inicio", "◉  Estadísticas", "✦  Coach"]


def test_refresh_fetch_happens_only_after_the_button_is_pressed(monkeypatch):
    calls = []

    def load(state, timezone_name):
        calls.append((timezone_name, state.get("strava_access_token")))

    monkeypatch.setattr("src.ui.dashboard.load_recent_weekly_overview", load)
    app = _app(token=True)
    assert calls == []
    app.button(key="dashboard-refresh-strava").click().run()
    assert not app.exception
    assert calls == [("Europe/Madrid", "dummy-token")]


def test_refresh_provider_failure_shows_safe_message(monkeypatch):
    def fail(*_args):
        raise RuntimeError("provider detail must not be displayed")

    monkeypatch.setattr("src.ui.dashboard.load_recent_weekly_overview", fail)
    app = _app(token=True)
    app.button(key="dashboard-refresh-strava").click().run()
    text = _text(app)
    assert not app.exception
    assert "No se pudieron cargar todas las páginas de Strava" in text
    assert "provider detail" not in text


def test_dashboard_handles_empty_weekly_results_without_fake_activities():
    app = _app(data_loaded=True)
    app.session_state[WEEKLY_ANALYSES_KEY] = tuple(
        WeeklyAnalysis(
            week_start_date=date(2026, 10, 5) + timedelta(weeks=index),
            running_distance_meters=0.0,
            running_activity_count=0,
            running_moving_time_seconds=0,
            running_structure_by_type=(),
        )
        for index in range(7)
    )
    app.session_state[WEEKLY_ACTIVITIES_KEY] = ()
    app = app.run()
    assert not app.exception
    text = _text(app)
    _assert_dashboard_composition(text)
    assert "No se devolvieron carreras de tipo Run" in text
    assert "No hay un plan conectado" in text


def test_dashboard_incomplete_weekly_context_keeps_every_module_visible():
    app = _app(data_loaded=True)
    app.session_state[WEEKLY_PERIOD_END_KEY] = None
    app = app.run()
    assert not app.exception
    text = _text(app)
    _assert_dashboard_composition(text)
    assert "Faltan fechas o datos de cobertura" in text
    assert "La cobertura temporal está incompleta" in text
    assert "El resumen está incompleto" in text
    assert "Rodaje de prueba" in text
