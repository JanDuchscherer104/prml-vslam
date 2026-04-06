"""Tests for the optional Record3D USB integration."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from prml_vslam.io import record3d as record3d_module
from prml_vslam.io import record3d_source as record3d_source_module
from prml_vslam.io.record3d import (
    Record3DDeviceType,
    Record3DStreamConfig,
    Record3DTransportId,
    build_record3d_frame_details,
    list_record3d_usb_devices,
    open_record3d_usb_packet_stream,
)
from prml_vslam.io.record3d_source import Record3DStreamingSourceConfig
from prml_vslam.protocols.source import OfflineSequenceSource, StreamingSequenceSource


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

    with pytest.raises(RuntimeError, match="uv sync --extra streaming"):
        Record3DStreamConfig().setup_target()


def test_record3d_stream_lists_connected_devices(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = SimpleNamespace(Record3DStream=FakeRecord3DStream)
    monkeypatch.setattr(record3d_module, "_import_record3d_module", lambda: fake_module)

    session = Record3DStreamConfig().setup_target()

    assert session is not None
    devices = session.list_devices()

    assert [device.product_id for device in devices] == [101, 202]
    assert [device.udid for device in devices] == ["device-101", "device-202"]
    helper_devices = list_record3d_usb_devices()
    assert [device.product_id for device in helper_devices] == [101, 202]
    assert [device.udid for device in helper_devices] == ["device-101", "device-202"]


def test_record3d_stream_wait_for_packet_returns_shared_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = SimpleNamespace(Record3DStream=FakeRecord3DStream)
    monkeypatch.setattr(record3d_module, "_import_record3d_module", lambda: fake_module)

    stream = Record3DStreamConfig(device_index=1, frame_timeout_seconds=0.1).setup_target()

    assert stream is not None
    connected = stream.connect()
    packet = stream.wait_for_packet()

    assert connected.product_id == 202
    assert packet.metadata["transport"] == Record3DTransportId.USB.value
    assert packet.metadata["device_type"] == Record3DDeviceType.LIDAR.value
    assert packet.rgb.shape == (2, 2, 3)
    assert packet.depth.shape == (2, 2)
    assert packet.intrinsics is not None
    assert packet.intrinsics.fx == 100.0
    assert packet.pose is not None
    assert packet.pose.tx == 1.0
    assert packet.pose.tz == 3.0
    assert packet.confidence is not None
    np.testing.assert_array_equal(packet.confidence, np.array([[0, 1], [2, 3]], dtype=np.float32))


def test_usb_packet_stream_wait_for_packet_returns_shared_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = SimpleNamespace(Record3DStream=FakeRecord3DStream)
    monkeypatch.setattr(record3d_module, "_import_record3d_module", lambda: fake_module)

    stream = open_record3d_usb_packet_stream(device_index=1, frame_timeout_seconds=0.1)

    assert stream is not None
    device = stream.connect()
    packet = stream.wait_for_packet()

    assert device.udid == "device-202"
    assert packet.metadata["transport"] == Record3DTransportId.USB.value
    assert packet.rgb.shape == (2, 2, 3)
    assert packet.depth.shape == (2, 2)
    assert packet.intrinsics is not None
    assert packet.metadata["device_type"] == Record3DDeviceType.LIDAR.value


def test_usb_packet_stream_disconnect_stops_active_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = SimpleNamespace(Record3DStream=FakeRecord3DStream)
    monkeypatch.setattr(record3d_module, "_import_record3d_module", lambda: fake_module)

    stream = open_record3d_usb_packet_stream(device_index=0, frame_timeout_seconds=0.1)
    stream.connect()

    active_binding = FakeRecord3DStream.instances[-1]
    stream.disconnect()

    assert active_binding.disconnected is True


def test_record3d_usb_streaming_source_satisfies_shared_source_protocol(monkeypatch, tmp_path) -> None:
    sentinel_stream = object()
    monkeypatch.setattr(
        record3d_source_module,
        "open_record3d_usb_packet_stream",
        lambda *, device_index, frame_timeout_seconds: (
            sentinel_stream if (device_index, frame_timeout_seconds) == (1, 0.25) else None
        ),
    )

    source = Record3DStreamingSourceConfig(
        transport=Record3DTransportId.USB,
        device_index=1,
        frame_timeout_seconds=0.25,
    ).setup_target()

    assert source is not None
    assert isinstance(source, OfflineSequenceSource)
    assert isinstance(source, StreamingSequenceSource)
    assert source.label == "Record3D USB device #1"
    assert source.prepare_sequence_manifest(tmp_path).sequence_id == "record3d-usb-1"
    assert source.open_stream(loop=True) is sentinel_stream


def test_build_record3d_frame_details_falls_back_to_packet_timestamp() -> None:
    packet = record3d_module.FramePacket(
        seq=0,
        timestamp_ns=2_000_000_000,
        arrival_timestamp_s=None,
        metadata={"original_size": [960, 720]},
    )

    assert build_record3d_frame_details(packet, source_label="USB device #1") == {
        "arrival_timestamp_s": 2.0,
        "source": "USB device #1",
        "original_size": [960, 720],
        "metadata": {"original_size": [960, 720]},
    }
