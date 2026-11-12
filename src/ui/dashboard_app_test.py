"""AppTest boundary checks for the isolated demo and real app routes."""

from streamlit.testing.v1 import AppTest

from src.ui.dashboard import DASHBOARD_VIEW_KEY, NAVIGATION_KEY
from src.ui.strava_weekly_overview import (
    WEEKLY_ACTIVITIES_KEY,
    WEEKLY_ANALYSES_KEY,
)


def _app(view="Inicio"):
    app = AppTest.from_file("../../src/main.py")
    app.session_state[DASHBOARD_VIEW_KEY] = view
    app.session_state[NAVIGATION_KEY] = view
    app.session_state["athlete_timezone"] = "Europe/Madrid"
    return app.run()


def test_home_mounts_demo_without_streamlit_errors_or_real_sidebar():
    app = _app()

    assert not app.exception
    assert app.session_state[DASHBOARD_VIEW_KEY] == "Inicio"
    assert list(app.radio) == []
    assert "dashboard_navigation_open" not in app.session_state
    assert WEEKLY_ANALYSES_KEY not in app.session_state
    assert WEEKLY_ACTIVITIES_KEY not in app.session_state


def test_home_does_not_fetch_strava_automatically(monkeypatch):
    calls = []

    def fail_if_called(*_args, **_kwargs):
        calls.append("fetch")
        raise AssertionError("Dashboard demo must not fetch Strava data")

    monkeypatch.setattr(
        "src.ui.strava_dashboard.load_recent_weekly_overview", fail_if_called
    )
    app = _app()

    assert not app.exception
    assert calls == []
    assert WEEKLY_ANALYSES_KEY not in app.session_state


def test_native_navigation_opens_real_statistics_section_without_fetching(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "src.ui.strava_dashboard.load_recent_weekly_overview",
        lambda *_args, **_kwargs: calls.append("fetch"),
    )
    app = _app("Estadísticas")

    assert not app.exception
    assert app.session_state[DASHBOARD_VIEW_KEY] == "Estadísticas"
    assert app.session_state[NAVIGATION_KEY] == "Estadísticas"
    assert [radio.options for radio in app.radio] == [
        ["▦  Inicio", "◉  Estadísticas", "✦  Coach"]
    ]
    assert calls == []


def test_native_sidebar_opens_real_coach_section():
    app = _app("Estadísticas")
    app.radio(key=NAVIGATION_KEY).set_value("Coach").run()

    assert not app.exception
    assert app.session_state[DASHBOARD_VIEW_KEY] == "Coach"
    assert app.session_state[NAVIGATION_KEY] == "Coach"
    assert len(app.radio) == 1


def test_native_sidebar_keeps_home_available_from_real_coach_section():
    app = _app("Coach")

    assert not app.exception
    assert app.session_state[DASHBOARD_VIEW_KEY] == "Coach"
    assert app.session_state[NAVIGATION_KEY] == "Coach"
    app.radio(key=NAVIGATION_KEY).set_value("Inicio").run()
    assert not app.exception
    assert app.session_state[DASHBOARD_VIEW_KEY] == "Inicio"
