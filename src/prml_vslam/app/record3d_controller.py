"""Small controller helpers for the Record3D Streamlit page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prml_vslam.io.record3d import Record3DStreamSnapshot, Record3DStreamState, Record3DTransportId
from prml_vslam.utils import BaseData

if TYPE_CHECKING:
    from .bootstrap import AppContext


_ACTIVE_STREAM_STATES = {Record3DStreamState.CONNECTING, Record3DStreamState.STREAMING}


class Record3DPageAction(BaseData):
    """Typed Record3D page action payload."""

    transport: Record3DTransportId
    usb_device_index: int | None = None
    wifi_device_address: str | None = None
    start_requested: bool = False
    stop_requested: bool = False


def handle_record3d_page_action(context: AppContext, action: Record3DPageAction) -> Record3DStreamSnapshot:
    """Apply one Record3D page action and return the latest snapshot."""
    page_state = context.state.record3d
    should_save = False

    if action.transport is not page_state.transport:
        if page_state.is_running:
            context.record3d_runtime.stop()
            page_state.is_running = False
        page_state.transport = action.transport
        should_save = True

    if action.start_requested:
        usb_device_index = page_state.usb_device_index if action.usb_device_index is None else action.usb_device_index
        wifi_device_address = (
            page_state.wifi_device_address if action.wifi_device_address is None else action.wifi_device_address
        )
        selectors_changed = (
            usb_device_index != page_state.usb_device_index or wifi_device_address != page_state.wifi_device_address
        )
        if selectors_changed and page_state.is_running:
            context.record3d_runtime.stop()
            page_state.is_running = False
        page_state.usb_device_index = usb_device_index
        page_state.wifi_device_address = wifi_device_address
        match action.transport:
            case Record3DTransportId.USB:
                context.record3d_runtime.start_usb(device_index=usb_device_index)
            case Record3DTransportId.WIFI:
                context.record3d_runtime.start_wifi(device_address=wifi_device_address)
        page_state.is_running = True
        should_save = True
    elif action.stop_requested and page_state.is_running:
        context.record3d_runtime.stop()
        page_state.is_running = False
        should_save = True

    snapshot = sync_record3d_running_state(context)
    if should_save:
        context.store.save(context.state)
    return snapshot


def sync_record3d_running_state(
    context: AppContext,
    snapshot: Record3DStreamSnapshot | None = None,
) -> Record3DStreamSnapshot:
    """Keep persisted running state aligned with the latest runtime snapshot."""
    current_snapshot = context.record3d_runtime.snapshot() if snapshot is None else snapshot
    if context.state.record3d.is_running and current_snapshot.state not in _ACTIVE_STREAM_STATES:
        context.state.record3d.is_running = False
        context.store.save(context.state)
    return current_snapshot


__all__ = ["Record3DPageAction", "handle_record3d_page_action", "sync_record3d_running_state"]
