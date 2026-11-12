"""Inline CCv2 bridge for the isolated Stride demonstration dashboard."""

from pathlib import Path

import streamlit as st

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


def render_stride_dashboard():
    """Mount the isolated demonstration dashboard."""
    return _STRIDE_DASHBOARD(
        data={"demo": True},
    )
