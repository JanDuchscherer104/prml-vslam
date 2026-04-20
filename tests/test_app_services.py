"""Focused tests for app-owned preview runtime controllers."""

from __future__ import annotations

import time
from threading import Event

import numpy as np

from prml_vslam.app.models import PreviewStreamState
from prml_vslam.app.services import AdvioPreviewRuntimeController, Record3DStreamRuntimeController
from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.interfaces import FramePacket, FramePacketProvenance, FrameTransform
from prml_vslam.io.record3d import Record3DDevice, Record3DTransportId


class _BlockingPacketStream:
    """Emit one packet, then block until the test disconnects the stream."""

    def __init__(
        self, *, packet: FramePacket, connected_target: Record3DDevice | None = None, timeout_error: str
    ) -> None:
        self._packet = packet
        self._connected_target = connected_target
        self._timeout_error = timeout_error
        self._disconnect_event = Event()
        self.connected = False
        self.disconnected = False

    def connect(self) -> Record3DDevice | None:
        self.connected = True
        return self._connected_target

    def disconnect(self) -> None:
        self.disconnected = True
        self._disconnect_event.set()

    def wait_for_packet(self, timeout_seconds: float | None = None) -> FramePacket:
        if self._packet is not None:
            packet, self._packet = self._packet, None
            return packet
        wait_seconds = 0.05 if timeout_seconds is None else max(timeout_seconds, 0.0)
        self._disconnect_event.wait(timeout=wait_seconds)
        raise RuntimeError(self._timeout_error)


def _packet(*, seq: int, timestamp_ns: int, arrival_timestamp_s: float | None) -> FramePacket:
    return FramePacket(
        seq=seq,
        timestamp_ns=timestamp_ns,
        arrival_timestamp_s=arrival_timestamp_s,
        pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0),
        provenance=FramePacketProvenance(source_id="test"),
    )


def _wait_for_snapshot(predicate, *, timeout_seconds: float = 2.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Timed out waiting for the preview snapshot to reach the expected state.")


def test_advio_preview_runtime_controller_processes_one_packet() -> None:
    stream = _BlockingPacketStream(
        packet=_packet(seq=1, timestamp_ns=1_000_000_000, arrival_timestamp_s=None),
        timeout_error="Preview stream closed.",
    )
    controller = AdvioPreviewRuntimeController(frame_timeout_seconds=5.0)

    controller.start(
        sequence_id=7,
        sequence_label="ADVIO 07",
        pose_source=AdvioPoseSource.GROUND_TRUTH,
        stream=stream,
    )

    _wait_for_snapshot(
        lambda: controller.snapshot().state is PreviewStreamState.STREAMING
        and controller.snapshot().received_frames == 1
    )
    snapshot = controller.snapshot()

    assert stream.connected is True
    assert snapshot.sequence_id == 7
    assert snapshot.sequence_label == "ADVIO 07"
    assert snapshot.pose_source is AdvioPoseSource.GROUND_TRUTH
    assert snapshot.latest_packet is not None
    assert snapshot.latest_packet.seq == 1
    assert snapshot.received_frames == 1
    assert snapshot.accepted_keyframes == 1
    assert snapshot.trajectory_positions_xyz.shape == (1, 3)
    assert np.allclose(snapshot.trajectory_positions_xyz[0], np.array([1.0, 2.0, 3.0]))
    assert np.allclose(snapshot.trajectory_timestamps_s, np.array([0.0]))

    controller.stop()

    assert stream.disconnected is True
    assert controller.snapshot().state is PreviewStreamState.IDLE


def test_record3d_runtime_controller_formats_usb_source_label() -> None:
    device = Record3DDevice(product_id=1234, udid="device-udid")
    stream = _BlockingPacketStream(
        packet=_packet(seq=2, timestamp_ns=2_000_000_000, arrival_timestamp_s=12.5),
        connected_target=device,
        timeout_error="Timed out waiting for Record3D frame.",
    )
    controller = Record3DStreamRuntimeController(
        frame_timeout_seconds=0.05,
        usb_stream_factory=lambda device_index, timeout_seconds: stream,
    )

    controller.start_usb(device_index=3)

    _wait_for_snapshot(
        lambda: controller.snapshot().state is PreviewStreamState.STREAMING
        and controller.snapshot().received_frames == 1
    )
    snapshot = controller.snapshot()

    assert stream.connected is True
    assert snapshot.transport is Record3DTransportId.USB
    assert snapshot.source_label == "device-udid (1234)"
    assert snapshot.latest_packet is not None
    assert snapshot.latest_packet.seq == 2
    assert snapshot.received_frames == 1
    assert snapshot.accepted_keyframes == 1
    assert np.allclose(snapshot.trajectory_timestamps_s, np.array([12.5]))

    controller.stop()

    assert stream.disconnected is True
    assert controller.snapshot().state is PreviewStreamState.IDLE
