"""Small controller helpers for the Record3D Streamlit page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.utils import BaseData

from .models import Record3DStreamSnapshot, Record3DStreamState
from .state import save_model_updates

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
    transport = page_state.transport
    usb_device_index = page_state.usb_device_index
    wifi_device_address = page_state.wifi_device_address
    is_running = page_state.is_running

    if action.transport is not transport:
        if is_running:
            context.record3d_runtime.stop()
            is_running = False
        transport = action.transport

    if action.start_requested:
        usb_device_index = usb_device_index if action.usb_device_index is None else action.usb_device_index
        wifi_device_address = wifi_device_address if action.wifi_device_address is None else action.wifi_device_address
        selectors_changed = (
            usb_device_index != page_state.usb_device_index or wifi_device_address != page_state.wifi_device_address
        )
        if selectors_changed and is_running:
            context.record3d_runtime.stop()
            is_running = False
        match transport:
            case Record3DTransportId.USB:
                context.record3d_runtime.start_usb(device_index=usb_device_index)
            case Record3DTransportId.WIFI:
                context.record3d_runtime.start_wifi(device_address=wifi_device_address)
        is_running = True
    elif action.stop_requested and is_running:
        context.record3d_runtime.stop()
        is_running = False

    save_model_updates(
        context.store,
        context.state,
        page_state,
        transport=transport,
        usb_device_index=usb_device_index,
        wifi_device_address=wifi_device_address,
        is_running=is_running,
    )

    snapshot = sync_record3d_running_state(context)
    return snapshot


def sync_record3d_running_state(
    context: AppContext,
    snapshot: Record3DStreamSnapshot | None = None,
) -> Record3DStreamSnapshot:
    """Keep persisted running state aligned with the latest runtime snapshot."""
    current_snapshot = context.record3d_runtime.snapshot() if snapshot is None else snapshot
    if context.state.record3d.is_running and current_snapshot.state not in _ACTIVE_STREAM_STATES:
        save_model_updates(context.store, context.state, context.state.record3d, is_running=False)
    return current_snapshot


__all__ = ["Record3DPageAction", "handle_record3d_page_action", "sync_record3d_running_state"]
