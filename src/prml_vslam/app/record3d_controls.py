"""Shared Record3D transport controls for app pages."""

from __future__ import annotations

import streamlit as st
from pydantic import Field

from prml_vslam.io.record3d import Record3DDevice, Record3DTransportId, list_record3d_usb_devices
from prml_vslam.utils import BaseData


class Record3DTransportSelection(BaseData):
    """Resolved Record3D transport inputs for one page render."""

    transport: Record3DTransportId
    """Selected Record3D transport."""

    usb_device_index: int = 0
    """Selected USB device index when using the USB transport."""

    wifi_device_address: str = ""
    """Entered Wi-Fi preview device address."""

    usb_devices: list[Record3DDevice] = Field(default_factory=list)
    """Discovered USB devices for the current render pass."""

    usb_error_message: str = ""
    """Discovery error surfaced while checking USB devices."""

    input_error: str | None = None
    """Transport-specific input error that should disable start actions when present."""


def render_record3d_transport_controls(
    *,
    transport: Record3DTransportId,
    usb_device_index: int,
    wifi_device_address: str,
    widget_key_prefix: str,
) -> Record3DTransportSelection:
    """Render the shared Record3D transport controls and return the selection."""
    selected_transport = st.segmented_control(
        "Transport",
        options=list(Record3DTransportId),
        default=transport,
        format_func=lambda item: item.label,
        selection_mode="single",
        key=f"{widget_key_prefix}_transport_selector",
        width="stretch",
    )
    resolved_transport = transport if selected_transport is None else selected_transport
    usb_devices: list[Record3DDevice] = []
    usb_error_message = ""
    resolved_usb_device_index = usb_device_index
    resolved_wifi_device_address = wifi_device_address

    if resolved_transport is Record3DTransportId.USB:
        try:
            usb_devices = list_record3d_usb_devices()
        except Exception as exc:
            usb_error_message = str(exc)
        resolved_usb_device_index = _render_usb_selector(
            current_index=usb_device_index,
            devices=usb_devices,
            widget_key_prefix=widget_key_prefix,
        )
    else:
        resolved_wifi_device_address = st.text_input(
            "Wi-Fi Preview Device Address",
            value=wifi_device_address,
            placeholder="myiPhone.local or 192.168.1.100",
            key=f"{widget_key_prefix}_wifi_device_address",
        ).strip()

    return Record3DTransportSelection(
        transport=resolved_transport,
        usb_device_index=resolved_usb_device_index,
        wifi_device_address=resolved_wifi_device_address,
        usb_devices=usb_devices,
        usb_error_message=usb_error_message,
        input_error=record3d_transport_input_error(
            transport=resolved_transport,
            wifi_device_address=resolved_wifi_device_address,
            usb_devices=usb_devices,
            usb_error_message=usb_error_message,
        ),
    )


def record3d_transport_input_error(
    *,
    transport: Record3DTransportId,
    wifi_device_address: str,
    usb_devices: list[Record3DDevice] | None = None,
    usb_error_message: str = "",
) -> str | None:
    """Return a surfaced input error for the selected Record3D transport."""
    if transport is Record3DTransportId.WIFI:
        return None if wifi_device_address != "" else "Enter a Record3D Wi-Fi preview device address."
    if usb_error_message:
        return usb_error_message
    if usb_devices is None:
        try:
            usb_devices = list_record3d_usb_devices()
        except Exception as exc:
            return str(exc)
    devices = usb_devices
    return None if devices else "No USB Record3D devices are currently connected."


def render_record3d_transport_details(selection: Record3DTransportSelection) -> None:
    """Render the standard transport-detail block for one Record3D selection."""
    with st.expander("Transport details", expanded=bool(selection.usb_error_message)):
        st.write(selection.transport.stream_hint())
        if selection.usb_error_message:
            st.warning(selection.usb_error_message)
        elif selection.transport is Record3DTransportId.USB and not selection.usb_devices:
            st.info("No USB Record3D devices are currently connected.")


def _render_usb_selector(
    *,
    current_index: int,
    devices: list[Record3DDevice],
    widget_key_prefix: str,
) -> int:
    if not devices:
        st.selectbox(
            "USB Device",
            options=["No USB device available"],
            index=0,
            disabled=True,
            key=f"{widget_key_prefix}_usb_device_selector",
        )
        return 0
    selected_index = current_index if 0 <= current_index < len(devices) else 0
    selected_device = st.selectbox(
        "USB Device",
        options=devices,
        index=selected_index,
        format_func=lambda item: f"{item.udid} ({item.product_id})",
        key=f"{widget_key_prefix}_usb_device_selector",
    )
    return devices.index(selected_device)


__all__ = [
    "Record3DTransportSelection",
    "record3d_transport_input_error",
    "render_record3d_transport_details",
    "render_record3d_transport_controls",
]
