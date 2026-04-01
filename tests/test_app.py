"""Tests for the Streamlit workbench page."""

from __future__ import annotations

from prml_vslam import app as app_module
from prml_vslam.io.record3d_wifi import Record3DWiFiViewerState


def test_run_app_renders_record3d_wifi_section(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(app_module.st, "set_page_config", lambda **kwargs: calls.append(("set_page_config", kwargs)))
    monkeypatch.setattr(app_module.st, "title", lambda message: calls.append(("title", message)))
    monkeypatch.setattr(app_module.st, "caption", lambda message: calls.append(("caption", message)))
    monkeypatch.setattr(app_module.st, "subheader", lambda message: calls.append(("subheader", message)))
    monkeypatch.setattr(app_module.st, "markdown", lambda message: calls.append(("markdown", message)))

    def fake_render_record3d_wifi_viewer() -> Record3DWiFiViewerState:
        calls.append(("render_record3d_wifi_viewer", None))
        return Record3DWiFiViewerState(
            device_address="http://myiPhone.local",
            connection_state="streaming",
            metadata={"K": [525.0, 0.0, 320.0, 0.0, 525.0, 240.0, 0.0, 0.0, 1.0]},
        )

    monkeypatch.setattr(app_module, "render_record3d_wifi_viewer", fake_render_record3d_wifi_viewer)

    app_module.run_app()

    markdown_messages = [value for name, value in calls if name == "markdown"]
    subheaders = [value for name, value in calls if name == "subheader"]
    render_calls = [name for name, _ in calls if name == "render_record3d_wifi_viewer"]

    assert ("title", "PRML VSLAM Workbench") in calls
    assert "Record3D Wi-Fi" in subheaders
    assert "Camera Intrinsics" in subheaders
    assert len(render_calls) == 1
    assert any("display-only" in message for message in markdown_messages)
    assert any("Chrome and Safari" in message for message in markdown_messages)
    assert any(r"\begin{bmatrix}" in message for message in markdown_messages)
    assert any("525.000" in message for message in markdown_messages)
    assert any("320.000" in message for message in markdown_messages)
    assert any("240.000" in message for message in markdown_messages)
    intrinsic_messages = [message for message in markdown_messages if r"\begin{bmatrix}" in message]
    assert any("320.000" in message and "240.000" in message and "1.000" in message for message in intrinsic_messages)
    assert all(
        "Workbench scaffold for the monocular VSLAM benchmark project." not in message for message in markdown_messages
    )
