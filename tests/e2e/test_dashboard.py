"""Dashboard layout, navigation, theme and keyboard checks at supported widths."""
import re
from datetime import date
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

import pytest
from playwright.sync_api import sync_playwright

from src.ui.dashboard import _dashboard_summary, _date_label, _format_kilometers, _sample_sessions, _week_interval


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


def _assert_dashboard_card_geometry(page):
    geometry = page.evaluate("""() => {
        const cardSelectors = [
            '.st-key-dashboard-progress', '.st-key-dashboard-pace',
            '.st-key-dashboard-training', '.st-key-dashboard-agenda',
            '.st-key-dashboard-performance', '.st-key-coach-preview'
        ];
        const paddings = cardSelectors.map(selector => {
            const style = getComputedStyle(document.querySelector(selector));
            return [parseFloat(style.paddingTop), parseFloat(style.paddingBottom)];
        });
        const bottom = selector => document.querySelector(selector).getBoundingClientRect().bottom;
        const top = selector => document.querySelector(selector).getBoundingClientRect().top;
        const date = document.querySelector('.st-key-dashboard-training .dashboard-date');
        const dateStyle = getComputedStyle(date);
        const dateRect = date.getBoundingClientRect();
        const columnRect = date.closest('[data-testid="stColumn"]').getBoundingClientRect();
        const row = date.closest('[class*="st-key-training-"]');
        const rowStyle = getComputedStyle(row);
        const title = row.querySelector('.dashboard-session-title').getBoundingClientRect();
        const trainingCard = document.querySelector('.st-key-dashboard-training');
        const trainingRows = [...trainingCard.querySelectorAll('[class*="st-key-training-"]')];
        const lastRow = trainingRows[trainingRows.length - 1];
        const lastDetailBottom = lastRow.querySelector('.dashboard-session-detail').getBoundingClientRect().bottom;
        const progressRect = document.querySelector('.st-key-dashboard-progress').getBoundingClientRect();
        const paceRect = document.querySelector('.st-key-dashboard-pace').getBoundingClientRect();
        const trainingRect = trainingCard.getBoundingClientRect();
        const paceKicker = document.querySelector('.st-key-dashboard-pace .dashboard-kicker').getBoundingClientRect();
        const paceBars = document.querySelector('.st-key-dashboard-pace .dashboard-pace-bars').getBoundingClientRect();
        const trainingKicker = trainingCard.querySelector('.dashboard-kicker').getBoundingClientRect();
        const range = document.createRange();
        range.selectNodeContents(date);
        return {
            viewportWidth: window.innerWidth,
            paddings,
            progressCopyBottomGap: bottom('.st-key-dashboard-progress')
                - document.querySelector('.st-key-dashboard-progress .dashboard-progress-copy').getBoundingClientRect().bottom,
            trainingToPerformanceGap: top('.st-key-dashboard-performance') - bottom('.st-key-dashboard-training'),
            agendaToCoachGap: top('.st-key-coach-preview') - bottom('.st-key-dashboard-agenda'),
            dateTextRectCount: range.getClientRects().length,
            dateFontFamily: dateStyle.fontFamily,
            dateFontSize: parseFloat(dateStyle.fontSize),
            dateFontWeight: dateStyle.fontWeight,
            dateWhiteSpace: dateStyle.whiteSpace,
            dateMinWidth: parseFloat(dateStyle.minWidth),
            dateCenterOffset: Math.abs((dateRect.left + dateRect.right) / 2 - (columnRect.left + columnRect.right) / 2),
            rowPadding: [parseFloat(rowStyle.paddingLeft), parseFloat(rowStyle.paddingRight)],
            dateBeforeTitle: dateRect.right <= title.left,
            trainingKickerTopInset: trainingKicker.top - trainingRect.top,
            trainingLastDetailBottomInset: trainingRect.bottom - lastDetailBottom,
            lastRowPaddingBottom: parseFloat(getComputedStyle(lastRow).paddingBottom),
            paceKickerTopInset: paceKicker.top - paceRect.top,
            paceBarsBottomInset: paceRect.bottom - paceBars.bottom,
            progressToTrainingGap: trainingRect.top - progressRect.bottom,
            paceToTrainingGap: trainingRect.top - paceRect.bottom,
            summaryCardHeightDifference: Math.abs(progressRect.height - paceRect.height),
        };
    }""")
    assert all(abs(top - bottom) < 0.1 for top, bottom in geometry["paddings"]), geometry
    assert geometry["progressCopyBottomGap"] >= 8, geometry
    assert geometry["trainingToPerformanceGap"] == pytest.approx(16, abs=1), geometry
    assert geometry["agendaToCoachGap"] == pytest.approx(16, abs=1), geometry
    assert geometry["dateTextRectCount"] == 1, geometry
    assert geometry["dateFontFamily"].startswith("system-ui"), geometry
    assert 12 <= geometry["dateFontSize"] <= 13, geometry
    assert geometry["dateFontWeight"] == "700", geometry
    assert geometry["dateWhiteSpace"] == "nowrap", geometry
    assert geometry["dateMinWidth"] >= 52, geometry
    assert geometry["dateCenterOffset"] <= 1, geometry
    assert min(geometry["rowPadding"]) >= 8, geometry
    assert geometry["dateBeforeTitle"], geometry
    assert geometry["trainingKickerTopInset"] >= (14 if geometry["viewportWidth"] <= 680 else 16), geometry
    assert geometry["trainingLastDetailBottomInset"] >= (14 if geometry["viewportWidth"] <= 680 else 16), geometry
    assert geometry["lastRowPaddingBottom"] >= 12, geometry
    assert geometry["paceKickerTopInset"] >= (14 if geometry["viewportWidth"] <= 680 else 16), geometry
    assert geometry["paceBarsBottomInset"] >= 12, geometry
    if geometry["viewportWidth"] > 680:
        assert abs(geometry["paceKickerTopInset"] - geometry["paceBarsBottomInset"]) <= 6, geometry
        assert geometry["summaryCardHeightDifference"] <= 1, geometry
        assert geometry["progressToTrainingGap"] == pytest.approx(16, abs=1), geometry
    assert geometry["paceToTrainingGap"] == pytest.approx(16, abs=1), geometry


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
        page.get_by_text("Cómo está tu entrenamiento esta semana").wait_for()
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
        summary = _dashboard_summary(date.today())
        progress_copy = page.locator(".st-key-dashboard-progress .dashboard-progress-copy")
        assert f"{_format_kilometers(summary['completed_distance_km'])} km" in progress_copy.inner_text()
        assert f"{summary['completed_sessions']} de {summary['planned_sessions']} entrenamientos" in progress_copy.inner_text()
        assert page.locator(".st-key-dashboard-progress .dashboard-arc").get_attribute("aria-label") == (
            f"{summary['progress_percent']} % de la distancia prevista"
        )
        assert re.search(r"(?:Lun|Mar|Mié|Jue|Vie|Sáb|Dom) \d{2}", page.locator(".st-key-dashboard-training").inner_text())

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
        assert len(top_row.evaluate("el => getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean)")) == 2
        _assert_dashboard_card_geometry(page)
        _assert_no_horizontal_overflow(page)

        desktop_16 = browser.new_page(viewport={"width": 1728, "height": 1117}, device_scale_factor=1)
        desktop_16.goto(server)
        desktop_16.get_by_text("Cómo está tu entrenamiento esta semana").wait_for()
        _assert_dashboard_card_geometry(desktop_16)
        assert desktop_16.evaluate("window.devicePixelRatio") == 1
        assert desktop_16.locator(".st-key-dashboard-home").evaluate(
            "el => el.getBoundingClientRect().width <= 1800"
        )
        desktop_16_layout = desktop_16.evaluate("""() => ({
            viewportHeight: window.innerHeight,
            cards: ['.st-key-dashboard-summary', '.st-key-dashboard-progress', '.st-key-dashboard-pace',
                '.st-key-dashboard-training', '.st-key-dashboard-performance', '.st-key-dashboard-agenda',
                '.st-key-coach-preview'].map(selector => {
                const rect = document.querySelector(selector).getBoundingClientRect();
                return [selector, rect.top, rect.bottom, rect.height];
            }),
        })""")
        desktop_16.screenshot(path=str(capture_dir / "dashboard-1728.png"), full_page=True)
        assert max(card[2] for card in desktop_16_layout["cards"] if card[0] in ('.st-key-dashboard-performance', '.st-key-coach-preview')) <= desktop_16_layout["viewportHeight"], desktop_16_layout
        _assert_no_horizontal_overflow(desktop_16)
        desktop_16.close()

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
        page.get_by_text("Cómo está tu entrenamiento esta semana").wait_for()
        page.get_by_role("button", name="Abrir Coach").click()
        page.get_by_test_id("stMainBlockContainer").get_by_role("heading", name="Coach").wait_for()
        assert not any("strava" in url.lower() or "openai" in url.lower() for url in external_requests)

        laptop = browser.new_page(viewport={"width": 1024, "height": 1200}, device_scale_factor=1)
        laptop.goto(server)
        laptop.get_by_text("Cómo está tu entrenamiento esta semana").wait_for()
        laptop.screenshot(path=str(capture_dir / "dashboard-1024.png"), full_page=True)
        laptop_grid = laptop.locator(".st-key-dashboard-top > [data-testid=stLayoutWrapper] > [data-testid=stHorizontalBlock]")
        assert len(laptop_grid.evaluate("el => getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean)")) == 2
        assert laptop.get_by_label("Semana de la agenda").is_visible()
        _assert_dashboard_card_geometry(laptop)
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
            mobile.get_by_text("Cómo está tu entrenamiento esta semana").wait_for()
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
            _assert_dashboard_card_geometry(mobile)
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
            page.get_by_text("Cómo está tu entrenamiento esta semana").wait_for()
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


def _measure_agenda_grid(grid):
    return grid.evaluate("""grid => {
        const cards = [...grid.querySelectorAll('.agenda-card')];
        const surfaces = cards.map(card => {
            const rect = card.getBoundingClientRect();
            const style = getComputedStyle(card);
            return {
                left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, height: rect.height,
                scrollWidth: card.scrollWidth, clientWidth: card.clientWidth,
                boxSizing: style.boxSizing, minWidth: style.minWidth, maxWidth: style.maxWidth,
            };
        });
        const cardMetrics = cards.map((card, index) => {
            const rect = card.getBoundingClientRect();
            const surface = surfaces[index];
            const kicker = card.querySelector('.dashboard-kicker');
            const title = card.querySelector('.dashboard-session-title');
            const status = card.querySelector('.agenda-status');
            const descendants = [kicker, title, status];
            const within = node => {
                const bounds = node.getBoundingClientRect();
                return bounds.left >= surface.left - 1 && bounds.right <= surface.right + 1
                    && bounds.top >= surface.top - 1 && bounds.bottom <= surface.bottom + 1;
            };
            const statusStyle = getComputedStyle(status);
            const cardStyle = getComputedStyle(card);
            return {
                scrollWidth: card.scrollWidth, clientWidth: card.clientWidth,
                scrollHeight: card.scrollHeight, clientHeight: card.clientHeight,
                contentInside: descendants.every(within),
                statusScrollWidth: status.scrollWidth, statusClientWidth: status.clientWidth,
                statusScrollHeight: status.scrollHeight, statusClientHeight: status.clientHeight,
                statusFits: status.scrollWidth <= status.clientWidth + 1
                    && status.scrollHeight <= status.clientHeight + 1
                    && statusStyle.boxSizing === 'border-box' && statusStyle.minWidth === '0px'
                    && statusStyle.maxWidth !== 'none' && statusStyle.overflowWrap !== 'normal',
                cardFits: card.scrollWidth <= card.clientWidth + 1
                    && card.scrollHeight <= card.clientHeight + 1
                    && cardStyle.boxSizing === 'border-box' && cardStyle.minWidth === '0px'
                    && cardStyle.maxWidth !== 'none' && cardStyle.height !== '0px',
            };
        });
        const overlaps = [], rowGaps = [], columnGaps = [], sameRowHeightDiffs = [];
        for (let first = 0; first < surfaces.length; first++) {
            for (let second = first + 1; second < surfaces.length; second++) {
                const a = surfaces[first], b = surfaces[second];
                if (a.left < b.right - 1 && b.left < a.right - 1
                    && a.top < b.bottom - 1 && b.top < a.bottom - 1) overlaps.push([first, second]);
                const sameRow = Math.abs(a.top - b.top) < 1;
                const sameColumn = Math.abs(a.left - b.left) < 1;
                if (sameRow) {
                    sameRowHeightDiffs.push(Math.abs(a.height - b.height));
                    columnGaps.push(Math.max(0, b.left - a.right, a.left - b.right));
                }
                if (sameColumn) rowGaps.push(Math.max(0, b.top - a.bottom, a.top - b.bottom));
            }
        }
        return {
            columns: getComputedStyle(grid).gridTemplateColumns.split(' ').filter(Boolean).length,
            columnGap: parseFloat(getComputedStyle(grid).columnGap),
            rowGap: parseFloat(getComputedStyle(grid).rowGap),
            domKickers: cards.map(card => card.querySelector('.dashboard-kicker').textContent.trim()),
            statuses: cards.map(card => card.querySelector('.agenda-status').textContent.trim().split(' · ').at(-1)),
            overlaps, rowGaps, columnGaps, sameRowHeightDiffs,
            surfacesFit: surfaces.every(surface => surface.scrollWidth <= surface.clientWidth + 1
                && surface.boxSizing === 'border-box' && surface.minWidth === '0px'
                && surface.maxWidth !== 'none'),
            contentFits: cardMetrics.every(card => card.contentInside && card.cardFits && card.statusFits),
            gridFits: grid.scrollWidth <= grid.clientWidth + 1,
        };
    }""")


@pytest.mark.parametrize("width", [1728, 1440, 1024, 681, 680, 391, 390, 320])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_agenda_cards_reflow_without_overlap_clipping_or_overflow(server, dark_server, width, theme):
    address = dark_server if theme == "dark" else server
    expected_columns = 3 if width > 680 else (2 if width > 390 else 1)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": 1600}, device_scale_factor=1)
        page.goto(address)
        page.get_by_text("Cómo está tu entrenamiento esta semana").wait_for()
        cards_grid = page.locator(".st-key-dashboard-agenda .agenda-grid")
        observed_statuses = set()
        for week in ("current", "previous"):
            if week == "previous":
                _select_option(page, "Semana de la agenda", "Anterior")
            expected_end = _week_interval(week)[1]
            page.locator(".st-key-dashboard-agenda [data-testid=stCaptionContainer]").last.get_by_text(
                re.compile(f"Semana de agenda: {expected_end:%d %b}"), exact=False
            ).wait_for()
            sessions = _sample_sessions(week)
            layout = _measure_agenda_grid(cards_grid)
            expected_kickers = [
                f"SESIÓN {index:02d} · {_date_label(session['date']).upper()}"
                for index, session in enumerate(sessions, start=1)
            ]
            expected_statuses = [
                "Realizado" if session["done"] else (
                    "Próxima" if session["date"] >= date.today() else "Sin actividad vinculada"
                )
                for session in sessions
            ]
            assert layout["columns"] == expected_columns, {"width": width, "theme": theme, "week": week, **layout}
            assert layout["domKickers"] == expected_kickers, {"width": width, "theme": theme, "week": week, **layout}
            assert layout["statuses"] == expected_statuses, {"width": width, "theme": theme, "week": week, **layout}
            assert not layout["overlaps"], {"width": width, "theme": theme, "week": week, **layout}
            assert layout["columnGap"] >= 6 and layout["rowGap"] >= 6, {
                "width": width, "theme": theme, "week": week, **layout
            }
            assert all(gap >= 6 for gap in layout["columnGaps"] + layout["rowGaps"]), {
                "width": width, "theme": theme, "week": week, **layout
            }
            assert all(diff <= 2 for diff in layout["sameRowHeightDiffs"]), {
                "width": width, "theme": theme, "week": week, **layout
            }
            assert layout["contentFits"] and layout["surfacesFit"] and layout["gridFits"], {
                "width": width, "theme": theme, "week": week, **layout
            }
            observed_statuses.update(layout["statuses"])
            assert "SEMANA ACTUAL" in page.locator(".st-key-dashboard-progress").inner_text()
            _assert_no_horizontal_overflow(page)

            if week == "current" and width in (1440, 1024, 681, 391, 390):
                capture_dir = Path("test-results/ui-captures/after")
                capture_dir.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(capture_dir / f"agenda-{theme}-{width}.png"), full_page=True)

        assert {"Próxima", "Realizado", "Sin actividad vinculada"} <= observed_statuses, {
            "width": width, "theme": theme, "statuses": observed_statuses
        }
        _select_option(page, "Semana de la agenda", "Siguiente")
        expected_end = _week_interval("next")[1]
        page.locator(".st-key-dashboard-agenda [data-testid=stCaptionContainer]").last.get_by_text(
            re.compile(f"Semana de agenda: {expected_end:%d %b}"), exact=False
        ).wait_for()
        assert "SEMANA ACTUAL" in page.locator(".st-key-dashboard-progress").inner_text()
        browser.close()


@pytest.mark.parametrize("viewport", [{"width": 1440, "height": 1000}, {"width": 390, "height": 844}])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_shared_control_focus_is_single_visible_and_keyboard_usable(server, dark_server, viewport, theme):
    address = dark_server if theme == "dark" else server
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport=viewport)
        page.goto(address)
        combo = page.get_by_label("Semana de la agenda")
        if viewport["width"] <= 680:
            combo.click()
            pointer_focus = combo.evaluate("""el => ({
                shadow: getComputedStyle(el.closest('[role=group]')).boxShadow,
                border: getComputedStyle(el.closest('[role=group]')).borderColor,
                outline: parseFloat(getComputedStyle(el).outlineWidth),
                focusVisible: el.matches(':focus-visible'),
                focusVisibleData: el.getAttribute('data-focus-visible'),
                groupFocusVisibleData: el.closest('[role=group]').getAttribute('data-focus-visible'),
            })""")
            assert pointer_focus["shadow"] == "none", pointer_focus
            assert pointer_focus["border"] not in ("rgb(255, 75, 75)", "rgb(255, 0, 0)"), pointer_focus
            assert float(pointer_focus["outline"]) == 0, pointer_focus
            assert pointer_focus["focusVisibleData"] is None, pointer_focus
            assert pointer_focus["groupFocusVisibleData"] is None, pointer_focus
            combo.press("Tab")
            page.keyboard.press("Shift+Tab")
        else:
            for _ in range(40):
                if combo.evaluate("el => el === document.activeElement"):
                    break
                page.keyboard.press("Tab")
            assert combo.evaluate("el => el === document.activeElement && el.matches(':focus-visible')")
            page.keyboard.press("Shift+Tab")
            assert page.evaluate("document.activeElement.matches(':focus-visible')")
            page.keyboard.press("Tab")
            assert combo.evaluate("el => el === document.activeElement && el.matches(':focus-visible')")
        assert combo.get_attribute("data-focus-visible") == "true"
        combo_style = combo.evaluate("""el => {
            const group = el.closest('[role=group]');
            const outer = getComputedStyle(group);
            const inner = getComputedStyle(el);
            return {
                boxShadow: outer.boxShadow,
                borderColor: outer.borderColor,
                outlineStyle: inner.outlineStyle,
                outlineWidth: parseFloat(inner.outlineWidth),
                outlineColor: inner.outlineColor,
                focusVisibleData: el.getAttribute('data-focus-visible'),
                focusVisible: el.matches(':focus-visible'),
            };
        }""")
        assert combo_style["boxShadow"] == "none", combo_style
        assert combo_style["borderColor"] not in ("rgb(255, 75, 75)", "rgb(255, 0, 0)"), combo_style
        assert combo_style["outlineStyle"] == "solid" and combo_style["outlineWidth"] >= 2, combo_style
        assert combo_style["focusVisible"], combo_style
        assert _contrast_ratio(combo_style["outlineColor"], _effective_background(combo)) >= 3, combo_style
        assert combo_style["focusVisibleData"] == "true", combo_style
        combo.press("ArrowDown")
        if viewport["width"] > 680:
            assert combo.evaluate("el => el.getAttribute('aria-expanded')") == "true"
            page.keyboard.press("Escape")
            assert combo.evaluate("el => el.getAttribute('aria-expanded')") == "false"
            combo.press("ArrowDown")
            combo.press("Enter")
            page.get_by_text("Semana de agenda:", exact=False).wait_for()

        if viewport["width"] <= 680:
            page.set_viewport_size({"width": 1440, "height": 1000})
        page.locator("[data-testid=stSidebar] label").filter(has_text="Coach").click()
        page.get_by_label("Your time zone").wait_for()
        page.set_viewport_size(viewport)
        timezone = page.get_by_label("Your time zone")
        timezone.focus()
        timezone.press("ArrowDown")
        assert timezone.evaluate("el => el.getAttribute('aria-expanded')") == "true"
        page.keyboard.press("Escape")
        timezone.fill("Europe/London")
        timezone.press("ArrowDown")
        timezone.press("Enter")
        assert timezone.input_value() == "Europe/London"

        date_group = page.get_by_role("group", name="Target date")
        date_group.click()
        page.get_by_role("grid").wait_for()
        page.keyboard.press("Escape")
        spinbutton = page.locator('[data-testid="stDateInput"] [role="spinbutton"]').first
        spinbutton.wait_for()
        date_value = date_group.locator('[role="spinbutton"]').evaluate_all(
            "els => els.map(el => el.getAttribute('aria-valuenow'))"
        )
        spinbutton.focus()
        date_focus = spinbutton.evaluate("""el => {
            const field = el.closest('[data-testid="stDateInputField"]');
            const wrapper = getComputedStyle(field);
            const active = getComputedStyle(el);
            return {
                boxShadow: wrapper.boxShadow,
                borderColor: wrapper.borderColor,
                outlineStyle: active.outlineStyle,
                outlineWidth: parseFloat(active.outlineWidth),
                outlineColor: active.outlineColor,
                appText: getComputedStyle(document.querySelector('.stApp')).color,
                focusVisible: el.matches(':focus-visible'),
            };
        }""")
        assert date_focus["boxShadow"] == "none", date_focus
        assert date_focus["borderColor"] not in ("rgb(255, 75, 75)", "rgb(255, 0, 0)"), date_focus
        assert date_focus["outlineStyle"] == "solid" and date_focus["outlineWidth"] >= 2, date_focus
        assert date_focus["focusVisible"], date_focus
        assert _contrast_ratio(date_focus["outlineColor"], _effective_background(spinbutton)) >= 3, date_focus
        assert date_group.locator('[role="spinbutton"]').evaluate_all(
            "els => els.map(el => el.getAttribute('aria-valuenow'))"
        ) == date_value
        assert page.locator("body").evaluate("el => el.scrollWidth <= window.innerWidth")
        browser.close()


def _contrast_ratio(foreground, background):
    def luminance(value):
        channels = [int(part) / 255 for part in re.findall(r"\d+", value)[:3]]
        linear = [channel / 12.92 if channel <= .04045 else ((channel + .055) / 1.055) ** 2.4 for channel in channels]
        return sum(channel * weight for channel, weight in zip(linear, (.2126, .7152, .0722)))

    first, second = luminance(foreground), luminance(background)
    return (max(first, second) + .05) / (min(first, second) + .05)


def _effective_background(locator):
    return locator.evaluate("""element => {
        const parseColor = value => {
            const channels = value.match(/[\\d.]+/g).map(Number);
            return [channels[0], channels[1], channels[2], value.startsWith('rgba') ? channels[3] : 1];
        };
        const layers = [];
        for (let node = element; node; node = node.parentElement) {
            layers.push(parseColor(getComputedStyle(node).backgroundColor));
        }
        let background = [0, 0, 0, 0];
        for (const layer of layers.reverse()) {
            const alpha = layer[3];
            background = [
                layer[0] * alpha + background[0] * (1 - alpha),
                layer[1] * alpha + background[1] * (1 - alpha),
                layer[2] * alpha + background[2] * (1 - alpha),
                alpha + background[3] * (1 - alpha),
            ];
        }
        if (background[3] < 0.999) {
            const canvas = parseColor(getComputedStyle(document.documentElement).backgroundColor);
            const alpha = canvas[3];
            background = [
                canvas[0] * alpha + background[0] * (1 - alpha),
                canvas[1] * alpha + background[1] * (1 - alpha),
                canvas[2] * alpha + background[2] * (1 - alpha),
                alpha + background[3] * (1 - alpha),
            ];
        }
        if (background[3] < 0.999) {
            background = [
                background[0] + 255 * (1 - background[3]),
                background[1] + 255 * (1 - background[3]),
                background[2] + 255 * (1 - background[3]),
                1,
            ];
        }
        return `rgb(${background.slice(0, 3).map(channel => Math.round(channel)).join(', ')})`;
    }""")
