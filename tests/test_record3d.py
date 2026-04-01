"""Tests for the optional Record3D integration."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from prml_vslam.io import record3d as record3d_module
from prml_vslam.io.record3d import (
    Record3DDependencyError,
    Record3DDeviceType,
    Record3DPreviewConfig,
    Record3DStreamConfig,
)


class FakeRecord3DStream:
    """Small in-memory stand-in for the upstream Record3D bindings."""

    connected_devices = [
        SimpleNamespace(product_id=101, udid="device-101"),
        SimpleNamespace(product_id=202, udid="device-202"),
    ]
    instances: list[FakeRecord3DStream] = []

    def __init__(self) -> None:
        self.on_new_frame = None
        self.on_stream_stopped = None
        self.connected_device = None
        self.disconnected = False
        type(self).instances.append(self)

    @staticmethod
    def get_connected_devices() -> list[SimpleNamespace]:
        return list(FakeRecord3DStream.connected_devices)

    def connect(self, device: SimpleNamespace) -> bool:
        self.connected_device = device
        if self.on_new_frame is not None:
            self.on_new_frame()
        return True

    def disconnect(self) -> None:
        self.disconnected = True
        if self.on_stream_stopped is not None:
            self.on_stream_stopped()

    def get_depth_frame(self) -> np.ndarray:
        return np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)

    def get_rgb_frame(self) -> np.ndarray:
        return np.array(
            [
                [[1, 2, 3], [4, 5, 6]],
                [[7, 8, 9], [10, 11, 12]],
            ],
            dtype=np.uint8,
        )

    def get_confidence_frame(self) -> np.ndarray:
        return np.array([[0, 1], [2, 3]], dtype=np.uint8)

    def get_intrinsic_mat(self) -> SimpleNamespace:
        return SimpleNamespace(fx=100.0, fy=200.0, tx=10.0, ty=20.0)

    def get_camera_pose(self) -> SimpleNamespace:
        return SimpleNamespace(qx=0.1, qy=0.2, qz=0.3, qw=0.4, tx=1.0, ty=2.0, tz=3.0)

    def get_device_type(self) -> int:
        return Record3DDeviceType.LIDAR


@pytest.fixture(autouse=True)
def reset_fake_streams() -> None:
    FakeRecord3DStream.instances = []


def test_record3d_stream_requires_optional_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_missing(module_name: str) -> None:
        raise ModuleNotFoundError(module_name)

    monkeypatch.setattr(record3d_module.importlib, "import_module", raise_missing)

    with pytest.raises(Record3DDependencyError, match="uv sync --extra streaming"):
        Record3DStreamConfig().setup_target()


def test_record3d_stream_lists_connected_devices(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = SimpleNamespace(Record3DStream=FakeRecord3DStream)
    monkeypatch.setattr(record3d_module, "_import_record3d_module", lambda: fake_module)

    session = Record3DStreamConfig().setup_target()

    assert session is not None
    devices = session.list_devices()

    assert [device.product_id for device in devices] == [101, 202]
    assert [device.udid for device in devices] == ["device-101", "device-202"]


def test_record3d_stream_wait_for_frame_returns_typed_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = SimpleNamespace(Record3DStream=FakeRecord3DStream)
    monkeypatch.setattr(record3d_module, "_import_record3d_module", lambda: fake_module)

    session = Record3DStreamConfig(device_index=1, frame_timeout_seconds=0.1).setup_target()

    assert session is not None
    connected = session.connect()
    frame = session.wait_for_frame()

    assert connected.product_id == 202
    assert frame.device_type is Record3DDeviceType.LIDAR
    assert frame.rgb.shape == (2, 2, 3)
    assert frame.depth.shape == (2, 2)
    assert frame.confidence.shape == (2, 2)
    assert frame.intrinsic_matrix.as_matrix()[0, 0] == 100.0
    assert frame.camera_pose.tz == 3.0


def test_record3d_preview_runs_single_frame_and_disconnects(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = SimpleNamespace(Record3DStream=FakeRecord3DStream)
    monkeypatch.setattr(record3d_module, "_import_record3d_module", lambda: fake_module)

    shown_windows: list[str] = []
    destroyed = {"called": False}

    monkeypatch.setattr(record3d_module.cv2, "imshow", lambda name, image: shown_windows.append(name))
    monkeypatch.setattr(record3d_module.cv2, "waitKey", lambda _: ord("q"))
    monkeypatch.setattr(record3d_module.cv2, "destroyAllWindows", lambda: destroyed.__setitem__("called", True))

    preview = Record3DPreviewConfig(max_frames=1).setup_target()

    assert preview is not None
    preview.run()

    assert "Record3D RGB" in shown_windows
    assert "Record3D Depth" in shown_windows
    assert "Record3D Confidence" in shown_windows
    assert FakeRecord3DStream.instances[-1].disconnected is True
    assert destroyed["called"] is True
