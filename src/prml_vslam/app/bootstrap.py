"""Bootstrap helpers for the packaged PRML VSLAM Streamlit app."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from prml_vslam.utils.path_config import PathConfig, get_path_config

from .models import AppPageId, AppState
from .pages.metrics import render as render_metrics_page
from .pages.record3d import render as render_record3d_page
from .services import MetricsAppService, Record3DAppService, Record3DStreamRuntimeController
from .state import SessionStateStore
from .ui import inject_styles


@dataclass(slots=True)
class AppContext:
    """Typed per-rerun context passed to page renderers."""

    path_config: PathConfig
    metrics_service: MetricsAppService
    record3d_service: Record3DAppService
    record3d_runtime: Record3DStreamRuntimeController
    store: SessionStateStore
    state: AppState


def build_context() -> AppContext:
    """Construct the typed services and persisted state for one rerun."""
    path_config = get_path_config()
    store = SessionStateStore()
    return AppContext(
        path_config=path_config,
        metrics_service=MetricsAppService(path_config),
        record3d_service=Record3DAppService(),
        record3d_runtime=store.load_record3d_runtime(),
        store=store,
        state=store.load(),
    )


def run_app() -> None:
    """Render the packaged Streamlit application."""
    st.set_page_config(
        page_title="PRML VSLAM Workbench",
        page_icon=":material/videocam:",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_styles()
    context = build_context()
    _render_top_level_navigation(context)

    match context.state.current_page:
        case AppPageId.RECORD3D:
            render_record3d_page(context)
        case AppPageId.METRICS:
            render_metrics_page(context)


def _render_top_level_navigation(context: AppContext) -> None:
    selected_page = st.segmented_control(
        "Page",
        options=list(AppPageId),
        default=context.state.current_page,
        format_func=lambda item: item.label,
        width="stretch",
    )
    if selected_page is None:
        selected_page = context.state.current_page

    previous_page = context.state.current_page
    if previous_page is AppPageId.RECORD3D and selected_page is not AppPageId.RECORD3D:
        context.record3d_runtime.stop()
        context.state.record3d.is_running = False

    context.state.current_page = selected_page
    context.store.save(context.state)


__all__ = ["AppContext", "build_context", "run_app"]
