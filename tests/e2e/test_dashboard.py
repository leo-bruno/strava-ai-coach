"""Dashboard layout, navigation, theme and keyboard checks at supported widths."""
import re
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

import pytest
from playwright.sync_api import sync_playwright

from src.ui.dashboard import _date_label, _sample_sessions, _week_interval


def _start_server(port: int, *theme_options: str):
    command = [
        ".venv/bin/python", "-m", "streamlit", "run", "src/main.py",
        "--server.headless=true", f"--server.port={port}", *theme_options,
    ]
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


@pytest.fixture(scope="module")
def server():
    process, address = _start_server(8770)
    yield address
    _stop_server(process)


@pytest.fixture(scope="module")
def dark_server():
    process, address = _start_server(8771, "--theme.base=dark")
    yield address
    _stop_server(process)


def _select_option(page, label: str, option_name: str) -> None:
    selector = page.get_by_label(label)
    selector.fill(option_name)
    page.get_by_role("option", name=re.compile(option_name, re.IGNORECASE)).click()


def _assert_no_horizontal_overflow(page):
    assert page.locator("body").evaluate("el => el.scrollWidth <= window.innerWidth")
    assert page.locator("[data-testid=stMainBlockContainer]").evaluate(
        "el => el.scrollWidth <= el.clientWidth + 1"
    )


def test_dashboard_responsive_navigation_and_agenda(server):
    capture_dir = Path("test-results/ui-captures/after")
    capture_dir.mkdir(parents=True, exist_ok=True)
    reference_dir = Path("test-results/ui-captures/prototype")
    reference_dir.mkdir(parents=True, exist_ok=True)
    external_requests = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1400}, device_scale_factor=1)
        page.on("request", lambda request: external_requests.append(request.url))
        prototype = browser.new_page(viewport={"width": 1440, "height": 1400}, device_scale_factor=1)
        prototype.goto((Path(__file__).resolve().parents[2] / "docs/design/dashboard-prototype.html").as_uri())
        prototype.evaluate("""async () => {
            await Promise.all([400, 500, 600, 700, 800].map(weight => document.fonts.load(`${weight} 16px Manrope`)));
            await document.fonts.ready;
        }""")
        prototype.screenshot(path=str(reference_dir / "dashboard-1440.png"), full_page=True)
        page.goto(server)
        page.get_by_text("Tu entrenamiento esta semana").wait_for()
        assert page.evaluate("window.devicePixelRatio") == 1
        assert page.evaluate("window.visualViewport.scale") == 1
        checked_manrope = page.evaluate("""async () => {
            const weights = [400, 500, 600, 700, 800];
            await document.fonts.ready;
            return weights.map(weight => document.fonts.check(`${weight} 16px Manrope`));
        }""")
        assert all(checked_manrope), checked_manrope
        heading_font = page.locator(".st-key-dashboard-home h1").evaluate("el => getComputedStyle(el).fontFamily")
        control_font = page.get_by_label("Semana de la agenda").evaluate("el => getComputedStyle(el).fontFamily")
        assert "Manrope" in heading_font and "Manrope" in control_font
        page.screenshot(path=str(capture_dir / "dashboard-1440.png"), full_page=True)

        wrapper = page.locator(".st-key-dashboard-home")
        assert wrapper.evaluate("el => el.getBoundingClientRect().width") <= 1800
        assert page.locator(".st-key-dashboard-training h3").evaluate(
            "el => getComputedStyle(el).whiteSpace === 'nowrap' && el.getBoundingClientRect().height < 55"
        )
        assert page.locator(".st-key-dashboard-progress .dashboard-number").evaluate(
            "el => getComputedStyle(el).whiteSpace === 'nowrap'"
        )

        top_row = page.locator(".st-key-dashboard-top [data-testid=stLayoutWrapper] > [data-testid=stHorizontalBlock]").first
        assert top_row.count() == 1
        assert len(top_row.evaluate("el => getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean)")) == 3
        _assert_no_horizontal_overflow(page)

        focus_before = page.locator(":focus-visible").count()
        page.keyboard.press("Tab")
        assert page.locator(":focus-visible").count() >= max(1, focus_before)

        _select_option(page, "Semana de la agenda", "Siguiente")
        expected_agenda_end = _week_interval("next")[1]
        agenda_summary = page.locator(".st-key-dashboard-agenda [data-testid=stCaptionContainer]").last
        agenda_summary.get_by_text(re.compile(f"Semana de agenda: {expected_agenda_end:%d %b}"), exact=False).wait_for()
        assert "SEMANA ACTUAL" in page.locator(".st-key-dashboard-progress").inner_text()

        plan_expander = page.get_by_test_id("stExpander")
        plan_expander.get_by_text("Mi plan · ejemplo").click()
        page.get_by_label("Semana del plan").wait_for()
        plan_expander.get_by_text("Mi plan · ejemplo").click()
        page.get_by_label("Semana del plan").wait_for(state="hidden")

        page.locator("[data-testid=stSidebar] label").filter(has_text="Mi plan").click()
        page.get_by_role("heading", name="Mi plan").wait_for()
        _select_option(page, "Semana del plan", "Semana siguiente")
        page.get_by_text(re.compile("Plan de ejemplo · semana siguiente")).wait_for()
        for session in _sample_sessions("next"):
            page.get_by_text(f"{_date_label(session['date'])} · {session['name']}").wait_for()
        page.get_by_role("button", name=re.compile("Rodaje suave")).click()
        page.get_by_role("button", name="← Volver a Mi plan").wait_for()
        page.get_by_role("button", name="← Volver a Mi plan").click()
        page.get_by_role("heading", name="Mi plan").wait_for()
        assert "Semana siguiente" in page.get_by_label("Semana del plan").input_value()
        page.locator("[data-testid=stSidebar] label").filter(has_text="Inicio").click()
        page.get_by_text("Tu entrenamiento esta semana").wait_for()
        page.get_by_role("button", name="Abrir Coach").click()
        page.get_by_test_id("stMainBlockContainer").get_by_role("heading", name="Coach").wait_for()
        assert not any("strava" in url.lower() or "openai" in url.lower() for url in external_requests)

        laptop = browser.new_page(viewport={"width": 1024, "height": 1200}, device_scale_factor=1)
        laptop.goto(server)
        laptop.get_by_text("Tu entrenamiento esta semana").wait_for()
        laptop.screenshot(path=str(capture_dir / "dashboard-1024.png"), full_page=True)
        laptop_grid = laptop.locator(".st-key-dashboard-top > [data-testid=stLayoutWrapper] > [data-testid=stHorizontalBlock]")
        assert len(laptop_grid.evaluate("el => getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean)")) == 3
        assert laptop.get_by_label("Semana de la agenda").is_visible()
        _assert_no_horizontal_overflow(laptop)

        for width in (390, 320):
            mobile = browser.new_page(viewport={"width": width, "height": 2700}, device_scale_factor=1)
            mobile_reference = browser.new_page(viewport={"width": width, "height": 2700}, device_scale_factor=1)
            mobile_reference.goto((Path(__file__).resolve().parents[2] / "docs/design/dashboard-prototype.html").as_uri())
            mobile_reference.evaluate("""async () => {
                await Promise.all([400, 500, 600, 700, 800].map(weight => document.fonts.load(`${weight} 16px Manrope`)));
                await document.fonts.ready;
            }""")
            mobile_reference.screenshot(path=str(reference_dir / f"dashboard-{width}.png"), full_page=True)
            mobile.goto(server)
            mobile.get_by_text("Tu entrenamiento esta semana").wait_for()
            assert mobile.evaluate("window.devicePixelRatio") == 1
            mobile_label = mobile.locator(".dashboard-header-label")
            assert mobile_label.is_visible()
            assert mobile_label.evaluate("el => el.getBoundingClientRect().top >= 56")
            assert mobile.locator(".st-key-dashboard-training h3").evaluate(
                "el => getComputedStyle(el).whiteSpace === 'nowrap'"
            )
            mobile.screenshot(path=str(capture_dir / f"dashboard-{width}.png"), full_page=True)
            grid = mobile.locator(".st-key-dashboard-top > [data-testid=stLayoutWrapper] > [data-testid=stHorizontalBlock]")
            assert len(grid.evaluate("el => getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean)")) == 1
            assert mobile.get_by_label("Semana de la agenda").is_visible()
            assert mobile.locator(".st-key-dashboard-home h1").evaluate(
                "el => getComputedStyle(el).wordBreak === 'normal' && getComputedStyle(el).overflowWrap === 'normal'"
            )
            assert mobile.locator(".st-key-dashboard-home h1").evaluate("""el => {
                const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
                let node;
                while ((node = walker.nextNode())) {
                    const index = node.textContent.indexOf('entrenamiento');
                    if (index < 0) continue;
                    const range = document.createRange();
                    range.setStart(node, index);
                    range.setEnd(node, index + 'entrenamiento'.length);
                    return range.getClientRects().length === 1;
                }
                return false;
            }""")
            _assert_no_horizontal_overflow(mobile)
            assert mobile.evaluate("window.devicePixelRatio") == 1
            if width == 390:
                mobile.locator(".st-key-dashboard-agenda").screenshot(path=str(capture_dir / "dashboard-390-agenda.png"))
                mobile.locator(".st-key-coach-preview").screenshot(path=str(capture_dir / "dashboard-390-coach.png"))
            mobile_reference.close()
            mobile.close()
        prototype.close()
        browser.close()


def test_dashboard_theme_surfaces_follow_light_and_dark(server, dark_server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        themes = []
        for address, expected_base in ((server, "light"), (dark_server, "dark")):
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
            page.goto(address)
            page.get_by_text("Tu entrenamiento esta semana").wait_for()
            card = page.locator(".st-key-dashboard-progress")
            theme = card.evaluate(r"""el => {
                const app = document.querySelector('.stApp');
                const appStyle = getComputedStyle(app);
                const cardStyle = getComputedStyle(el);
                const heading = getComputedStyle(el.querySelector('h2')).color;
                const appText = appStyle.color;
                const appBg = appStyle.backgroundColor;
                function color(value) {
                    if (value.startsWith('color(srgb ')) {
                        const [r, g, b, alpha = 1] = value.slice(11, -1).split(/[ /]+/).map(Number);
                        return [r * 255, g * 255, b * 255, alpha];
                    }
                    const values = value.match(/[\d.]+/g).slice(0,3).map(Number);
                    return [...values, value.startsWith('rgba') ? Number(value.match(/,\s*([\d.]+)\)$/)[1]) : 1];
                }
                function lum(value) {
                    return value.slice(0,3).map(x => { x /= 255; return x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4; })
                        .reduce((sum, x, i) => sum + x * [.2126,.7152,.0722][i], 0);
                }
                function composite(foreground, background) {
                    const f = color(foreground), b = color(background), alpha = f[3];
                    return [0,1,2].map(i => f[i] * alpha + b[i] * (1 - alpha));
                }
                function ratio(a, b) { const x = lum(a), y = lum(b); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05); }
                const cardSurface = composite(cardStyle.backgroundColor, appBg);
                return {
                    appBackground: appBg,
                    appText,
                    cardBackground: cardStyle.backgroundColor,
                    cardText: heading,
                    contrast: ratio(color(appText), color(appBg)),
                    cardContrast: ratio(color(heading), cardSurface),
                };
            }""")
            assert theme["appBackground"] not in ("rgba(0, 0, 0, 0)", "transparent")
            assert theme["cardBackground"] not in ("rgba(0, 0, 0, 0)", "transparent")
            assert theme["contrast"] >= 4.5
            assert theme["cardContrast"] >= 4.5
            themes.append(theme)
            page.screenshot(path=f"test-results/ui-captures/after/dashboard-{expected_base}.png", full_page=True)
            page.close()
        # Inicio uses the prototype's fixed light palette in either Streamlit theme.
        assert themes[0]["appBackground"] == themes[1]["appBackground"]
        assert themes[0]["appText"] == themes[1]["appText"]
        browser.close()
