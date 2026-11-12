"""Browser checks for the supplied prototype demo and its real app routes."""

import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

import pytest
from playwright.sync_api import sync_playwright


def _start_server(port: int, *, dark=False):
    project_root = Path(__file__).resolve().parents[2]
    launcher = Path(f"/tmp/stride_demo_e2e_{port}.py")
    launcher.write_text(
        f"import sys\nsys.path.insert(0, {str(project_root)!r})\n"
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


def _start_page(playwright, address, width, height=1000):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": width, "height": height})
    page.goto(address)
    page.get_by_role("button", name="Registrar carrera").wait_for()
    page.get_by_role("heading", name="Vamos a por más, Leo").wait_for()
    return browser, page


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("width", [1440, 1024, 393, 320])
def test_prototype_composition_is_faithful_responsive_and_theme_safe(theme, width):
    port = 18780 + (10 if theme == "dark" else 0) + [1440, 1024, 393, 320].index(width)
    process, address = _start_server(port, dark=theme == "dark")
    try:
        with sync_playwright() as playwright:
            browser, page = _start_page(playwright, address, width)
            for text in (
                "stride.", "OBJETIVO SEMANAL", "DISTANCIA TOTAL", "RITMO MEDIO",
                "TIEMPO EN MOVIMIENTO", "Tu progreso", "Tu semana", "Últimas carreras",
                "Entrenar mejor empieza", "datos ficticios", "no consulta Strava ni OpenAI",
            ):
                assert page.get_by_text(text, exact=False).count() > 0, text
            assert page.locator("#add").is_visible()
            assert page.get_by_role("heading", name="Vamos a por más, Leo").is_visible()
            action_box = page.locator("#add").bounding_box()
            assert action_box and action_box["y"] < 900, action_box
            assert page.locator(".stride-root").get_by_role(
                "button", name="Estadísticas", exact=False
            ).count() == 0
            assert page.locator(".stride-root [data-app-route]").count() == 0
            assert page.get_by_role("button", name="Coach real", exact=False).count() == 0
            assert page.get_by_role("button", name="Abrir el Coach real", exact=False).count() == 0
            assert page.locator("[data-testid='stSidebar']").is_hidden()
            assert page.locator("body").evaluate("el => el.scrollWidth <= window.innerWidth")
            assert page.locator(".stride-root").evaluate(
                "el => el.scrollWidth <= el.clientWidth + 1"
            )
            output = Path("test-results/ui-captures/after")
            output.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(output / f"stride-demo-{theme}-{width}.png"), full_page=True)
            page.locator(".notice").scroll_into_view_if_needed()
            assert page.locator(".notice").is_visible()
            browser.close()
    finally:
        _stop_server(process)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_demo_controls_week_month_chart_days_and_plan_tabs(theme):
    process, address = _start_server(18801 + (theme == "dark"), dark=theme == "dark")
    try:
        with sync_playwright() as playwright:
            browser, page = _start_page(playwright, address, 1440)
            axis = page.locator(".axis")
            assert "Lun" in axis.inner_text()
            page.get_by_label("Periodo del gráfico").select_option("month")
            assert "1 nov" in axis.inner_text()
            page.get_by_label("Periodo del gráfico").select_option("week")
            assert "Dom" in axis.inner_text()

            expected_workouts = (
                "Empieza con calma", "Un poco de velocidad", "Hoy, disfruta del camino",
                "Recargar también cuenta", "Encuentra tu ritmo", "Sin prisa, sin pausa",
                "Un poquito más lejos",
            )
            for index, (day, expected) in enumerate(zip(
                ("LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"),
                expected_workouts,
            )):
                page.get_by_role("button", name=f"{day} {9 + index}, ver entrenamiento").click()
                assert page.locator(".workout h3").inner_text() == expected

            page.get_by_role("button", name="Registrar carrera").click()
            dialog = page.locator("#modal")
            assert dialog.evaluate("el => el.open")
            dialog.get_by_label("Nombre de la carrera").fill("Rodaje de prueba")
            dialog.get_by_label("Distancia en km").fill("2")
            dialog.get_by_label("Duración en minutos").fill("12")
            dialog.get_by_role("button", name="Guardar carrera").click()
            assert page.get_by_text("Rodaje de prueba", exact=True).count() == 1
            assert page.locator("#goalKm").inner_text() == "39"
            assert page.evaluate("localStorage.getItem('stride-runs')").find("Rodaje de prueba") >= 0
            page.keyboard.press("Escape")
            page.get_by_role("heading", name="Vamos a por más, Leo").wait_for()
            page.reload()
            page.get_by_role("button", name="Registrar carrera").wait_for()
            assert page.locator("#goalKm").inner_text() == "39"
            assert page.get_by_text("Rodaje de prueba", exact=True).count() == 1

            page.locator("[data-view='plan']").first.click()
            assert page.locator("#training").is_visible()
            page.locator("[data-plan='past']").click()
            assert page.locator("#planHeading").inner_text() == "Sesiones anteriores · Noviembre"
            assert "Tirada larga · Semana 5" in page.locator("#planList").inner_text()
            page.locator("[data-plan='future']").click()
            assert "Semana 7" in page.locator("#planList").inner_text()
            page.locator("[data-plan='library']").click()
            assert "Tu primera media maratón" in page.locator("#planList").inner_text()
            browser.close()
    finally:
        _stop_server(process)


def test_demo_canned_chat_has_modal_focus_restore_and_keyboard_escape():
    process, address = _start_server(18802)
    try:
        with sync_playwright() as playwright:
            browser, page = _start_page(playwright, address, 1024)
            launcher = page.get_by_label("Pregunta a tu entrenador")
            launcher.fill("¿Cómo voy esta semana?")
            launcher.press("Enter")
            drawer = page.get_by_role("dialog", name="Tu entrenador IA")
            drawer.wait_for()
            assert "37 de los 50 km semanales" in drawer.inner_text()
            assert drawer.get_by_label("Tu mensaje").evaluate("el => el === el.getRootNode().activeElement")
            page.keyboard.press("Shift+Tab")
            assert drawer.get_by_role("button", name="Cerrar conversación").evaluate(
                "el => el === el.getRootNode().activeElement"
            )
            page.keyboard.press("Tab")
            assert drawer.get_by_label("Tu mensaje").evaluate("el => el === el.getRootNode().activeElement")
            page.keyboard.press("Escape")
            assert not drawer.is_visible()
            assert launcher.evaluate("el => el === el.getRootNode().activeElement")

            page.set_viewport_size({"width": 393, "height": 844})
            page.get_by_role("button", name="Entrenador IA · demo").click()
            drawer.wait_for()
            assert "Demo interactiva" in drawer.inner_text()
            page.keyboard.press("Escape")
            assert not drawer.is_visible()

            add = page.get_by_role("button", name="Registrar carrera")
            add.click()
            modal = page.locator("#modal")
            assert modal.evaluate("el => el.open")
            page.keyboard.press("Escape")
            assert not modal.is_visible()
            assert add.evaluate("el => el === el.getRootNode().activeElement")
            browser.close()
    finally:
        _stop_server(process)


@pytest.mark.parametrize(("width", "port"), [(1440, 18804), (393, 18805)])
def test_home_menu_opens_native_sidebar_and_routes_back_from_coach(width, port):
    process, address = _start_server(port)
    try:
        with sync_playwright() as playwright:
            browser, page = _start_page(playwright, address, width)
            nav = page.locator('[data-testid="stSidebar"] [data-testid="stRadio"]')
            assert nav.is_hidden()
            page.get_by_role("button", name="Abrir navegación").click()
            nav.wait_for(state="visible")
            assert page.locator("body").evaluate("el => el.scrollWidth <= window.innerWidth")
            assert page.get_by_role("button", name="Estadísticas", exact=False).count() == 0
            assert page.locator(".stride-root [data-app-route]").count() == 0
            nav.locator("label").filter(has_text="Coach").click()
            page.locator('[data-testid="stMainBlockContainer"] h1').filter(
                has_text="Coach"
            ).wait_for()
            assert nav.is_visible(), page.locator("body").inner_text()
            assert "Coach" in nav.inner_text()
            assert page.locator("body").evaluate("el => el.scrollWidth <= window.innerWidth")
            assert page.get_by_role("button", name="Registrar carrera").count() == 0
            assert page.get_by_text("Rodaje por el Retiro", exact=True).count() == 0
            nav.locator("label").filter(has_text="Inicio").click()
            page.get_by_role("heading", name="Vamos a por más, Leo").wait_for()
            assert nav.is_hidden()
            assert page.locator("body").evaluate("el => el.scrollWidth <= window.innerWidth")
            browser.close()
    finally:
        _stop_server(process)
