"""Pure-Streamlit Record3D page for USB and Wi-Fi live preview."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.interfaces import FramePacket
from prml_vslam.io.record3d import (
    Record3DDevice,
    Record3DTransportId,
    build_record3d_frame_details,
    list_record3d_usb_devices,
)
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
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


def render(context: AppContext) -> None:
    """Render the dedicated Record3D page."""
    render_page_intro(
        eyebrow="Live Capture",
        title="Record3D Stream",
        body=(
            "Capture from the official USB bindings or use the optional Wi-Fi preview fallback, inspect RGBD "
            "frames, and monitor a live session without leaving the workbench. USB remains the canonical "
            "programmatic path, while the preview panel refreshes independently."
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
        st.caption("Choose a source, then start or restart the active stream. USB is the recommended capture path.")
        selected_transport = st.segmented_control(
            "Transport",
            options=list(Record3DTransportId),
            default=page_state.transport,
            format_func=lambda item: item.label,
            selection_mode="single",
            key="record3d_transport_selector",
            width="stretch",
        )
        transport = selected_transport or page_state.transport
        usb_devices: list[Record3DDevice] = []
        usb_error_message = ""
        if transport is Record3DTransportId.USB:
            try:
                usb_devices = list_record3d_usb_devices()
            except Exception as exc:
                usb_error_message = str(exc)
        selected_usb_index = page_state.usb_device_index
        wifi_device_address = page_state.wifi_device_address
        if transport is Record3DTransportId.USB:
            selected_usb_index = _render_usb_selector(current_index=page_state.usb_device_index, devices=usb_devices)
        else:
            wifi_device_address = st.text_input(
                "Wi-Fi Preview Device Address",
                value=page_state.wifi_device_address,
                placeholder="myiPhone.local or 192.168.1.100",
            ).strip()
        start_requested, stop_requested = render_live_action_slot(
            is_active=page_state.is_running,
            start_label="Start stream",
            stop_label="Stop stream",
            start_disabled=_start_disabled(
                transport=transport,
                usb_devices=usb_devices,
                wifi_device_address=wifi_device_address,
            ),
        )
        with st.expander("Transport details", expanded=bool(usb_error_message)):
            st.write(transport.stream_hint())
            if usb_error_message:
                st.warning(usb_error_message)
            elif transport is Record3DTransportId.USB and not usb_devices:
                st.info("No USB Record3D devices are currently connected.")
            elif transport is Record3DTransportId.WIFI:
                st.info("Wi-Fi Preview is optional and lower fidelity than the official USB integration.")
    return Record3DPageAction(
        transport=transport,
        usb_device_index=selected_usb_index,
        wifi_device_address=wifi_device_address,
        start_requested=start_requested,
        stop_requested=stop_requested,
    )


def _render_live_snapshot(context: AppContext) -> None:
    render_live_fragment(
        run_every=live_poll_interval(is_active=context.state.record3d.is_running, interval_seconds=0.5),
        render_body=lambda: _render_snapshot(sync_record3d_running_state(context)),
    )


def _render_usb_selector(*, current_index: int, devices: list[Record3DDevice]) -> int:
    if not devices:
        st.selectbox("USB Device", options=["No USB device available"], index=0, disabled=True)
        return 0
    selected_index = current_index if 0 <= current_index < len(devices) else 0
    selected_device = st.selectbox(
        "USB Device",
        options=devices,
        index=selected_index,
        format_func=lambda item: f"{item.udid} ({item.product_id})",
    )
    return devices.index(selected_device)


def _render_snapshot(snapshot: Record3DStreamSnapshot) -> None:
    render_live_session_shell(
        title="Live Session",
        status_renderer=lambda: _render_status_notice(snapshot),
        metrics=_snapshot_metrics(snapshot),
        caption=None if not snapshot.source_label else f"Source: {snapshot.source_label}",
        body_renderer=lambda: render_live_packet_tabs(
            packet=snapshot.latest_packet,
            preview_renderer=_render_frame_preview,
            positions_xyz=snapshot.trajectory_positions_xyz,
            timestamps_s=snapshot.trajectory_timestamps_s if len(snapshot.trajectory_timestamps_s) else None,
            trajectory_empty_message="Live ego trajectory is not available for the current transport yet.",
            details_payload={}
            if snapshot.latest_packet is None
            else build_record3d_frame_details(snapshot.latest_packet, source_label=snapshot.source_label),
            intrinsics_missing_message="Camera intrinsics are not available for the current packet.",
        ),
    )


def _snapshot_metrics(snapshot: Record3DStreamSnapshot) -> tuple[LiveMetric, ...]:
    return (
        ("Status", snapshot.state.value.upper()),
        ("Received Frames", str(snapshot.received_frames)),
        ("Frame Rate", f"{snapshot.measured_fps:.2f} fps"),
        ("Transport", snapshot.transport.label if snapshot.transport is not None else "Idle"),
    )


def _render_frame_preview(packet: FramePacket) -> None:
    frame_columns = st.columns(2, gap="large")
    with frame_columns[0]:
        st.markdown("**RGB Frame**")
        st.image(packet.rgb, channels="RGB", clamp=True)
    with frame_columns[1]:
        st.markdown("**Depth Frame**")
        st.image(normalize_grayscale_image(packet.depth), clamp=True)
    st.markdown("**Depth Confidence**")
    if packet.confidence is None:
        st.info("Depth confidence is not available for this transport.")
    else:
        st.image(normalize_grayscale_image(packet.confidence), clamp=True)


def _start_disabled(
    *,
    transport: Record3DTransportId,
    usb_devices: list[Record3DDevice],
    wifi_device_address: str,
) -> bool:
    return (transport is Record3DTransportId.USB and not usb_devices) or (
        transport is Record3DTransportId.WIFI and wifi_device_address == ""
    )


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
