"""Pure-Streamlit Record3D page for USB and Wi-Fi live preview."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import streamlit as st

from prml_vslam.io.record3d import (
    Record3DDevice,
    Record3DIntrinsicMatrix,
    Record3DStreamSnapshot,
    Record3DStreamState,
    Record3DTransportId,
)

from ..plotting import build_live_trajectory_figure
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


_ACTIVE_STREAM_STATES = {
    Record3DStreamState.CONNECTING,
    Record3DStreamState.STREAMING,
}


def render(context: AppContext) -> None:
    """Render the dedicated Record3D page."""
    state = context.state
    runtime = context.record3d_runtime
    page_state = state.record3d

    _sync_running_state(context)
    render_page_intro(
        eyebrow="Live Capture",
        title="Record3D Stream",
        body=(
            "Capture from USB or Wi-Fi, inspect RGBD frames, and monitor a live session without leaving the "
            "workbench. Stream setup stays explicit, while the preview panel refreshes independently."
        ),
    )
    transport, selected_usb_index, wifi_device_address, start_requested, stop_requested = _render_sidebar_controls(
        context
    )

    if start_requested:
        selectors_changed = (
            selected_usb_index != page_state.usb_device_index or wifi_device_address != page_state.wifi_device_address
        )
        if selectors_changed and page_state.is_running:
            runtime.stop()
            page_state.is_running = False

        page_state.usb_device_index = selected_usb_index
        page_state.wifi_device_address = wifi_device_address

        if transport is Record3DTransportId.USB:
            runtime.start_usb(device_index=selected_usb_index)
        else:
            runtime.start_wifi(device_address=wifi_device_address)
        page_state.is_running = True
        context.store.save(state)

    if stop_requested:
        runtime.stop()
        page_state.is_running = False
        context.store.save(state)

    _render_live_snapshot(context)


def _render_sidebar_controls(
    context: AppContext,
) -> tuple[Record3DTransportId, int, str, bool, bool]:
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

        if transport != page_state.transport:
            if page_state.is_running:
                context.record3d_runtime.stop()
                page_state.is_running = False
            page_state.transport = transport
            context.store.save(context.state)

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
                    current_index=page_state.usb_device_index,
                    devices=usb_devices,
                    disabled=False,
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
                    transport=transport,
                    usb_devices=usb_devices,
                    wifi_device_address=wifi_device_address,
                ),
                use_container_width=True,
            )

        stop_requested = st.button(
            "Stop stream",
            disabled=not page_state.is_running,
            use_container_width=True,
        )

        with st.expander("Transport details", expanded=bool(usb_error_message)):
            st.write(_stream_hint(transport))
            if usb_error_message:
                st.warning(usb_error_message)
            elif transport is Record3DTransportId.USB and not usb_devices:
                st.info("No USB Record3D devices are currently connected.")

    return transport, selected_usb_index, wifi_device_address, start_requested, stop_requested


def _render_usb_selector(
    *,
    current_index: int,
    devices: list[Record3DDevice],
    disabled: bool,
) -> int:
    if not devices:
        st.selectbox(
            "USB Device",
            options=["No USB device available"],
            index=0,
            disabled=True,
        )
        return 0

    selected_index = current_index if 0 <= current_index < len(devices) else 0
    selected_device = st.selectbox(
        "USB Device",
        options=devices,
        index=selected_index,
        disabled=disabled,
        format_func=lambda item: f"{item.udid} ({item.product_id})",
    )
    return devices.index(selected_device)


def _sync_running_state(
    context: AppContext,
    snapshot: Record3DStreamSnapshot | None = None,
) -> Record3DStreamSnapshot:
    current_snapshot = context.record3d_runtime.snapshot() if snapshot is None else snapshot
    if context.state.record3d.is_running and current_snapshot.state not in _ACTIVE_STREAM_STATES:
        context.state.record3d.is_running = False
        context.store.save(context.state)
    return current_snapshot


def _render_live_snapshot(context: AppContext) -> None:
    page_state = context.state.record3d

    @st.fragment(run_every=0.5 if page_state.is_running else None)
    def _render_fragment() -> None:
        snapshot = _sync_running_state(context)
        _render_snapshot(snapshot)

    _render_fragment()


def _render_snapshot(snapshot: Record3DStreamSnapshot) -> None:
    st.subheader("Live Session")
    _render_status_notice(snapshot)
    metric_columns = st.columns(4, gap="small")
    metric_columns[0].metric("Status", snapshot.state.value.upper())
    metric_columns[1].metric("Received Frames", str(snapshot.received_frames))
    metric_columns[2].metric("Frame Rate", f"{snapshot.measured_fps:.2f} fps")
    metric_columns[3].metric(
        "Transport",
        snapshot.transport.label if snapshot.transport is not None else "Idle",
    )
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
            st.image(_normalize_grayscale(packet.depth), clamp=True)

        st.markdown("**Uncertainty / Confidence**")
        if packet.uncertainty is None:
            st.info("Uncertainty / confidence is not available for this transport.")
        else:
            st.image(_normalize_grayscale(packet.uncertainty), clamp=True)

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
            if packet.intrinsic_matrix is None:
                st.info("Camera intrinsics are not available for the current packet.")
            else:
                st.latex(_format_intrinsic_matrix(packet.intrinsic_matrix))
        with details_col:
            st.markdown("**Frame Details**")
            st.json(_frame_details(snapshot, packet), expanded=False)


def _format_intrinsic_matrix(matrix: Record3DIntrinsicMatrix) -> str:
    return (
        "K = \\begin{bmatrix}"
        f"{matrix.fx:.3f} & 0.000 & {matrix.tx:.3f} \\\\ "
        f"0.000 & {matrix.fy:.3f} & {matrix.ty:.3f} \\\\ "
        "0.000 & 0.000 & 1.000"
        "\\end{bmatrix}"
    )


# TODO: this is a general utility function that should be moved to a shared utils module.
def _normalize_grayscale(image: np.ndarray) -> np.ndarray:
    if image.size == 0:
        return np.zeros((1, 1), dtype=np.uint8)
    finite = np.asarray(image, dtype=np.float32)
    finite_mask = np.isfinite(finite)
    if not np.any(finite_mask):
        return np.zeros_like(finite, dtype=np.uint8)

    minimum = float(np.min(finite[finite_mask]))
    maximum = float(np.max(finite[finite_mask]))
    if maximum <= minimum:
        return np.zeros_like(finite, dtype=np.uint8)
    scaled = np.zeros_like(finite, dtype=np.float32)
    scaled[finite_mask] = (finite[finite_mask] - minimum) / (maximum - minimum)
    return np.clip(scaled * 255.0, 0.0, 255.0).astype(np.uint8)


def _start_disabled(
    *,
    transport: Record3DTransportId,
    usb_devices: list[Record3DDevice],
    wifi_device_address: str,
) -> bool:
    match transport:
        case Record3DTransportId.USB:
            return not usb_devices
        case Record3DTransportId.WIFI:
            return wifi_device_address == ""


def _stream_hint(transport: Record3DTransportId) -> str:
    match transport:
        case Record3DTransportId.USB:
            return (
                "USB capture uses the native `record3d` Python bindings and can expose RGB, depth, "
                "intrinsics, and confidence."
            )
        case Record3DTransportId.WIFI:
            return (
                "Wi-Fi capture uses a Python-side WebRTC receiver. Enter the Record3D device address shown "
                "in the iPhone app."
            )


def _render_status_notice(snapshot: Record3DStreamSnapshot) -> None:
    if snapshot.error_message:
        st.error(snapshot.error_message)
        return

    match snapshot.state:
        case Record3DStreamState.IDLE:
            st.info("Choose a source and start a stream to preview live Record3D data.")
        case Record3DStreamState.CONNECTING:
            st.info("Connecting to Record3D and waiting for the first frame.")
        case Record3DStreamState.STREAMING:
            st.success("Streaming live packets into the workbench.")
        case Record3DStreamState.DISCONNECTED:
            st.warning("The Record3D stream disconnected before a new frame could be displayed.")
        case Record3DStreamState.FAILED:
            st.warning("The stream ended unexpectedly.")


def _frame_details(snapshot: Record3DStreamSnapshot, packet) -> dict[str, object]:
    details: dict[str, object] = {
        "arrival_timestamp_s": round(packet.arrival_timestamp_s, 3),
    }
    if snapshot.source_label:
        details["source"] = snapshot.source_label
    if "original_size" in packet.metadata:
        details["original_size"] = packet.metadata["original_size"]
    if packet.metadata:
        details["metadata"] = packet.metadata
    return details
