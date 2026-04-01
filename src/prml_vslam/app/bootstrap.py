"""Bootstrap helpers for the PRML VSLAM metrics app."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from prml_vslam.utils.path_config import PathConfig, get_path_config

from .models import AppState
from .pages.metrics import render as render_metrics_page
from .services import MetricsAppService
from .state import SessionStateStore
from .ui import inject_styles


@dataclass(slots=True)
class AppContext:
    """Typed per-rerun context passed to page renderers."""

    path_config: PathConfig
    service: MetricsAppService
    store: SessionStateStore
    state: AppState


def build_context() -> AppContext:
    """Construct the typed services and persisted state for one rerun."""
    path_config = get_path_config()
    store = SessionStateStore()
    return AppContext(
        path_config=path_config,
        service=MetricsAppService(path_config),
        store=store,
        state=store.load(),
    )


def run_app() -> None:
    """Render the metrics-first Streamlit application."""
    st.set_page_config(
        page_title="PRML VSLAM Metrics",
        page_icon=":material/query_stats:",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_styles()
    render_metrics_page(build_context())


__all__ = ["AppContext", "build_context", "run_app"]
