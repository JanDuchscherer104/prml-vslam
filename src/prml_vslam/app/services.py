"""Reusable live-preview services for the packaged Streamlit app. Every component of the app must define its own service layer derived from shared service interfaces / protocols."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from enum import StrEnum
from threading import Event, Lock, Thread
from typing import Any, Generic, TypeVar

import numpy as np
from pydantic import Field

from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.interfaces import FramePacket
from prml_vslam.io.record3d import (
    Record3DDevice,
    Record3DStreamConfig,
    Record3DStreamSnapshot,
    Record3DStreamState,
    Record3DTransportId,
    Record3DUSBPacketStreamConfig,
)
from prml_vslam.io.wifi_session import Record3DWiFiStreamConfig
from prml_vslam.protocols import FramePacketStream
from prml_vslam.utils import BaseData

SnapshotT = TypeVar("SnapshotT", bound=BaseData)
StreamT = TypeVar("StreamT")


def empty_positions_xyz() -> np.ndarray:
    return np.empty((0, 3), dtype=np.float64)


def empty_timestamps_s() -> np.ndarray:
    return np.empty((0,), dtype=np.float64)


def _extract_camera_position_from_pose(packet: FramePacket) -> np.ndarray | None:
    if packet.pose is None:
        return None
    position = np.array([packet.pose.tx, packet.pose.ty, packet.pose.tz], dtype=np.float64)
    return position if np.all(np.isfinite(position)) else None


def _to_disconnected_snapshot(snapshot: SnapshotT, *, streaming_state: Any, disconnected_state: Any) -> SnapshotT:
    if snapshot.state is not streaming_state:
        return snapshot
    return snapshot.model_copy(
        update={"state": disconnected_state, "latest_packet": None, "received_frames": 0, "measured_fps": 0.0}
    )


def _is_record3d_frame_timeout(error: RuntimeError) -> bool:
    message = str(error)
    return message.startswith("Timed out waiting ") and "Record3D" in message and " frame." in message


class RollingRuntimeMetrics:
    def __init__(self, *, fps_window_size: int, trajectory_window_size: int) -> None:
        self._arrival_times: deque[float] = deque(maxlen=fps_window_size)
        self._trajectory_positions: deque[np.ndarray] = deque(maxlen=trajectory_window_size)
        self._trajectory_timestamps: deque[float] = deque(maxlen=trajectory_window_size)
        self._received_frames = 0

    def record(
        self,
        *,
        arrival_time_s: float,
        position_xyz: np.ndarray | None,
        trajectory_time_s: float | None,
    ) -> None:
        self._received_frames += 1
        self._arrival_times.append(arrival_time_s)
        if position_xyz is not None and trajectory_time_s is not None:
            self._trajectory_positions.append(position_xyz)
            self._trajectory_timestamps.append(trajectory_time_s)

    def snapshot_fields(self) -> dict[str, int | float | np.ndarray]:
        return {
            "received_frames": self._received_frames,
            "measured_fps": self._measure_fps(self._arrival_times),
            "trajectory_positions_xyz": self._positions_to_array(self._trajectory_positions),
            "trajectory_timestamps_s": np.asarray(tuple(self._trajectory_timestamps), dtype=np.float64),
        }

    @staticmethod
    def _measure_fps(arrival_times: deque[float]) -> float:
        if len(arrival_times) < 2:
            return 0.0
        elapsed = arrival_times[-1] - arrival_times[0]
        return 0.0 if elapsed <= 0.0 else float((len(arrival_times) - 1) / elapsed)

    @staticmethod
    def _positions_to_array(positions: deque[np.ndarray]) -> np.ndarray:
        return np.vstack(tuple(positions)).astype(np.float64, copy=False) if positions else empty_positions_xyz()


class WorkerRuntime(Generic[SnapshotT, StreamT]):
    def __init__(
        self,
        *,
        empty_snapshot: Callable[[], SnapshotT],
        stop_timeout_message: str,
        disconnect_stream: Callable[[StreamT], None],
    ) -> None:
        self._empty_snapshot = empty_snapshot
        self._stop_timeout_message = stop_timeout_message
        self._disconnect_stream = disconnect_stream
        self._lock = Lock()
        self._snapshot = empty_snapshot()
        self._active_stream: StreamT | None = None
        self._active_stop_event: Event | None = None
        self._worker_thread: Thread | None = None

    def snapshot(self) -> SnapshotT:
        with self._lock:
            return self._snapshot.model_copy(deep=True)

    def launch(
        self,
        *,
        connecting_snapshot: SnapshotT,
        thread_name: str,
        worker_target: Callable[[Event], None],
    ) -> None:
        self.stop()
        stop_event = Event()
        worker = Thread(target=worker_target, args=(stop_event,), name=thread_name, daemon=True)
        with self._lock:
            self._active_stop_event = stop_event
            self._worker_thread = worker
            self._snapshot = connecting_snapshot
        worker.start()

    def register_stream(self, *, stop_event: Event, stream: StreamT) -> None:
        with self._lock:
            if self._active_stop_event is stop_event:
                self._active_stream = stream

    def update_fields(self, **fields: object) -> None:
        with self._lock:
            self._snapshot = self._snapshot.model_copy(update=fields)

    def stop(self) -> None:
        with self._lock:
            worker = self._worker_thread
            stop_event = self._active_stop_event
            stream = self._active_stream
            self._active_stream = None
        if stop_event is not None:
            stop_event.set()
        if stream is not None:
            self._disconnect_stream(stream)
        if worker is not None:
            worker.join(timeout=2.0)
            if worker.is_alive():
                raise RuntimeError(self._stop_timeout_message)
        with self._lock:
            self._active_stream = None
            self._active_stop_event = None
            self._worker_thread = None
            self._snapshot = self._empty_snapshot()

    def finalize_run(
        self,
        *,
        stop_event: Event,
        disconnected_snapshot: Callable[[SnapshotT], SnapshotT],
    ) -> None:
        stream: StreamT | None = None
        with self._lock:
            if self._active_stop_event is stop_event:
                stream = self._active_stream
                self._active_stream = None
                self._active_stop_event = None
                self._worker_thread = None
            self._snapshot = self._empty_snapshot() if stop_event.is_set() else disconnected_snapshot(self._snapshot)
        if stream is not None:
            self._disconnect_stream(stream)


class Record3DAppService:
    def list_usb_devices(self) -> list[Record3DDevice]:
        stream = Record3DUSBPacketStreamConfig().setup_target()
        if stream is None:
            raise RuntimeError("Failed to initialize the USB Record3D packet stream.")
        return stream.list_devices()


class AdvioPreviewStreamState(StrEnum):
    IDLE = "idle"
    CONNECTING = "connecting"
    STREAMING = "streaming"
    DISCONNECTED = "disconnected"
    FAILED = "failed"


class AdvioPreviewSnapshot(BaseData):
    state: AdvioPreviewStreamState = AdvioPreviewStreamState.IDLE
    sequence_id: int | None = None
    sequence_label: str = ""
    pose_source: AdvioPoseSource | None = None
    latest_packet: FramePacket | None = None
    received_frames: int = 0
    measured_fps: float = 0.0
    trajectory_positions_xyz: np.ndarray = Field(default_factory=empty_positions_xyz)
    trajectory_timestamps_s: np.ndarray = Field(default_factory=empty_timestamps_s)
    error_message: str = ""


class AdvioPreviewRuntimeController:
    def __init__(
        self,
        *,
        frame_timeout_seconds: float = 0.5,
        fps_window_size: int = 30,
        trajectory_window_size: int = 512,
    ) -> None:
        self.frame_timeout_seconds = frame_timeout_seconds
        self.fps_window_size = fps_window_size
        self.trajectory_window_size = trajectory_window_size
        self._runtime = WorkerRuntime(
            empty_snapshot=AdvioPreviewSnapshot,
            stop_timeout_message="Timed out stopping the ADVIO preview worker thread.",
            disconnect_stream=lambda stream: stream.disconnect(),
        )

    def snapshot(self) -> AdvioPreviewSnapshot:
        return self._runtime.snapshot()

    def start(
        self,
        *,
        sequence_id: int,
        sequence_label: str,
        pose_source: AdvioPoseSource,
        stream: FramePacketStream,
    ) -> None:
        self._runtime.launch(
            connecting_snapshot=AdvioPreviewSnapshot(
                state=AdvioPreviewStreamState.CONNECTING,
                sequence_id=sequence_id,
                sequence_label=sequence_label,
                pose_source=pose_source,
            ),
            thread_name=f"ADVIO-preview-{sequence_id:02d}",
            worker_target=lambda stop_event: self._run_stream_worker(
                sequence_id=sequence_id,
                sequence_label=sequence_label,
                pose_source=pose_source,
                stream=stream,
                stop_event=stop_event,
            ),
        )

    def stop(self) -> None:
        self._runtime.stop()

    def _run_stream_worker(
        self,
        *,
        sequence_id: int,
        sequence_label: str,
        pose_source: AdvioPoseSource,
        stream: FramePacketStream,
        stop_event: Event,
    ) -> None:
        metrics = RollingRuntimeMetrics(
            fps_window_size=self.fps_window_size,
            trajectory_window_size=self.trajectory_window_size,
        )
        first_packet_timestamp_ns: int | None = None

        try:
            self._runtime.register_stream(stop_event=stop_event, stream=stream)
            stream.connect()
            self._runtime.update_fields(
                state=AdvioPreviewStreamState.STREAMING,
                sequence_id=sequence_id,
                sequence_label=sequence_label,
                pose_source=pose_source,
                error_message="",
            )
            while not stop_event.is_set():
                packet = stream.wait_for_packet(timeout_seconds=self.frame_timeout_seconds)
                if first_packet_timestamp_ns is None:
                    first_packet_timestamp_ns = packet.timestamp_ns
                camera_position = _extract_camera_position_from_pose(packet)
                metrics.record(
                    arrival_time_s=time.monotonic(),
                    position_xyz=camera_position,
                    trajectory_time_s=(
                        None
                        if first_packet_timestamp_ns is None
                        else max(packet.timestamp_ns - first_packet_timestamp_ns, 0) / 1e9
                    ),
                )
                self._runtime.update_fields(
                    state=AdvioPreviewStreamState.STREAMING,
                    sequence_id=sequence_id,
                    sequence_label=sequence_label,
                    pose_source=pose_source,
                    latest_packet=packet,
                    error_message="",
                    **metrics.snapshot_fields(),
                )
        except Exception as exc:
            if not stop_event.is_set():
                self._runtime.update_fields(
                    state=AdvioPreviewStreamState.FAILED,
                    sequence_id=sequence_id,
                    sequence_label=sequence_label,
                    pose_source=pose_source,
                    error_message=str(exc),
                )
        finally:
            self._runtime.finalize_run(
                stop_event=stop_event,
                disconnected_snapshot=lambda snapshot: _to_disconnected_snapshot(
                    snapshot,
                    streaming_state=AdvioPreviewStreamState.STREAMING,
                    disconnected_state=AdvioPreviewStreamState.DISCONNECTED,
                ),
            )


class Record3DStreamRuntimeController:
    def __init__(
        self,
        *,
        frame_timeout_seconds: float = 0.5,
        fps_window_size: int = 30,
        trajectory_window_size: int = 512,
        usb_stream_factory: Callable[[int, float], FramePacketStream] | None = None,
        wifi_stream_factory: Callable[[str, float], FramePacketStream] | None = None,
    ) -> None:
        self.frame_timeout_seconds = frame_timeout_seconds
        self.fps_window_size = fps_window_size
        self.trajectory_window_size = trajectory_window_size
        self.usb_stream_factory = usb_stream_factory or self._default_usb_stream_factory
        self.wifi_stream_factory = wifi_stream_factory or self._default_wifi_stream_factory
        self._runtime = WorkerRuntime(
            empty_snapshot=Record3DStreamSnapshot,
            stop_timeout_message="Timed out stopping the Record3D runtime worker thread.",
            disconnect_stream=lambda stream: stream.disconnect(),
        )

    def snapshot(self) -> Record3DStreamSnapshot:
        return self._runtime.snapshot()

    def start_usb(self, *, device_index: int) -> None:
        self._runtime.launch(
            connecting_snapshot=Record3DStreamSnapshot(
                transport=Record3DTransportId.USB,
                state=Record3DStreamState.CONNECTING,
                source_label=f"USB device #{device_index}",
            ),
            thread_name=f"Record3D-{Record3DTransportId.USB.value}-worker",
            worker_target=lambda stop_event: self._run_stream_worker(
                transport=Record3DTransportId.USB,
                source_descriptor=f"USB device #{device_index}",
                stop_event=stop_event,
                stream_factory=lambda: self.usb_stream_factory(device_index, self.frame_timeout_seconds),
            ),
        )

    def start_wifi(self, *, device_address: str) -> None:
        self._runtime.launch(
            connecting_snapshot=Record3DStreamSnapshot(
                transport=Record3DTransportId.WIFI,
                state=Record3DStreamState.CONNECTING,
                source_label=device_address,
            ),
            thread_name=f"Record3D-{Record3DTransportId.WIFI.value}-worker",
            worker_target=lambda stop_event: self._run_stream_worker(
                transport=Record3DTransportId.WIFI,
                source_descriptor=device_address,
                stop_event=stop_event,
                stream_factory=lambda: self.wifi_stream_factory(device_address, self.frame_timeout_seconds),
            ),
        )

    def stop(self) -> None:
        self._runtime.stop()

    def _run_stream_worker(
        self,
        *,
        transport: Record3DTransportId,
        source_descriptor: str,
        stop_event: Event,
        stream_factory: Callable[[], FramePacketStream],
    ) -> None:
        metrics = RollingRuntimeMetrics(
            fps_window_size=self.fps_window_size,
            trajectory_window_size=self.trajectory_window_size,
        )
        stream: FramePacketStream | None = None

        try:
            stream = stream_factory()
            self._runtime.register_stream(stop_event=stop_event, stream=stream)
            connected_target = stream.connect()
            source_label = self._format_source_label(
                transport=transport,
                source_descriptor=source_descriptor,
                connected_target=connected_target,
            )
            self._runtime.update_fields(
                transport=transport,
                state=Record3DStreamState.STREAMING,
                source_label=source_label,
                error_message="",
            )

            while not stop_event.is_set():
                try:
                    packet = stream.wait_for_packet(timeout_seconds=self.frame_timeout_seconds)
                except RuntimeError as exc:
                    if _is_record3d_frame_timeout(exc):
                        continue
                    raise
                arrival_time_s = packet.arrival_timestamp_s if packet.arrival_timestamp_s is not None else time.time()
                camera_position = _extract_camera_position_from_pose(packet)
                metrics.record(
                    arrival_time_s=arrival_time_s,
                    position_xyz=camera_position,
                    trajectory_time_s=arrival_time_s if camera_position is not None else None,
                )
                self._runtime.update_fields(
                    transport=transport,
                    state=Record3DStreamState.STREAMING,
                    source_label=source_label,
                    latest_packet=packet,
                    error_message="",
                    **metrics.snapshot_fields(),
                )
        except Exception as exc:
            if not stop_event.is_set():
                self._runtime.update_fields(
                    transport=transport,
                    state=Record3DStreamState.FAILED,
                    source_label=source_descriptor,
                    error_message=str(exc),
                )
        finally:
            self._runtime.finalize_run(
                stop_event=stop_event,
                disconnected_snapshot=lambda snapshot: _to_disconnected_snapshot(
                    snapshot,
                    streaming_state=Record3DStreamState.STREAMING,
                    disconnected_state=Record3DStreamState.DISCONNECTED,
                ),
            )

    @staticmethod
    def _default_usb_stream_factory(device_index: int, frame_timeout_seconds: float) -> FramePacketStream:
        stream = Record3DUSBPacketStreamConfig(
            stream=Record3DStreamConfig(
                device_index=device_index,
                frame_timeout_seconds=frame_timeout_seconds,
            )
        ).setup_target()
        if stream is None:
            raise RuntimeError("Failed to initialize the USB Record3D packet stream.")
        return stream

    @staticmethod
    def _default_wifi_stream_factory(device_address: str, frame_timeout_seconds: float) -> FramePacketStream:
        stream = Record3DWiFiStreamConfig(
            device_address=device_address,
            frame_timeout_seconds=max(1.0, frame_timeout_seconds),
            signaling_timeout_seconds=10.0,
            setup_timeout_seconds=12.0,
        ).setup_target()
        if stream is None:
            raise RuntimeError("Failed to initialize the Record3D Wi-Fi stream.")
        return stream

    @staticmethod
    def _format_source_label(
        *,
        transport: Record3DTransportId,
        source_descriptor: str,
        connected_target: Any,
    ) -> str:
        if transport is Record3DTransportId.USB and isinstance(connected_target, Record3DDevice):
            return f"{connected_target.udid} ({connected_target.product_id})"
        if hasattr(connected_target, "device_address"):
            return str(connected_target.device_address)
        return source_descriptor


__all__ = [
    "AdvioPreviewRuntimeController",
    "AdvioPreviewSnapshot",
    "AdvioPreviewStreamState",
    "Record3DAppService",
    "Record3DStreamRuntimeController",
]
