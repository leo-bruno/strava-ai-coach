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
            assert page.get_by_role("button", name="Registrar carrera").count() == 0
            assert page.locator("#modal").count() == 0
            assert page.locator("#goalKm").inner_text() == "37"
            assert page.locator("#total").inner_text() == "128,4"
            assert page.locator("#sessions .session").count() == 3
            assert page.get_by_text("Rodaje por el Retiro", exact=True).is_visible()
            assert page.get_by_text("Series para ir más lejos", exact=True).is_visible()
            assert page.get_by_text("Domingo de tirada larga", exact=True).is_visible()
            assert page.title() == "Runner Coach"
            logo = page.locator(".stride-root .logo")
            assert logo.is_visible()
            assert "Runner Coach" in logo.inner_text()
            assert logo.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
            assert logo.evaluate(
                "el => el.getBoundingClientRect().height <= parseFloat(getComputedStyle(el).fontSize) * 1.3"
            )
            assert page.get_by_role("heading", name="Vamos a por más, Leo").is_visible()
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

            assert page.get_by_role("button", name="Registrar carrera").count() == 0
            assert page.locator("#modal").count() == 0
            assert page.locator("#goalKm").inner_text() == "37"
            assert page.locator("#total").inner_text() == "128,4"
            assert page.locator("#sessions .session").count() == 3
            assert page.get_by_text("Rodaje de prueba", exact=True).count() == 0

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


@pytest.mark.parametrize("width", [1440, 393])
def test_demo_chat_drawer_stays_below_app_header_and_closes_accessibly(width):
    port = 18802 if width == 1440 else 18803
    process, address = _start_server(port)
    try:
        with sync_playwright() as playwright:
            browser, page = _start_page(playwright, address, width, 844)
            if width == 1440:
                quick_launcher = page.get_by_label("Pregunta a tu entrenador")
                quick_launcher.fill("¿Cómo voy esta semana?")
                quick_launcher.press("Enter")
                quick_drawer = page.get_by_role("dialog", name="Tu entrenador IA")
                quick_drawer.wait_for()
                assert "37 de los 50 km semanales" in quick_drawer.inner_text()
                page.keyboard.press("Escape")
                assert not quick_drawer.is_visible()
                assert quick_launcher.evaluate("el => el === el.getRootNode().activeElement")

            if width <= 600:
                page.locator(".mobile-nav [data-view='plan']").click()
            else:
                page.locator(".stride-root aside nav [data-view='plan']").click()
            launcher = page.get_by_role("button", name="Hablar con mi entrenador")
            launcher.click()
            drawer = page.get_by_role("dialog", name="Tu entrenador IA")
            drawer.wait_for()
            assert "Tu plan de ejemplo prepara una media maratón" in drawer.inner_text()
            backdrop = page.locator("#drawerBackdrop")
            assert backdrop.is_visible()

            header = page.locator('[data-testid="stHeader"]')
            header_box = header.bounding_box()
            drawer_box = drawer.bounding_box()
            assert header_box and drawer_box
            assert drawer_box["y"] >= header_box["y"] + header_box["height"] - 1
            assert drawer_box["y"] + drawer_box["height"] <= 844
            assert page.locator("body").evaluate("el => el.scrollWidth <= window.innerWidth")
            title_box = drawer.get_by_role("heading", name="Tu entrenador IA").bounding_box()
            composer_box = drawer.locator(".chat-launch").bounding_box()
            assert title_box and title_box["y"] >= drawer_box["y"]
            assert composer_box and composer_box["y"] + composer_box["height"] <= drawer_box["y"] + drawer_box["height"]
            assert drawer.get_by_label("Tu mensaje").evaluate("el => el === el.getRootNode().activeElement")

            drawer.locator(".drawer-head h2").click()
            assert drawer.is_visible()
            drawer.get_by_label("Tu mensaje").focus()

            close_button = drawer.get_by_role("button", name="Cerrar conversación")
            send_button = drawer.get_by_role("button", name="Enviar mensaje")
            close_button.focus()
            page.keyboard.press("Shift+Tab")
            assert send_button.evaluate(
                "el => el === el.getRootNode().activeElement"
            )
            page.keyboard.press("Tab")
            assert close_button.evaluate(
                "el => el === el.getRootNode().activeElement"
            )
            drawer.get_by_label("Tu mensaje").focus()

            drawer.get_by_role("button", name="Cerrar conversación").click()
            assert not drawer.is_visible()
            assert not backdrop.is_visible()
            assert launcher.evaluate("el => el === el.getRootNode().activeElement")
            assert not page.locator(".stride-root main").evaluate("el => el.inert")
            assert not page.locator(".stride-root > aside").evaluate("el => el.inert")

            launcher.click()
            drawer.wait_for()
            page.keyboard.press("Escape")
            assert not drawer.is_visible()
            assert not backdrop.is_visible()
            assert launcher.evaluate("el => el === el.getRootNode().activeElement")
            assert not page.locator(".stride-root main").evaluate("el => el.inert")
            assert not page.locator(".stride-root > aside").evaluate("el => el.inert")

            if width == 1440:
                launcher.click()
                drawer.wait_for()
                background_control = page.locator(".stride-root aside nav [data-view='all']")
                target = background_control.bounding_box()
                assert target
                page.mouse.click(target["x"] + target["width"] / 2, target["y"] + target["height"] / 2)
                assert not drawer.is_visible()
                assert not backdrop.is_visible()
                assert page.locator("#training").is_visible()
                assert launcher.evaluate("el => el === el.getRootNode().activeElement")
                assert not page.locator(".stride-root main").evaluate("el => el.inert")
                assert not page.locator(".stride-root > aside").evaluate("el => el.inert")

            assert page.get_by_role("button", name="Registrar carrera").count() == 0
            assert page.locator("#modal").count() == 0
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
