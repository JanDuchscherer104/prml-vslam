"""Packaged Streamlit entrypoint for the PRML VSLAM workbench."""

from __future__ import annotations

import streamlit as st


def run_app() -> None:
    """Render the placeholder Streamlit workbench."""
    st.set_page_config(page_title="PRML VSLAM Workbench", layout="wide")
    st.title("PRML VSLAM Workbench")
    st.caption("Workbench scaffold for the monocular VSLAM benchmark project.")
