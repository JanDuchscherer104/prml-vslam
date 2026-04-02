"""Bootstrap helpers for the packaged PRML VSLAM Streamlit app."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial

import streamlit as st

from prml_vslam.datasets import AdvioDatasetService
from prml_vslam.eval import TrajectoryEvaluationService
from prml_vslam.utils.path_config import PathConfig, get_path_config

from .models import AppPageId, AppState
from .pages.advio import render as render_advio_page
from .pages.metrics import render as render_metrics_page
from .pages.record3d import render as render_record3d_page
from .services import Record3DAppService, Record3DStreamRuntimeController
from .state import SessionStateStore
from .ui import inject_styles


@dataclass(slots=True)
class AppContext:
    """Typed per-rerun context passed to page renderers."""

    path_config: PathConfig
    advio_service: AdvioDatasetService
    evaluation_service: TrajectoryEvaluationService
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
        advio_service=AdvioDatasetService(path_config),
        evaluation_service=TrajectoryEvaluationService(path_config),
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
        initial_sidebar_state="expanded",
    )
    inject_styles()
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
            partial(_render_record3d_page_entry, context),
            title=AppPageId.RECORD3D.label,
            icon=":material/videocam:",
            url_path=AppPageId.RECORD3D.value,
            default=True,
        ),
        st.Page(
            partial(_render_advio_page_entry, context),
            title=AppPageId.ADVIO.label,
            icon=":material/download:",
            url_path=AppPageId.ADVIO.value,
            default=False,
        ),
        st.Page(
            partial(_render_metrics_page_entry, context),
            title=AppPageId.METRICS.label,
            icon=":material/show_chart:",
            url_path=AppPageId.METRICS.value,
            default=False,
        ),
    ]


def _render_record3d_page_entry(context: AppContext) -> None:
    _enter_page(context, AppPageId.RECORD3D)
    render_record3d_page(context)


def _render_metrics_page_entry(context: AppContext) -> None:
    _enter_page(context, AppPageId.METRICS)
    render_metrics_page(context)


def _render_advio_page_entry(context: AppContext) -> None:
    _enter_page(context, AppPageId.ADVIO)
    render_advio_page(context)


def _enter_page(context: AppContext, page_id: AppPageId) -> None:
    if page_id is not AppPageId.RECORD3D and context.state.record3d.is_running:
        context.record3d_runtime.stop()
        context.state.record3d.is_running = False
        context.store.save(context.state)


__all__ = ["AppContext", "build_context", "run_app"]
