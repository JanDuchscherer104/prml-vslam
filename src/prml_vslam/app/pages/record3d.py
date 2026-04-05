"""Pure-Streamlit Record3D page for USB and Wi-Fi live preview."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.io.record3d import (
    Record3DDevice,
    Record3DStreamSnapshot,
    Record3DStreamState,
    Record3DTransportId,
)
from prml_vslam.plotting import build_live_trajectory_figure

from ..camera_display import format_camera_intrinsics_latex
from ..image_utils import normalize_grayscale_image
from ..record3d_controller import Record3DPageAction, handle_record3d_page_action, sync_record3d_running_state
from ..record3d_view_utils import build_record3d_frame_details, record3d_stream_hint
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


def render(context: AppContext) -> None:
    """Render the dedicated Record3D page."""
    render_page_intro(
        eyebrow="Live Capture",
        title="Record3D Stream",
        body=(
            "Capture from USB or Wi-Fi, inspect RGBD frames, and monitor a live session without leaving the "
            "workbench. Stream setup stays explicit, while the preview panel refreshes independently."
        ),
    )
    handle_record3d_page_action(context, _render_sidebar_controls(context))
    _render_live_snapshot(context)


def _render_sidebar_controls(context: AppContext) -> Record3DPageAction:
    page_state = context.state.record3d
    with st.sidebar:
        st.subheader("Stream Controls")
        st.caption("Choose a source, then start or restart the active stream.")
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
                usb_devices = context.record3d_service.list_usb_devices()
            except Exception as exc:
                usb_error_message = str(exc)
        selected_usb_index = page_state.usb_device_index
        wifi_device_address = page_state.wifi_device_address
        with st.form("record3d_connection_form", border=False):
            if transport is Record3DTransportId.USB:
                selected_usb_index = _render_usb_selector(
                    current_index=page_state.usb_device_index, devices=usb_devices
                )
            else:
                wifi_device_address = st.text_input(
                    "Wi-Fi Device Address",
                    value=page_state.wifi_device_address,
                    placeholder="myiPhone.local or 192.168.1.100",
                ).strip()
            start_requested = st.form_submit_button(
                "Start stream" if not page_state.is_running else "Restart stream",
                type="primary",
                disabled=_start_disabled(
                    transport=transport, usb_devices=usb_devices, wifi_device_address=wifi_device_address
                ),
                use_container_width=True,
            )
        stop_requested = st.button("Stop stream", disabled=not page_state.is_running, use_container_width=True)
        with st.expander("Transport details", expanded=bool(usb_error_message)):
            st.write(record3d_stream_hint(transport))
            if usb_error_message:
                st.warning(usb_error_message)
            elif transport is Record3DTransportId.USB and not usb_devices:
                st.info("No USB Record3D devices are currently connected.")
    return Record3DPageAction(
        transport=transport,
        usb_device_index=selected_usb_index,
        wifi_device_address=wifi_device_address,
        start_requested=start_requested,
        stop_requested=stop_requested,
    )


def _render_live_snapshot(context: AppContext) -> None:
    @st.fragment(run_every=0.5 if context.state.record3d.is_running else None)
    def _render_fragment() -> None:
        _render_snapshot(sync_record3d_running_state(context))

    _render_fragment()


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
    st.subheader("Live Session")
    _render_status_notice(snapshot)
    metric_columns = st.columns(4, gap="small")
    metric_columns[0].metric("Status", snapshot.state.value.upper())
    metric_columns[1].metric("Received Frames", str(snapshot.received_frames))
    metric_columns[2].metric("Frame Rate", f"{snapshot.measured_fps:.2f} fps")
    metric_columns[3].metric("Transport", snapshot.transport.label if snapshot.transport is not None else "Idle")
    if snapshot.source_label:
        st.caption(f"Source: {snapshot.source_label}")
    packet = snapshot.latest_packet
    if packet is None:
        return
    preview_tab, trajectory_tab, camera_tab = st.tabs(["Frames", "Trajectory", "Camera"])
    with preview_tab:
        frame_columns = st.columns(2, gap="large")
        with frame_columns[0]:
            st.markdown("**RGB Frame**")
            st.image(packet.rgb, channels="RGB", clamp=True)
        with frame_columns[1]:
            st.markdown("**Depth Frame**")
            st.image(normalize_grayscale_image(packet.depth), clamp=True)
        st.markdown("**Uncertainty / Confidence**")
        if packet.uncertainty is None:
            st.info("Uncertainty / confidence is not available for this transport.")
        else:
            st.image(normalize_grayscale_image(packet.uncertainty), clamp=True)
    with trajectory_tab:
        if len(snapshot.trajectory_positions_xyz) == 0:
            st.info("Live ego trajectory is not available for the current transport yet.")
        else:
            st.plotly_chart(
                build_live_trajectory_figure(
                    snapshot.trajectory_positions_xyz,
                    snapshot.trajectory_timestamps_s if len(snapshot.trajectory_timestamps_s) else None,
                ),
                width="stretch",
            )
    with camera_tab:
        intrinsics_col, details_col = st.columns((1.0, 1.1), gap="large")
        with intrinsics_col:
            st.markdown("**Camera Intrinsics**")
            if packet.intrinsics is None:
                st.info("Camera intrinsics are not available for the current packet.")
            else:
                st.latex(
                    format_camera_intrinsics_latex(
                        fx=packet.intrinsics.fx,
                        fy=packet.intrinsics.fy,
                        cx=packet.intrinsics.cx,
                        cy=packet.intrinsics.cy,
                    )
                )
        with details_col:
            st.markdown("**Frame Details**")
            st.json(build_record3d_frame_details(snapshot, packet), expanded=False)


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
        Record3DStreamState.IDLE: (st.info, "Choose a source and start a stream to preview live Record3D data."),
        Record3DStreamState.CONNECTING: (st.info, "Connecting to Record3D and waiting for the first frame."),
        Record3DStreamState.STREAMING: (st.success, "Streaming live packets into the workbench."),
        Record3DStreamState.DISCONNECTED: (
            st.warning,
            "The Record3D stream disconnected before a new frame could be displayed.",
        ),
        Record3DStreamState.FAILED: (st.warning, "The stream ended unexpectedly."),
    }[snapshot.state]
    notice(message)
