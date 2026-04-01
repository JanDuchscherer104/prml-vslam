"""Bootstrap helpers for the PRML VSLAM Streamlit app."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from prml_vslam.path_config import PathConfig

from .models import AppState
from .pages.dataset import render as render_dataset_page_impl
from .pages.metrics import render as render_metrics_page_impl
from .pages.record3d import render as render_record3d_page_impl
from .services import EvaluationService, Record3DService
from .state import SessionStateStore
from .ui import inject_styles


@dataclass(slots=True)
class AppServices:
    """Shared typed services for the Streamlit app."""

    path_config: PathConfig
    evaluation: EvaluationService
    record3d: Record3DService


@dataclass(slots=True)
class AppContext:
    """Per-rerun app context passed into page renderers."""

    services: AppServices
    store: SessionStateStore
    state: AppState


def get_services() -> AppServices:
    """Build the shared service bundle for the current Streamlit process."""
    path_config = PathConfig.load()
    return AppServices(
        path_config=path_config,
        evaluation=EvaluationService(path_config),
        record3d=Record3DService(),
    )


def _build_context() -> AppContext:
    services = get_services()
    store = SessionStateStore()
    state = store.load()
    return AppContext(services=services, store=store, state=state)


def run_app() -> None:
    """Render the full Streamlit application with native page navigation."""
    st.set_page_config(
        page_title="PRML VSLAM Metrics",
        page_icon=":material/query_stats:",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_styles()
    context = _build_context()

    def render_metrics_navigation_page() -> None:
        render_metrics_page_impl(context)

    def render_dataset_navigation_page() -> None:
        render_dataset_page_impl(context)

    def render_record3d_navigation_page() -> None:
        render_record3d_page_impl(context)

    navigation = st.navigation(
        [
            st.Page(
                render_metrics_navigation_page,
                title="Trajectory Metrics",
                icon=":material/query_stats:",
                url_path="trajectory-metrics",
                default=True,
            ),
            st.Page(
                render_dataset_navigation_page,
                title="Dataset Explorer",
                icon=":material/database:",
                url_path="dataset-explorer",
            ),
            st.Page(
                render_record3d_navigation_page,
                title="Record3D Streaming",
                icon=":material/videocam:",
                url_path="record3d-streaming",
            ),
        ],
        position="top",
    )
    navigation.run()


def run_metrics_page() -> None:
    """Render the metrics page directly."""
    inject_styles()
    context = _build_context()
    render_metrics_page_impl(context)


def run_dataset_page() -> None:
    """Render the dataset explorer page directly."""
    inject_styles()
    context = _build_context()
    render_dataset_page_impl(context)


def run_record3d_page() -> None:
    """Render the Record3D streaming page directly."""
    inject_styles()
    context = _build_context()
    render_record3d_page_impl(context)


__all__ = [
    "AppContext",
    "AppServices",
    "get_services",
    "run_app",
    "run_dataset_page",
    "run_metrics_page",
    "run_record3d_page",
]
