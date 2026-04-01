"""Tests for the Streamlit Record3D Wi-Fi viewer component."""

from __future__ import annotations

import importlib
import json

from prml_vslam.io import record3d_wifi as record3d_wifi_module
from prml_vslam.io.record3d_wifi import (
    RECORD3D_WIFI_COMPONENT_CSS,
    RECORD3D_WIFI_COMPONENT_HTML,
    RECORD3D_WIFI_COMPONENT_JS,
    RECORD3D_WIFI_COMPONENT_KEY,
    RECORD3D_WIFI_COMPONENT_NAME,
    Record3DWiFiViewerState,
    render_record3d_wifi_viewer,
)


def test_record3d_wifi_component_registers_once(monkeypatch) -> None:
    registrations: list[tuple[str, dict[str, object]]] = []

    def fake_component(name: str, **kwargs: object):
        registrations.append((name, kwargs))
        return lambda **mount_kwargs: mount_kwargs.get("default", {})

    with monkeypatch.context() as patch:
        patch.setattr(record3d_wifi_module.st.components.v2, "component", fake_component)
        importlib.reload(record3d_wifi_module)
        assert len(registrations) == 1
        assert registrations[0][0] == RECORD3D_WIFI_COMPONENT_NAME
        assert "Connect" in registrations[0][1]["html"]
        assert "/answer" in registrations[0][1]["js"]

    importlib.reload(record3d_wifi_module)


def test_record3d_wifi_viewer_state_has_stable_defaults() -> None:
    state = Record3DWiFiViewerState()

    assert state.model_dump(mode="python") == {
        "device_address": "",
        "connection_state": "idle",
        "error_message": "",
        "metadata": {},
        "show_inv_dist_std": True,
        "equalize_depth_histogram": False,
    }


def test_render_record3d_wifi_viewer_mounts_with_persisted_data(monkeypatch) -> None:
    mounted: dict[str, object] = {}

    def fake_component(**kwargs: object) -> dict[str, object]:
        mounted.update(kwargs)
        return {
            "device_address": "http://myiPhone.local",
            "connection_state": "streaming",
            "error_message": "",
            "metadata": {"K": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]},
            "show_inv_dist_std": False,
            "equalize_depth_histogram": True,
        }

    monkeypatch.setattr(record3d_wifi_module, "RECORD3D_WIFI_COMPONENT", fake_component)

    state = render_record3d_wifi_viewer(
        initial_state=Record3DWiFiViewerState(
            device_address="http://saved-device.local",
            show_inv_dist_std=False,
            equalize_depth_histogram=True,
        )
    )

    assert mounted["key"] == RECORD3D_WIFI_COMPONENT_KEY
    assert json.loads(mounted["data"]) == {
        "device_address": "http://saved-device.local",
        "show_inv_dist_std": False,
        "equalize_depth_histogram": True,
    }
    assert state.device_address == "http://myiPhone.local"
    assert state.connection_state == "streaming"
    assert state.metadata["K"][0][0] == 1
    assert state.show_inv_dist_std is False
    assert state.equalize_depth_histogram is True


def test_record3d_wifi_viewer_state_normalizes_missing_component_result() -> None:
    state = Record3DWiFiViewerState.from_component_result(None)

    assert state == Record3DWiFiViewerState()


def test_record3d_wifi_assets_cover_webrtc_signaling_and_cleanup() -> None:
    assert "Record3D Wi-Fi" in RECORD3D_WIFI_COMPONENT_HTML
    assert "Histogram equalize depth preview" in RECORD3D_WIFI_COMPONENT_HTML
    assert "record3d-rgb-canvas" in RECORD3D_WIFI_COMPONENT_HTML
    assert "record3d-depth-canvas" in RECORD3D_WIFI_COMPONENT_HTML
    assert "record3d-toggle-inv-dist-std" in RECORD3D_WIFI_COMPONENT_HTML
    assert "record3d-toggle-depth-equalization" in RECORD3D_WIFI_COMPONENT_HTML

    assert "/getOffer" in RECORD3D_WIFI_COMPONENT_JS
    assert "/answer" in RECORD3D_WIFI_COMPONENT_JS
    assert "/metadata" in RECORD3D_WIFI_COMPONENT_JS
    assert "class SignalingClient" in RECORD3D_WIFI_COMPONENT_JS
    assert "retrieveOffer" in RECORD3D_WIFI_COMPONENT_JS
    assert "sendAnswer" in RECORD3D_WIFI_COMPONENT_JS
    assert "RTCPeerConnection" in RECORD3D_WIFI_COMPONENT_JS
    assert "requestAnimationFrame" in RECORD3D_WIFI_COMPONENT_JS
    assert "equalizeHistogram" in RECORD3D_WIFI_COMPONENT_JS
    assert "show_inv_dist_std" in RECORD3D_WIFI_COMPONENT_JS
    assert "beforeunload" in RECORD3D_WIFI_COMPONENT_JS

    assert ".record3d-frame-grid" in RECORD3D_WIFI_COMPONENT_CSS
    assert ".record3d-frame-panel" in RECORD3D_WIFI_COMPONENT_CSS
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in RECORD3D_WIFI_COMPONENT_CSS
