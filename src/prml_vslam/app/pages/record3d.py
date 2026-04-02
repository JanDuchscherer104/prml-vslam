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

if TYPE_CHECKING:
    from ..bootstrap import AppContext


def render(context: AppContext) -> None:
    """Render the dedicated Record3D page."""
    state = context.state
    runtime = context.record3d_runtime
    page_state = state.record3d

    _sync_running_flag(context)

    with st.container(border=True):
        st.caption("Record3D")
        st.title("Record3D Stream")
        st.caption(
            "Preview live USB or Wi-Fi Record3D packets directly in Streamlit. "
            "The IO layer owns capture and decoding; the app only starts, stops, and renders snapshots."
        )

    transport = st.segmented_control(
        "Transport",
        options=list(Record3DTransportId),
        default=page_state.transport,
        format_func=lambda item: item.label,
        width="stretch",
    )
    if transport is None:
        transport = page_state.transport

    usb_devices: list[Record3DDevice] = []
    usb_error_message = ""
    if transport is Record3DTransportId.USB:
        try:
            usb_devices = context.record3d_service.list_usb_devices()
        except Exception as exc:
            usb_error_message = str(exc)

    selected_usb_index = _render_usb_selector(
        current_index=page_state.usb_device_index,
        devices=usb_devices,
        disabled=transport is not Record3DTransportId.USB,
    )
    wifi_device_address = st.text_input(
        "Wi-Fi Device Address",
        value=page_state.wifi_device_address,
        disabled=transport is not Record3DTransportId.WIFI,
        placeholder="myiPhone.local or 192.168.1.100",
    ).strip()

    selectors_changed = (
        transport != page_state.transport
        or selected_usb_index != page_state.usb_device_index
        or wifi_device_address != page_state.wifi_device_address
    )
    if selectors_changed and page_state.is_running:
        runtime.stop()
        page_state.is_running = False

    page_state.transport = transport
    page_state.usb_device_index = selected_usb_index
    page_state.wifi_device_address = wifi_device_address
    context.store.save(state)

    if usb_error_message:
        st.warning(usb_error_message)
    elif transport is Record3DTransportId.USB and not usb_devices:
        st.warning("No USB Record3D devices are currently connected.")

    start_disabled = _start_disabled(
        transport=transport,
        usb_devices=usb_devices,
        wifi_device_address=wifi_device_address,
    )
    start_col, stop_col, source_col = st.columns((0.8, 0.8, 1.8), gap="small")
    with start_col:
        start_requested = st.button("Start", type="primary", disabled=start_disabled, width="stretch")
    with stop_col:
        stop_requested = st.button("Stop", disabled=not page_state.is_running, width="stretch")
    with source_col:
        st.markdown(_stream_hint(transport))

    if start_requested:
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


def _sync_running_flag(context: AppContext) -> None:
    snapshot = context.record3d_runtime.snapshot()
    if (
        context.state.record3d.is_running
        and snapshot.state not in {Record3DStreamState.CONNECTING, Record3DStreamState.STREAMING}
    ):
        context.state.record3d.is_running = False
        context.store.save(context.state)


def _render_live_snapshot(context: AppContext) -> None:
    page_state = context.state.record3d

    @st.fragment(run_every=0.5 if page_state.is_running else None)
    def _render_fragment() -> None:
        snapshot = context.record3d_runtime.snapshot()
        if (
            page_state.is_running
            and snapshot.state not in {Record3DStreamState.CONNECTING, Record3DStreamState.STREAMING}
        ):
            context.state.record3d.is_running = False
            context.store.save(context.state)
        _render_snapshot(snapshot)

    _render_fragment()


def _render_snapshot(snapshot: Record3DStreamSnapshot) -> None:
    metric_columns = st.columns(4, gap="small")
    metric_columns[0].metric("Status", snapshot.state.value.upper())
    metric_columns[1].metric("Received Frames", str(snapshot.received_frames))
    metric_columns[2].metric("Frame Rate", f"{snapshot.measured_fps:.2f} fps")
    metric_columns[3].metric("Transport", snapshot.transport.label if snapshot.transport is not None else "Idle")

    if snapshot.source_label:
        st.markdown(f"**Source:** `{snapshot.source_label}`")
    if snapshot.error_message:
        st.error(snapshot.error_message)

    packet = snapshot.latest_packet
    if packet is None:
        if snapshot.state is Record3DStreamState.CONNECTING:
            st.info("Connecting to Record3D and waiting for the first frame.")
        elif snapshot.state is Record3DStreamState.IDLE:
            st.info("Start a USB or Wi-Fi Record3D stream to see live RGBD packets here.")
        elif snapshot.state is Record3DStreamState.DISCONNECTED:
            st.warning("The Record3D stream disconnected before a new frame could be displayed.")
        return

    intrinsics_col, details_col = st.columns((1.2, 1.0), gap="large")
    with intrinsics_col:
        st.subheader("Camera Intrinsics")
        if packet.intrinsic_matrix is None:
            st.info("Camera intrinsics are not available for the current packet.")
        else:
            st.markdown(_format_intrinsic_matrix(packet.intrinsic_matrix))
    with details_col:
        st.subheader("Packet Metadata")
        if "original_size" in packet.metadata:
            original_width, original_height = packet.metadata["original_size"]
            st.markdown(f"- Original size: `{original_width} x {original_height}`")
        st.markdown(f"- Arrival timestamp: `{packet.arrival_timestamp_s:.3f}`")

    frame_columns = st.columns(3, gap="large")
    with frame_columns[0]:
        st.markdown("**RGB Frame**")
        st.image(packet.rgb, channels="RGB", clamp=True)
    with frame_columns[1]:
        st.markdown("**Depth Frame**")
        st.image(_normalize_grayscale(packet.depth), clamp=True)
    with frame_columns[2]:
        st.markdown("**Uncertainty / Confidence**")
        if packet.uncertainty is None:
            st.info("Uncertainty / confidence is not available for this transport.")
        else:
            st.image(_normalize_grayscale(packet.uncertainty), clamp=True)


def _format_intrinsic_matrix(matrix: Record3DIntrinsicMatrix) -> str:
    return (
        "$$K = \\begin{bmatrix}"
        f"{matrix.fx:.3f} & 0.000 & {matrix.tx:.3f} \\\\ "
        f"0.000 & {matrix.fy:.3f} & {matrix.ty:.3f} \\\\ "
        "0.000 & 0.000 & 1.000"
        "\\end{bmatrix}$$"
    )


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
