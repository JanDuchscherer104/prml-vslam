"""Bootstrap helpers for the packaged PRML VSLAM Streamlit app."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

import streamlit as st

from prml_vslam.datasets.advio import AdvioDatasetService
from prml_vslam.eval import TrajectoryEvaluationService
from prml_vslam.pipeline.run_service import RunService
from prml_vslam.pipeline.session import PipelineSessionState
from prml_vslam.utils.path_config import PathConfig, get_path_config

from .models import AppPageId, AppState
from .pages import render_advio_page, render_metrics_page, render_pipeline_page, render_record3d_page
from .services import AdvioPreviewRuntimeController, Record3DStreamRuntimeController
from .state import SessionStateStore


@dataclass(slots=True)
class AppContext:
    """Typed per-rerun context passed to page renderers."""

    path_config: PathConfig
    advio_service: AdvioDatasetService
    evaluation_service: TrajectoryEvaluationService
    record3d_runtime: Record3DStreamRuntimeController
    advio_runtime: AdvioPreviewRuntimeController
    run_service: RunService
    store: SessionStateStore
    state: AppState


_PAGE_SPECS = (
    (AppPageId.RECORD3D, ":material/videocam:", render_record3d_page, True),
    (AppPageId.ADVIO, ":material/download:", render_advio_page, False),
    (AppPageId.PIPELINE, ":material/account_tree:", render_pipeline_page, False),
    (AppPageId.METRICS, ":material/show_chart:", render_metrics_page, False),
)


def build_context() -> AppContext:
    """Construct the typed services and persisted state for one rerun."""
    path_config = get_path_config()
    store = SessionStateStore()
    return AppContext(
        path_config=path_config,
        advio_service=AdvioDatasetService(path_config),
        evaluation_service=TrajectoryEvaluationService(path_config),
        record3d_runtime=store.load_record3d_runtime(),
        advio_runtime=store.load_advio_runtime(),
        run_service=store.load_run_service(path_config=path_config),
        store=store,
        state=store.load(),
    )


def run_app() -> None:
    """Render the packaged Streamlit application."""
    st.set_page_config(
        page_title="PRML VSLAM Workbench",
        page_icon=":material/videocam:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    context = build_context()
    _render_sidebar_brand()
    page = st.navigation(_build_pages(context), position="sidebar", expanded=True)
    page.run()


def _render_sidebar_brand() -> None:
    with st.sidebar:
        st.caption("PRML VSLAM")
        st.markdown("###### Workbench")
        st.divider()


def _build_pages(context: AppContext) -> list[st.Page]:
    return [
        st.Page(
            partial(_render_page_entry, context, page_id, render_page),
            title=page_id.label,
            icon=icon,
            url_path=page_id.value,
            default=default,
        )
        for page_id, icon, render_page, default in _PAGE_SPECS
    ]


def _render_page_entry(
    context: AppContext,
    page_id: AppPageId,
    render_page: Callable[[AppContext], None],
) -> None:
    _enter_page(context, page_id)
    render_page(context)


def _enter_page(context: AppContext, page_id: AppPageId) -> None:
    state_changed = False
    for active_page_id, runtime, page_state, field_name in (
        (AppPageId.RECORD3D, context.record3d_runtime, context.state.record3d, "is_running"),
        (AppPageId.ADVIO, context.advio_runtime, context.state.advio, "preview_is_running"),
    ):
        if page_id is active_page_id or not getattr(page_state, field_name):
            continue
        runtime.stop()
        setattr(page_state, field_name, False)
        state_changed = True
    if state_changed:
        context.store.save(context.state)
    if page_id not in {AppPageId.PIPELINE, AppPageId.METRICS} and context.run_service.snapshot().state in {
        PipelineSessionState.CONNECTING,
        PipelineSessionState.RUNNING,
    }:
        context.run_service.stop_run()


__all__ = ["AppContext", "build_context", "run_app"]
