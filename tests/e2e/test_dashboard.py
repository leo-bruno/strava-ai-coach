"""Browser checks for the supplied prototype demo and its real app routes."""

import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

import pytest
from playwright.sync_api import sync_playwright


def _start_server(port: int, *, dark=False, initial_view=None):
    project_root = Path(__file__).resolve().parents[2]
    launcher = Path(f"/tmp/stride_demo_e2e_{port}.py")
    seed_view = ""
    if initial_view:
        seed_view = (
            f"if 'dashboard_view' not in st.session_state:\n"
            f"    st.session_state['dashboard_view'] = {initial_view!r}\n"
            f"    st.session_state['dashboard_navigation'] = {initial_view!r}\n"
        )
    launcher.write_text(
        f"import sys\nsys.path.insert(0, {str(project_root)!r})\n"
        "import streamlit as st\nfrom src.ui.app import render_app\n"
        f"{seed_view}render_app()\n"
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


def _start_page(playwright, address, width, height=1000, *, native_view=None):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": width, "height": height})
    page.goto(address)
    if native_view == "Estadísticas":
        page.get_by_role("heading", name="Estadísticas").wait_for()
    else:
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
                "Runner Coach", "OBJETIVO SEMANAL", "DISTANCIA TOTAL", "RITMO MEDIO",
                "TIEMPO EN MOVIMIENTO", "Tu progreso", "Tu semana", "Últimas carreras",
                "Entrenar mejor empieza", "datos ficticios", "no consulta Strava ni OpenAI",
            ):
                assert page.get_by_text(text, exact=False).count() > 0, text
            assert page.locator("#add").is_visible()
            assert page.title() == "Runner Coach"
            logo = page.locator(".stride-root .logo")
            assert logo.is_visible()
            assert "Runner Coach" in logo.inner_text()
            assert logo.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
            assert logo.evaluate(
                "el => el.getBoundingClientRect().height <= parseFloat(getComputedStyle(el).fontSize) * 1.3"
            )
            assert page.get_by_role("heading", name="Vamos a por más, Leo").is_visible()
            action_box = page.locator("#add").bounding_box()
            assert action_box and action_box["y"] < 900, action_box
            assert page.locator(".stride-root").get_by_role(
                "button", name="Estadísticas", exact=False
            ).count() == 0
            assert page.locator(".stride-root [data-app-route]").count() == 0
            assert page.get_by_role("button", name="Menú", exact=True).count() == 0
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
@pytest.mark.parametrize("width", [1440, 1024, 393])
def test_period_selector_has_inset_caret_and_keeps_labels_clear(theme, width):
    port = 19040 + (10 if theme == "dark" else 0) + [1440, 1024, 393].index(width)
    process, address = _start_server(port, dark=theme == "dark")
    try:
        with sync_playwright() as playwright:
            browser, page = _start_page(playwright, address, width)
            period = page.locator("#period")
            metrics = period.evaluate("""el => {
                const style = getComputedStyle(el)
                const rect = el.getBoundingClientRect()
                const canvas = document.createElement('canvas')
                const context = canvas.getContext('2d')
                context.font = style.font
                const maxLabelWidth = Math.max(...[...el.options].map(option => context.measureText(option.text).width))
                return {
                    appearance: style.appearance,
                    paddingLeft: parseFloat(style.paddingLeft),
                    paddingRight: parseFloat(style.paddingRight),
                    backgroundImage: style.backgroundImage,
                    backgroundPosition: style.backgroundPosition,
                    width: rect.width,
                    labelWidth: maxLabelWidth,
                    scrollWidth: el.scrollWidth,
                    clientWidth: el.clientWidth,
                }
            }""")
            assert metrics["appearance"] == "none", metrics
            assert metrics["paddingRight"] == 34, metrics
            assert "linear-gradient" in metrics["backgroundImage"], metrics
            assert "20px" in metrics["backgroundPosition"] and "16px" in metrics["backgroundPosition"], metrics
            assert metrics["width"] >= metrics["labelWidth"] + metrics["paddingLeft"] + metrics["paddingRight"], metrics
            assert metrics["scrollWidth"] <= metrics["clientWidth"], metrics
            period.select_option("month")
            assert period.input_value() == "month"
            period.select_option("week")
            assert period.input_value() == "week"
            assert page.locator("body").evaluate("el => el.scrollWidth <= window.innerWidth")
            output = Path("test-results/ui-captures/after")
            output.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(output / f"period-select-{theme}-{width}.png"))
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


def test_native_sidebar_routes_between_real_coach_and_home():
    process, address = _start_server(18804, initial_view="Estadísticas")
    try:
        with sync_playwright() as playwright:
            browser, page = _start_page(
                playwright, address, 1440, native_view="Estadísticas"
            )
            nav = page.locator('[data-testid="stSidebar"] [data-testid="stRadio"]')
            page.get_by_role("heading", name="Estadísticas").wait_for()
            nav.wait_for(state="visible")
            assert "Runner Coach" in page.locator('[data-testid="stSidebar"]').inner_text()
            nav.locator("label").filter(has_text="Coach").click()
            page.locator('[data-testid="stMainBlockContainer"] h1').filter(
                has_text="Coach"
            ).wait_for()
            assert nav.is_visible(), page.locator("body").inner_text()
            assert "Coach" in nav.inner_text()
            assert page.get_by_role("button", name="Registrar carrera").count() == 0
            assert page.get_by_text("Rodaje por el Retiro", exact=True).count() == 0
            nav.locator("label").filter(has_text="Inicio").click()
            page.get_by_role("heading", name="Vamos a por más, Leo").wait_for()
            assert nav.is_hidden()
            browser.close()
    finally:
        _stop_server(process)
