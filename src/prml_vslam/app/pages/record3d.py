"""Pure-Streamlit Record3D page for USB and Wi-Fi live preview."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.interfaces import Observation
from prml_vslam.sources.record3d.record3d import build_record3d_frame_details
from prml_vslam.utils.image_utils import normalize_grayscale_image

from ..live_session import (
    LiveMetric,
    live_poll_interval,
    render_live_action_slot,
    render_live_fragment,
    render_live_packet_tabs,
    render_live_session_shell,
    rerun_after_action,
)
from ..models import PreviewStreamState, Record3DStreamSnapshot
from ..record3d_controller import Record3DPageAction, handle_record3d_page_action, sync_record3d_running_state
from ..record3d_controls import render_record3d_transport_controls, render_record3d_transport_details
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


def render(context: AppContext) -> None:
    """Render the dedicated Record3D page."""
    render_page_intro(
        eyebrow="Live Capture",
        title="Record3D Stream",
        body=(
            "Capture from the official USB bindings or the Wi-Fi transport, inspect RGBD frames, and monitor a "
            "live session without leaving the workbench."
        ),
    )
    action = _render_sidebar_controls(context)
    handle_record3d_page_action(context, action)
    if rerun_after_action(action_requested=action.start_requested or action.stop_requested):
        return
    _render_live_snapshot(context)


def _render_sidebar_controls(context: AppContext) -> Record3DPageAction:
    page_state = context.state.record3d
    with st.sidebar:
        st.subheader("Stream Controls")
        st.caption("Choose a source, then start or restart the active stream.")
        selection = render_record3d_transport_controls(
            transport=page_state.transport,
            usb_device_index=page_state.usb_device_index,
            wifi_device_address=page_state.wifi_device_address,
            widget_key_prefix="record3d",
        )
        start_requested, stop_requested = render_live_action_slot(
            is_active=page_state.is_running,
            start_label="Start stream",
            stop_label="Stop stream",
            start_disabled=selection.input_error is not None,
        )
        render_record3d_transport_details(selection)
    return Record3DPageAction(
        transport=selection.transport,
        usb_device_index=selection.usb_device_index,
        wifi_device_address=selection.wifi_device_address,
        start_requested=start_requested,
        stop_requested=stop_requested,
    )


def _render_live_snapshot(context: AppContext) -> None:
    render_live_fragment(
        run_every=live_poll_interval(is_active=context.state.record3d.is_running, interval_seconds=0.5),
        render_body=lambda: _render_snapshot(sync_record3d_running_state(context)),
    )


def _render_snapshot(snapshot: Record3DStreamSnapshot) -> None:
    render_live_session_shell(
        title="Live Session",
        status_renderer=lambda: _render_status_notice(snapshot),
        metrics=_snapshot_metrics(snapshot),
        caption=None if not snapshot.source_label else f"Source: {snapshot.source_label}",
        body_renderer=lambda: render_live_packet_tabs(
            packet=snapshot.preview_packet,
            preview_renderer=_render_frame_preview,
            positions_xyz=snapshot.preview_trajectory_xyz,
            timestamps_s=snapshot.preview_trajectory_time_s if len(snapshot.preview_trajectory_time_s) else None,
            trajectory_empty_message="Live ego trajectory is not available for the current transport yet.",
            details_payload={}
            if snapshot.preview_packet is None
            else build_record3d_frame_details(snapshot.preview_packet, source_label=snapshot.source_label),
            intrinsics_missing_message="Camera intrinsics are not available for the current packet.",
        ),
    )


def _snapshot_metrics(snapshot: Record3DStreamSnapshot) -> tuple[LiveMetric, ...]:
    return (
        ("Status", snapshot.state.value.upper()),
        ("Received Frames", str(snapshot.preview_frame_count)),
        ("Frame Rate", f"{snapshot.measured_fps:.2f} fps"),
        ("Transport", snapshot.transport.label if snapshot.transport is not None else "Idle"),
    )


def _render_frame_preview(packet: Observation) -> None:
    frame_columns = st.columns(2, gap="large")
    with frame_columns[0]:
        st.markdown("**RGB Frame**")
        st.image(packet.rgb, channels="RGB", clamp=True)
    with frame_columns[1]:
        st.markdown("**Depth Frame**")
        if packet.depth_m is None:
            st.info("Depth is not available for this transport.")
        else:
            st.image(normalize_grayscale_image(packet.depth_m), clamp=True)
    st.markdown("**Depth Confidence**")
    if packet.confidence is None:
        st.info("Depth confidence is not available for this transport.")
    else:
        st.image(normalize_grayscale_image(packet.confidence), clamp=True)


def _render_status_notice(snapshot: Record3DStreamSnapshot) -> None:
    if snapshot.error_message:
        st.error(snapshot.error_message)
        return
    notice, message = {
        PreviewStreamState.IDLE: (st.info, "Choose a source and start a stream to preview live Record3D data."),
        PreviewStreamState.CONNECTING: (st.info, "Connecting to Record3D and waiting for the first frame."),
        PreviewStreamState.STREAMING: (st.success, "Streaming live packets into the workbench."),
        PreviewStreamState.DISCONNECTED: (
            st.warning,
            "The Record3D stream disconnected before a new frame could be displayed.",
        ),
        PreviewStreamState.FAILED: (st.warning, "The stream ended unexpectedly."),
    }[snapshot.state]
    notice(message)
