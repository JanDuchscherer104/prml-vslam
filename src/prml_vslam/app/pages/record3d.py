"""Record3D streaming page for live browser-side inspection."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.io import Record3DIntrinsicMatrix, Record3DWiFiViewerState, render_record3d_wifi_viewer

from ..models import StreamingPageState
from ..ui import render_header, render_key_value_rows

if TYPE_CHECKING:
    from ..bootstrap import AppContext


def render(context: AppContext) -> None:
    """Render the Record3D streaming page."""
    render_header(
        title="Record3D Streaming",
        kicker="Live capture inspection",
        copy=(
            "Preview the Record3D Wi-Fi stream directly in the browser, inspect camera metadata, "
            "and check optional USB availability without bringing back the old monolithic workbench."
        ),
    )

    previous_state = Record3DWiFiViewerState(
        device_address=context.state.streaming.device_address,
        connection_state=context.state.streaming.connection_state,
        error_message=context.state.streaming.error_message,
        metadata=context.state.streaming.metadata,
        show_inv_dist_std=context.state.streaming.show_inv_dist_std,
        equalize_depth_histogram=context.state.streaming.equalize_depth_histogram,
    )
    component_error: str | None = None
    try:
        viewer_state = render_record3d_wifi_viewer(initial_state=previous_state)
    except Exception as exc:
        viewer_state = previous_state
        component_error = f"Record3D Wi-Fi viewer is unavailable in this execution context: {exc}"

    if component_error is not None:
        st.info(component_error)

    usb_status = context.services.record3d.probe_usb_status()

    context.state.streaming = StreamingPageState(
        device_address=viewer_state.device_address,
        connection_state=viewer_state.connection_state,
        error_message=viewer_state.error_message,
        metadata=viewer_state.metadata,
        show_inv_dist_std=viewer_state.show_inv_dist_std,
        equalize_depth_histogram=viewer_state.equalize_depth_histogram,
    )
    context.store.save(context.state)

    summary_col, usb_col = st.columns([1.2, 0.8], gap="large")
    with summary_col:
        st.markdown("### Connection summary")
        render_key_value_rows(
            [
                {"field": "Wi-Fi state", "value": viewer_state.connection_state},
                {"field": "Device address", "value": viewer_state.device_address or "not connected"},
                {"field": "Depth equalization", "value": viewer_state.equalize_depth_histogram},
                {"field": "inv_dist_std pane", "value": viewer_state.show_inv_dist_std},
            ]
        )

        intrinsics = Record3DIntrinsicMatrix.from_matrix_payload(viewer_state.metadata.get("K"))
        if intrinsics is not None:
            st.markdown("### Camera intrinsics")
            st.markdown(intrinsics.to_markdown_latex())
            render_key_value_rows(
                [
                    {"parameter": "fx", "value": intrinsics.fx},
                    {"parameter": "fy", "value": intrinsics.fy},
                    {"parameter": "cx", "value": intrinsics.tx},
                    {"parameter": "cy", "value": intrinsics.ty},
                ]
            )

        if viewer_state.metadata:
            st.markdown("### Metadata snapshot")
            render_key_value_rows(
                [
                    {"key": key, "value": value}
                    for key, value in sorted(viewer_state.metadata.items(), key=lambda item: item[0])
                ]
            )

    with usb_col:
        st.markdown("### USB status")
        if not usb_status.dependency_available:
            st.info(usb_status.error_message or "Install the optional streaming extras to use the USB bindings.")
            st.code("uv sync --extra streaming", language="bash")
        elif usb_status.error_message:
            st.warning(usb_status.error_message)
        elif usb_status.devices:
            render_key_value_rows(
                [{"product_id": device.product_id, "udid": device.udid} for device in usb_status.devices]
            )
        else:
            st.caption("No USB Record3D devices are currently connected.")

        st.markdown("### Notes")
        st.markdown(
            """
            - Wi-Fi preview is browser-side only and does not feed the Python pipeline yet.
            - Chrome and Safari are the supported browsers for this flow.
            - Record3D allows only one Wi-Fi receiver at a time.
            - USB preview remains the higher-fidelity path when the optional native bindings are installed.
            """
        )


__all__ = ["render"]
