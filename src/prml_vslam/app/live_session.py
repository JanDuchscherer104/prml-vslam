"""Shared Streamlit helpers for live-session app pages."""

from __future__ import annotations

import base64
from collections.abc import Callable, Sequence
from typing import Literal, TypeAlias

import cv2
import numpy as np
import streamlit as st

from prml_vslam.interfaces import CameraIntrinsics, FramePacket

LiveMetric: TypeAlias = tuple[str, str]
ImageWidth: TypeAlias = int | Literal["content", "stretch"]

_LIVE_IMAGE_MAX_WIDTH_PX = 730
_LIVE_IMAGE_JPEG_QUALITY = 90


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


def live_image_data_url(
    image: np.ndarray,
    *,
    channels: Literal["RGB", "BGR"] = "RGB",
    clamp: bool = True,
) -> str:
    """Encode one live preview image as a data URL.

    Streamlit stores array-backed ``st.image`` payloads in its in-memory media manager.
    High-frequency live previews can then leave the browser requesting an old
    ``/media/<hash>.jpg`` URL after Streamlit has already pruned it. Data URLs keep
    live preview frames out of that manager while preserving normal ``st.image``
    rendering.
    """
    display_image = _prepare_live_image_array(image, channels=channels, clamp=clamp)
    extension = ".png" if display_image.ndim == 3 and display_image.shape[-1] == 4 else ".jpg"
    mime_type = "image/png" if extension == ".png" else "image/jpeg"
    encode_params = [] if extension == ".png" else [int(cv2.IMWRITE_JPEG_QUALITY), _LIVE_IMAGE_JPEG_QUALITY]
    ok, encoded = cv2.imencode(extension, display_image, encode_params)
    if not ok:
        raise RuntimeError("Failed to encode live preview image.")
    encoded_base64 = base64.b64encode(encoded.tobytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded_base64}"


def render_live_image(
    image: np.ndarray,
    *,
    channels: Literal["RGB", "BGR"] = "RGB",
    clamp: bool = True,
    width: ImageWidth = "stretch",
) -> None:
    """Render one high-churn live image without using Streamlit's media endpoint."""
    st.image(live_image_data_url(image, channels=channels, clamp=clamp), width=width)


def _prepare_live_image_array(
    image: np.ndarray,
    *,
    channels: Literal["RGB", "BGR"],
    clamp: bool,
) -> np.ndarray:
    array = np.asarray(image)
    if array.ndim == 3 and array.shape[-1] == 1:
        array = array[..., 0]
    if array.ndim == 2:
        display_image = _to_uint8_image(array, clamp=clamp)
    elif array.ndim == 3 and array.shape[-1] in {3, 4}:
        display_image = _to_uint8_image(array, clamp=clamp)
    else:
        raise ValueError("Live preview images must have shape HxW, HxWx1, HxWx3, or HxWx4.")

    if display_image.shape[1] > _LIVE_IMAGE_MAX_WIDTH_PX:
        height_px = max(1, round(display_image.shape[0] * _LIVE_IMAGE_MAX_WIDTH_PX / display_image.shape[1]))
        display_image = cv2.resize(
            display_image,
            (_LIVE_IMAGE_MAX_WIDTH_PX, height_px),
            interpolation=cv2.INTER_AREA,
        )

    if display_image.ndim == 2:
        return display_image
    if display_image.shape[-1] == 4:
        return display_image[..., [2, 1, 0, 3]] if channels == "RGB" else display_image
    return display_image[..., ::-1] if channels == "RGB" else display_image


def _to_uint8_image(image: np.ndarray, *, clamp: bool) -> np.ndarray:
    if np.issubdtype(image.dtype, np.floating):
        if not np.isfinite(image).all():
            raise ValueError("Live preview images must contain finite values.")
        if clamp:
            image = np.clip(image, 0.0, 1.0)
        elif np.amin(image) < 0.0 or np.amax(image) > 1.0:
            raise ValueError("Live preview float images must be in [0.0, 1.0] unless clamp is enabled.")
        return np.asarray(image * 255.0, dtype=np.uint8)
    if clamp:
        image = np.clip(image, 0, 255)
    elif np.amin(image) < 0 or np.amax(image) > 255:
        raise ValueError("Live preview integer images must be in [0, 255] unless clamp is enabled.")
    return np.asarray(image, dtype=np.uint8)


def live_poll_interval(*, is_active: bool, interval_seconds: float) -> float | None:
    """Return the fragment refresh interval only while the session is active."""
    return interval_seconds if is_active else None


def render_live_action_slot(
    *,
    is_active: bool,
    start_label: str,
    stop_label: str,
    start_disabled: bool = False,
    use_container_width: bool = True,
) -> tuple[bool, bool]:
    """Render one explicit start-or-stop button slot and return the requested action flags."""
    if is_active:
        return False, st.button(stop_label, use_container_width=use_container_width)
    return (
        st.button(
            start_label,
            type="primary",
            disabled=start_disabled,
            use_container_width=use_container_width,
        ),
        False,
    )


def rerun_after_action(*, action_requested: bool, error_message: str | None = None) -> bool:
    """Trigger an immediate full-page rerun after a successful explicit action."""
    if error_message is not None or not action_requested:
        return False
    st.rerun()
    return True


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
    st.latex(intrinsics.to_latex())


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
    "live_poll_interval",
    "render_camera_intrinsics",
    "render_live_action_slot",
    "render_live_fragment",
    "render_live_image",
    "render_live_packet_tabs",
    "render_live_session_shell",
    "render_live_trajectory",
    "render_metric_row",
    "rerun_after_action",
    "live_image_data_url",
]
