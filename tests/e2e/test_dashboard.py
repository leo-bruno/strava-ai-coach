"""Responsive dashboard, planning navigation and keyboard smoke coverage."""
import re
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

import pytest
from playwright.sync_api import sync_playwright

from src.ui.dashboard import _date_label, _sample_sessions


@pytest.fixture(scope="module")
def server():
    process = subprocess.Popen(
        [".venv/bin/python", "-m", "streamlit", "run", "src/main.py", "--server.headless=true", "--server.port=8765"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(60):
        try:
            urlopen("http://127.0.0.1:8765", timeout=1)
            break
        except Exception:
            time.sleep(.5)
    else:
        process.terminate()
        pytest.fail("Streamlit server did not start")
    yield "http://127.0.0.1:8765"
    process.terminate()
    process.wait(timeout=10)


def test_dashboard_plan_detail_keyboard_and_responsive_layout(server):
    capture_dir = Path("test-results/ui-captures")
    capture_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.goto(server)
        page.get_by_text("Tu entrenamiento esta semana").wait_for()
        page.screenshot(path=str(capture_dir / "dashboard-desktop.png"), full_page=True)
        page.keyboard.press("Tab")
        assert page.locator(":focus-visible").count() >= 1
        page.locator("[data-testid=stSidebar] label").filter(has_text="Mi plan").click()
        page.get_by_role("heading", name="Mi plan").wait_for()
        page.get_by_label("Semana del plan").fill("Siguiente")
        page.get_by_role("option", name=re.compile("Semana siguiente")).click()
        page.get_by_text(re.compile("Plan de ejemplo · semana siguiente")).wait_for()
        for session in _sample_sessions("next"):
            page.get_by_text(f"{_date_label(session['date'])} · {session['name']}").wait_for()
        page.screenshot(path=str(capture_dir / "plan-desktop.png"), full_page=True)
        page.get_by_role("button", name=re.compile("Rodaje suave")).click()
        page.get_by_role("button", name="← Volver a Mi plan").wait_for()
        page.screenshot(path=str(capture_dir / "plan-detail-desktop.png"), full_page=True)
        page.get_by_role("button", name="← Volver a Mi plan").click()
        page.get_by_role("heading", name="Mi plan").wait_for()
        assert "Semana siguiente" in page.get_by_label("Semana del plan").input_value()
        mobile_plan = browser.new_page(viewport={"width": 390, "height": 844})
        mobile_plan.goto(server)
        mobile_plan.get_by_text("Tu entrenamiento esta semana").wait_for()
        mobile_plan.locator('button[aria-controls="stSidebar"]').click(timeout=5000)
        mobile_plan.locator("[data-testid=stSidebar] label").filter(has_text="Mi plan").click(timeout=5000)
        mobile_plan.get_by_role("heading", name="Mi plan").wait_for()
        mobile_plan.locator('button[aria-controls="stSidebar"]').evaluate("el => el.click()")
        mobile_plan.locator('[data-testid="stSidebar"][data-collapsed="true"]').wait_for()
        mobile_plan.wait_for_timeout(800)
        sidebar_width = mobile_plan.locator("[data-testid=stSidebar]").evaluate("el => el.getBoundingClientRect().width")
        main_geometry = mobile_plan.locator("[data-testid=stMainBlockContainer]").evaluate("el => ({x:el.getBoundingClientRect().x,w:el.getBoundingClientRect().width})")
        assert sidebar_width == 0
        assert main_geometry["x"] == 0 and main_geometry["w"] == 390
        mobile_plan.get_by_label("Semana del plan").fill("Siguiente")
        mobile_plan.get_by_role("option", name=re.compile("Semana siguiente")).click()
        mobile_plan.get_by_text(re.compile("Plan de ejemplo · semana siguiente")).wait_for()
        for session in _sample_sessions("next"):
            mobile_plan.get_by_text(f"{_date_label(session['date'])} · {session['name']}").wait_for()
        mobile_plan.screenshot(path=str(capture_dir / "plan-mobile.png"), full_page=True)
        assert mobile_plan.locator("body").evaluate("el => el.scrollWidth <= window.innerWidth")
        mobile_plan.get_by_role("button", name=re.compile("Rodaje suave")).click()
        mobile_plan.get_by_role("button", name="← Volver a Mi plan").wait_for()
        mobile_plan.screenshot(path=str(capture_dir / "plan-detail-mobile.png"), full_page=True)
        mobile_plan.get_by_role("button", name="← Volver a Mi plan").click()
        mobile_home = browser.new_page(viewport={"width": 390, "height": 844})
        mobile_home.goto(server)
        mobile_home.get_by_text("Tu entrenamiento esta semana").wait_for()
        mobile_home.screenshot(path=str(capture_dir / "dashboard-mobile.png"), full_page=True)
        assert mobile_home.locator("body").evaluate("el => el.scrollWidth <= window.innerWidth")
        browser.close()
