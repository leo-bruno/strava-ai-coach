"""Inline CCv2 bridge for the isolated Stride demonstration dashboard."""

from collections.abc import Callable
from pathlib import Path

import streamlit as st

COMPONENT_STATE_KEY = "stride_demo_dashboard"
_ASSET_DIRECTORY = Path(__file__).parent
_HTML = (_ASSET_DIRECTORY / "stride_dashboard_assets.html").read_text(encoding="utf-8")
_CSS = (_ASSET_DIRECTORY / "stride_dashboard_assets.css").read_text(encoding="utf-8")
_JS = (_ASSET_DIRECTORY / "stride_dashboard_assets.js").read_text(encoding="utf-8")

_STRIDE_DASHBOARD = st.components.v2.component(
    "stride_dashboard_demo",
    html=_HTML,
    css=_CSS,
    js=_JS,
    isolate_styles=True,
)


def render_stride_dashboard(
    *, on_route_change: Callable[[], None] | None = None
):
    """Mount the demo UI; only its explicit app-route links emit Python events."""
    callback = on_route_change if on_route_change is not None else (lambda: None)
    return _STRIDE_DASHBOARD(
        key=COMPONENT_STATE_KEY,
        data={"demo": True},
        on_route_change=callback,
    )
