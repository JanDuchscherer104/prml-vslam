"""UI helpers for the packaged Streamlit workbench."""

from __future__ import annotations

import streamlit as st


def render_page_intro(*, eyebrow: str, title: str, body: str) -> None:
    """Render a lightweight, theme-native page header."""
    st.caption(eyebrow)
    st.title(title)
    st.write(body)


__all__ = ["render_page_intro"]
