"""UI helpers for the packaged Streamlit workbench."""

from __future__ import annotations

import streamlit as st


def inject_styles() -> None:
    """Keep the hook in place without overriding Streamlit's theme system."""
    return None


def render_page_intro(*, eyebrow: str, title: str, body: str) -> None:
    """Render a lightweight, theme-native page header."""
    st.caption(eyebrow)
    st.title(title)
    st.write(body)


__all__ = ["inject_styles", "render_page_intro"]
