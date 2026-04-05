"""Shared Streamlit helpers for live-session app pages."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeAlias

import numpy as np
import streamlit as st

from prml_vslam.interfaces import CameraIntrinsics, FramePacket

from .camera_display import format_camera_intrinsics_latex

LiveMetric: TypeAlias = tuple[str, str]


def _build_live_trajectory_figure(
    positions_xyz: np.ndarray,
    timestamps_s: np.ndarray | None,
) -> object:
    """Resolve the live trajectory figure builder lazily for easier local testing."""
    from prml_vslam.plotting.record3d import build_live_trajectory_figure

    return build_live_trajectory_figure(positions_xyz, timestamps_s)


def render_live_fragment(*, run_every: float | None, render_body: Callable[[], None]) -> None:
    """Render one fragment-scoped live section."""

    @st.fragment(run_every=run_every)
    def _render_fragment() -> None:
        render_body()

    _render_fragment()


def render_live_session_shell(
    *,
    title: str | None,
    status_renderer: Callable[[], None],
    metrics: Sequence[LiveMetric],
    caption: str | None = None,
    body_renderer: Callable[[], None] | None = None,
) -> None:
    """Render the shared notice, metric, and body structure for one live section."""
    if title is not None:
        st.subheader(title)
    status_renderer()
    render_metric_row(metrics)
    if caption:
        st.caption(caption)
    if body_renderer is not None:
        body_renderer()


def render_metric_row(metrics: Sequence[LiveMetric]) -> None:
    """Render a compact metric row."""
    for column, (label, value) in zip(st.columns(len(metrics), gap="small"), metrics, strict=True):
        column.metric(label, value)


def render_live_trajectory(
    *,
    positions_xyz: np.ndarray,
    timestamps_s: np.ndarray | None,
    empty_message: str,
) -> None:
    """Render a live trajectory figure or a fallback message."""
    if len(positions_xyz) == 0:
        st.info(empty_message)
        return
    st.plotly_chart(_build_live_trajectory_figure(positions_xyz, timestamps_s), width="stretch")


def render_camera_intrinsics(
    *,
    intrinsics: CameraIntrinsics | None,
    missing_message: str,
) -> None:
    """Render camera intrinsics using the shared LaTeX presentation."""
    if intrinsics is None:
        st.info(missing_message)
        return
    st.latex(
        format_camera_intrinsics_latex(
            fx=intrinsics.fx,
            fy=intrinsics.fy,
            cx=intrinsics.cx,
            cy=intrinsics.cy,
        )
    )


def render_live_packet_tabs(
    *,
    packet: FramePacket | None,
    preview_renderer: Callable[[FramePacket], None],
    positions_xyz: np.ndarray,
    timestamps_s: np.ndarray | None,
    trajectory_empty_message: str,
    details_payload: dict[str, object],
    intrinsics_missing_message: str,
    details_title: str = "Frame Details",
) -> None:
    """Render the shared packet, trajectory, and camera tabs for live pages."""
    if packet is None:
        return
    preview_tab, trajectory_tab, camera_tab = st.tabs(["Frames", "Trajectory", "Camera"])
    with preview_tab:
        preview_renderer(packet)
    with trajectory_tab:
        render_live_trajectory(
            positions_xyz=positions_xyz,
            timestamps_s=timestamps_s,
            empty_message=trajectory_empty_message,
        )
    with camera_tab:
        left, right = st.columns((0.9, 1.1), gap="large")
        with left:
            st.markdown("**Camera Intrinsics**")
            render_camera_intrinsics(
                intrinsics=packet.intrinsics,
                missing_message=intrinsics_missing_message,
            )
        with right:
            st.markdown(f"**{details_title}**")
            st.json(details_payload, expanded=False)


__all__ = [
    "LiveMetric",
    "render_camera_intrinsics",
    "render_live_fragment",
    "render_live_packet_tabs",
    "render_live_session_shell",
    "render_live_trajectory",
    "render_metric_row",
]
