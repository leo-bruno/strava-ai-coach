"""Browser checks for Strava-backed dashboard layout, data and empty states."""
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

import pytest
from playwright.sync_api import sync_playwright


def _start_server(port: int, *, dark=False, state="empty"):
    project_root = Path(__file__).resolve().parents[2]
    launcher = Path(f"/tmp/strava_dashboard_e2e_{port}.py")
    setup = ""
    if state != "empty":
        setup = """
from datetime import date, datetime, timedelta, timezone
from src.models.activity import Activity
from src.models.weekly_analysis import WeeklyAnalysis
import streamlit as st
st.session_state['strava_access_token'] = 'dummy-token'
st.session_state['strava_access_token_expires_at'] = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
st.session_state['athlete_timezone'] = 'Europe/Madrid'
st.session_state['athlete_timezone_last_applied'] = 'Europe/Madrid'
"""
    if state in ("loaded", "zero-run", "incomplete"):
        all_zero = state == "zero-run"
        distance = "0" if all_zero else "5000 + i * 1000"
        count = "0" if all_zero else "i % 2 + 1"
        time_seconds = "0" if all_zero else "1800 + i * 60"
        activity = "" if all_zero else (
            "Activity(10, 'Rodaje de prueba', 'Run', "
            "datetime(2026, 11, 10, 7, tzinfo=timezone.utc), 6200, 1860),"
        )
        period_end = "None" if state == "incomplete" else "datetime(2026, 11, 23, tzinfo=timezone.utc)"
        setup += f"""
st.session_state['strava_weekly_analyses'] = tuple(
    WeeklyAnalysis(date(2026, 10, 5) + timedelta(weeks=i), {distance}, {count}, {time_seconds}, ())
    for i in range(7)
)
st.session_state['strava_weekly_activities'] = ({activity})
st.session_state['strava_weekly_period_start'] = datetime(2026, 10, 5, tzinfo=timezone.utc)
st.session_state['strava_weekly_period_end'] = {period_end}
st.session_state['strava_weekly_as_of'] = datetime(2026, 11, 12, tzinfo=timezone.utc)
st.session_state['strava_weekly_page_count'] = 2
"""
    launcher.write_text(
        f"import sys\nsys.path.insert(0, {str(project_root)!r})\n{setup}\n"
        "from src.ui.app import render_app\nrender_app()\n"
    )
    command = [
        ".venv/bin/python", "-m", "streamlit", "run", str(launcher),
        "--server.headless=true", f"--server.port={port}",
    ]
    if dark:
        command.append("--theme.base=dark")
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urlopen(f"http://127.0.0.1:{port}", timeout=1)
            return process, f"http://127.0.0.1:{port}"
        except Exception:
            if process.poll() is not None:
                pytest.fail(f"Streamlit exited while starting on port {port}")
            time.sleep(.25)
    process.terminate()
    pytest.fail(f"Streamlit did not start on port {port}")


def _stop_server(process):
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _assert_composition(page):
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
        page.get_by_text(heading, exact=False).wait_for()
        assert page.get_by_text(heading, exact=False).count() > 0, (heading, page.locator("body").inner_text())


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("width", [1440, 1024, 393, 320])
def test_dashboard_renders_loaded_data_without_horizontal_overflow(theme, width):
    port = 8790 + (1 if theme == "dark" else 0)
    process, address = _start_server(port, dark=theme == "dark", state="loaded")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": 1000})
            page.goto(address)
            page.get_by_text("Vamos paso a paso", exact=False).wait_for()
            _assert_composition(page)
            page.get_by_text("Rodaje de prueba").wait_for()
            page.locator(".vega-embed svg").wait_for()
            assert page.get_by_text("56,0", exact=False).is_visible()
            assert page.locator("body").evaluate("el => el.scrollWidth <= window.innerWidth")
            assert page.locator("[data-testid=stMainBlockContainer]").evaluate(
                "el => el.scrollWidth <= el.clientWidth + 1"
            )
            output = Path("test-results/ui-captures/after")
            output.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(output / f"strava-dashboard-{theme}-{width}.png"), full_page=True)
            browser.close()
    finally:
        _stop_server(process)


@pytest.mark.parametrize("state", ["empty", "connected-unloaded", "zero-run", "incomplete"])
def test_dashboard_keeps_composition_in_empty_and_partial_states(state):
    port = 8793 + ("empty", "connected-unloaded", "zero-run", "incomplete").index(state)
    process, address = _start_server(port, state=state)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1050})
            page.goto(address)
            page.get_by_text("Vamos paso a paso", exact=False).wait_for()
            _assert_composition(page)
            assert page.get_by_text("No hay un plan conectado", exact=False).count() > 0
            assert page.get_by_role("button", name="Abrir Coach").count() == 1
            assert page.get_by_text("37", exact=True).count() == 0
            assert page.get_by_text("50 km", exact=True).count() == 0
            if state in ("empty", "connected-unloaded"):
                assert page.locator(".vega-embed svg").count() == 0
            if state == "zero-run":
                assert page.get_by_text("No se devolvieron carreras de tipo Run", exact=False).count() > 0
            if state == "incomplete":
                assert page.get_by_text("Faltan fechas o datos de cobertura", exact=False).count() > 0
            browser.close()
    finally:
        _stop_server(process)


def test_dashboard_waits_for_explicit_refresh_and_navigation_stays_in_real_sections():
    process, address = _start_server(8792)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(address)
            page.get_by_text("Carga tus siete semanas de Strava para mostrar la evolución").wait_for()
            assert page.get_by_role("button", name="Actualizar datos de Strava").count() == 0
            nav = page.locator('[data-testid="stSidebar"] [data-testid="stRadio"]')
            assert "Mi plan" not in nav.inner_text()
            nav.get_by_text("Estadísticas").click()
            page.get_by_text("Weekly overview", exact=True).wait_for()
            nav.get_by_text("Coach").click()
            page.get_by_text("Coach", exact=True).wait_for()
            browser.close()
    finally:
        _stop_server(process)
