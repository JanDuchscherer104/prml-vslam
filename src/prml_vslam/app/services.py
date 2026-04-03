"""Reusable live-preview services for the packaged Streamlit app."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from enum import StrEnum
from threading import Event, Lock, Thread
from typing import Any

import numpy as np
from pydantic import Field

from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.io.interfaces import VideoFramePacket, VideoPacketStream
from prml_vslam.io.record3d import (
    Record3DConnectionError,
    Record3DDevice,
    Record3DPacketStream,
    Record3DStreamConfig,
    Record3DStreamSnapshot,
    Record3DStreamState,
    Record3DTimeoutError,
    Record3DTransportId,
    Record3DUSBPacketStreamConfig,
)
from prml_vslam.io.record3d_wifi import Record3DWiFiStreamConfig
from prml_vslam.utils import BaseData, Console


class Record3DAppService:
    """App-facing discovery helpers for Record3D transports."""

    def list_usb_devices(self) -> list[Record3DDevice]:
        """List USB-connected Record3D devices visible to the current machine."""
        stream = Record3DUSBPacketStreamConfig().setup_target()
        if stream is None:
            raise Record3DConnectionError("Failed to initialize the USB Record3D packet stream.")
        return stream.list_devices()


class AdvioPreviewStreamState(StrEnum):
    """Lifecycle states for the session-local ADVIO preview runtime."""

    IDLE = "idle"
    CONNECTING = "connecting"
    STREAMING = "streaming"
    DISCONNECTED = "disconnected"
    FAILED = "failed"


class AdvioPreviewSnapshot(BaseData):
    """Latest preview state exposed to the ADVIO Streamlit page."""

    model_config = {"arbitrary_types_allowed": True}

    state: AdvioPreviewStreamState = AdvioPreviewStreamState.IDLE
    """Current runtime state."""

    sequence_id: int | None = None
    """Active ADVIO sequence id when a preview has been started."""

    sequence_label: str = ""
    """User-facing label for the active sequence."""

    pose_source: AdvioPoseSource | None = None
    """Trajectory source currently attached to emitted packets."""

    latest_packet: VideoFramePacket | None = None
    """Most recent decoded RGB packet."""

    received_frames: int = 0
    """Total packets consumed by the current worker."""

    measured_fps: float = 0.0
    """Measured receive rate over the recent window."""

    trajectory_positions_xyz: np.ndarray = Field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))
    """Recent camera positions in meters."""

    trajectory_timestamps_s: np.ndarray = Field(default_factory=lambda: np.empty((0,), dtype=np.float64))
    """Elapsed preview timestamps aligned to `trajectory_positions_xyz`."""

    error_message: str = ""
    """Human-readable terminal error for failed preview sessions."""


class AdvioPreviewRuntimeController:
    """Own the looped ADVIO preview worker thread for one Streamlit browser session."""

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
        self.console = Console(__name__).child(self.__class__.__name__)
        self._lock = Lock()
        self._snapshot = AdvioPreviewSnapshot()
        self._active_stream: VideoPacketStream | None = None
        self._active_stop_event: Event | None = None
        self._worker_thread: Thread | None = None

    def snapshot(self) -> AdvioPreviewSnapshot:
        """Return a copy of the latest ADVIO preview snapshot."""
        with self._lock:
            return self._snapshot.model_copy(deep=True)

    def start(
        self,
        *,
        sequence_id: int,
        sequence_label: str,
        pose_source: AdvioPoseSource,
        stream: VideoPacketStream,
    ) -> None:
        """Start one ADVIO preview worker from a prepared packet stream."""
        self.stop()
        stop_event = Event()
        worker = Thread(
            target=self._run_stream_worker,
            kwargs={
                "sequence_id": sequence_id,
                "sequence_label": sequence_label,
                "pose_source": pose_source,
                "stream": stream,
                "stop_event": stop_event,
            },
            name=f"ADVIO-preview-{sequence_id:02d}",
            daemon=True,
        )
        with self._lock:
            self._active_stream = stream
            self._active_stop_event = stop_event
            self._worker_thread = worker
            self._snapshot = AdvioPreviewSnapshot(
                state=AdvioPreviewStreamState.CONNECTING,
                sequence_id=sequence_id,
                sequence_label=sequence_label,
                pose_source=pose_source,
            )
        worker.start()

    def stop(self) -> None:
        """Stop the active ADVIO preview worker and clear the snapshot."""
        with self._lock:
            worker = self._worker_thread
            stop_event = self._active_stop_event

        if stop_event is not None:
            stop_event.set()
        if worker is not None:
            worker.join(timeout=2.0)
            if worker.is_alive():
                raise RuntimeError("Timed out stopping the ADVIO preview worker thread.")

        with self._lock:
            self._active_stream = None
            self._active_stop_event = None
            self._worker_thread = None
            self._snapshot = AdvioPreviewSnapshot()

    def _run_stream_worker(
        self,
        *,
        sequence_id: int,
        sequence_label: str,
        pose_source: AdvioPoseSource,
        stream: VideoPacketStream,
        stop_event: Event,
    ) -> None:
        frames_received = 0
        arrival_times: deque[float] = deque(maxlen=self.fps_window_size)
        trajectory_positions: deque[np.ndarray] = deque(maxlen=self.trajectory_window_size)
        trajectory_timestamps: deque[float] = deque(maxlen=self.trajectory_window_size)
        first_packet_timestamp_ns: int | None = None

        try:
            stream.connect()
            self._update_snapshot(
                state=AdvioPreviewStreamState.STREAMING,
                sequence_id=sequence_id,
                sequence_label=sequence_label,
                pose_source=pose_source,
                error_message="",
            )
            while not stop_event.is_set():
                packet = stream.wait_for_packet(timeout_seconds=self.frame_timeout_seconds)
                frames_received += 1
                arrival_times.append(time.monotonic())
                if first_packet_timestamp_ns is None:
                    first_packet_timestamp_ns = packet.timestamp_ns
                camera_position = self._extract_camera_position(packet)
                if camera_position is not None and first_packet_timestamp_ns is not None:
                    trajectory_positions.append(camera_position)
                    trajectory_timestamps.append(max(packet.timestamp_ns - first_packet_timestamp_ns, 0) / 1e9)
                self._update_snapshot(
                    state=AdvioPreviewStreamState.STREAMING,
                    sequence_id=sequence_id,
                    sequence_label=sequence_label,
                    pose_source=pose_source,
                    latest_packet=packet,
                    received_frames=frames_received,
                    measured_fps=self._measure_fps(arrival_times),
                    trajectory_positions_xyz=self._to_positions_array(trajectory_positions),
                    trajectory_timestamps_s=np.asarray(tuple(trajectory_timestamps), dtype=np.float64),
                    error_message="",
                )
        except Exception as exc:
            if not stop_event.is_set():
                self._update_snapshot(
                    state=AdvioPreviewStreamState.FAILED,
                    sequence_id=sequence_id,
                    sequence_label=sequence_label,
                    pose_source=pose_source,
                    error_message=str(exc),
                )
        finally:
            stream.disconnect()
            with self._lock:
                if self._active_stop_event is stop_event:
                    self._active_stream = None
                    self._active_stop_event = None
                    self._worker_thread = None
                if stop_event.is_set():
                    self._snapshot = AdvioPreviewSnapshot()
                elif self._snapshot.state is AdvioPreviewStreamState.STREAMING:
                    self._snapshot = self._snapshot.model_copy(
                        update={
                            "state": AdvioPreviewStreamState.DISCONNECTED,
                            "latest_packet": None,
                            "received_frames": 0,
                            "measured_fps": 0.0,
                        }
                    )

    def _update_snapshot(
        self,
        *,
        state: AdvioPreviewStreamState,
        sequence_id: int | None,
        sequence_label: str,
        pose_source: AdvioPoseSource | None,
        latest_packet: VideoFramePacket | None = None,
        received_frames: int = 0,
        measured_fps: float = 0.0,
        trajectory_positions_xyz: np.ndarray | None = None,
        trajectory_timestamps_s: np.ndarray | None = None,
        error_message: str = "",
    ) -> None:
        with self._lock:
            self._snapshot = AdvioPreviewSnapshot(
                state=state,
                sequence_id=sequence_id,
                sequence_label=sequence_label,
                pose_source=pose_source,
                latest_packet=latest_packet,
                received_frames=received_frames,
                measured_fps=measured_fps,
                trajectory_positions_xyz=(
                    np.empty((0, 3), dtype=np.float64) if trajectory_positions_xyz is None else trajectory_positions_xyz
                ),
                trajectory_timestamps_s=(
                    np.empty((0,), dtype=np.float64) if trajectory_timestamps_s is None else trajectory_timestamps_s
                ),
                error_message=error_message,
            )

    @staticmethod
    def _measure_fps(arrival_times: deque[float]) -> float:
        if len(arrival_times) < 2:
            return 0.0
        elapsed = arrival_times[-1] - arrival_times[0]
        if elapsed <= 0.0:
            return 0.0
        return float((len(arrival_times) - 1) / elapsed)

    @staticmethod
    def _extract_camera_position(packet: VideoFramePacket) -> np.ndarray | None:
        if packet.camera_pose is None:
            return None
        position = np.array(
            [packet.camera_pose.tx, packet.camera_pose.ty, packet.camera_pose.tz],
            dtype=np.float64,
        )
        if not np.all(np.isfinite(position)):
            return None
        return position

    @staticmethod
    def _to_positions_array(positions: deque[np.ndarray]) -> np.ndarray:
        if not positions:
            return np.empty((0, 3), dtype=np.float64)
        return np.vstack(tuple(positions)).astype(np.float64, copy=False)


class Record3DStreamRuntimeController:
    """Own the live Record3D reader thread for one Streamlit browser session."""

    def __init__(
        self,
        *,
        frame_timeout_seconds: float = 0.5,
        fps_window_size: int = 30,
        trajectory_window_size: int = 512,
        usb_stream_factory: Callable[[int, float], Record3DPacketStream] | None = None,
        wifi_stream_factory: Callable[[str, float], Record3DPacketStream] | None = None,
    ) -> None:
        self.frame_timeout_seconds = frame_timeout_seconds
        self.fps_window_size = fps_window_size
        self.trajectory_window_size = trajectory_window_size
        self.usb_stream_factory = usb_stream_factory or self._default_usb_stream_factory
        self.wifi_stream_factory = wifi_stream_factory or self._default_wifi_stream_factory
        self.console = Console(__name__).child(self.__class__.__name__)
        self._lock = Lock()
        self._snapshot = Record3DStreamSnapshot()
        self._active_stream: Record3DPacketStream | None = None
        self._active_stop_event: Event | None = None
        self._worker_thread: Thread | None = None

    def snapshot(self) -> Record3DStreamSnapshot:
        """Return a copy of the latest live-stream snapshot."""
        with self._lock:
            return self._snapshot.model_copy(deep=True)

    def start_usb(self, *, device_index: int) -> None:
        """Start a USB-backed live Record3D reader thread."""
        self._start_worker(
            transport=Record3DTransportId.USB,
            source_descriptor=f"USB device #{device_index}",
            stream_factory=lambda: self.usb_stream_factory(device_index, self.frame_timeout_seconds),
        )

    def start_wifi(self, *, device_address: str) -> None:
        """Start a Wi-Fi-backed live Record3D reader thread."""
        self._start_worker(
            transport=Record3DTransportId.WIFI,
            source_descriptor=device_address,
            stream_factory=lambda: self.wifi_stream_factory(device_address, self.frame_timeout_seconds),
        )

    def stop(self) -> None:
        """Stop the active reader thread and clear the live snapshot."""
        with self._lock:
            worker = self._worker_thread
            stream = self._active_stream
            stop_event = self._active_stop_event

        if stop_event is not None:
            stop_event.set()
        if stream is not None:
            stream.disconnect()
        if worker is not None:
            worker.join(timeout=2.0)
            if worker.is_alive():
                raise RuntimeError("Timed out stopping the Record3D runtime worker thread.")

        with self._lock:
            self._active_stream = None
            self._active_stop_event = None
            self._worker_thread = None
            self._snapshot = Record3DStreamSnapshot()

    def _start_worker(
        self,
        *,
        transport: Record3DTransportId,
        source_descriptor: str,
        stream_factory: Callable[[], Record3DPacketStream],
    ) -> None:
        self.stop()
        stop_event = Event()
        worker = Thread(
            target=self._run_stream_worker,
            kwargs={
                "transport": transport,
                "source_descriptor": source_descriptor,
                "stop_event": stop_event,
                "stream_factory": stream_factory,
            },
            name=f"Record3D-{transport.value}-worker",
            daemon=True,
        )
        with self._lock:
            self._active_stop_event = stop_event
            self._worker_thread = worker
            self._snapshot = Record3DStreamSnapshot(
                transport=transport,
                state=Record3DStreamState.CONNECTING,
                source_label=source_descriptor,
            )
        worker.start()

    def _run_stream_worker(
        self,
        *,
        transport: Record3DTransportId,
        source_descriptor: str,
        stop_event: Event,
        stream_factory: Callable[[], Record3DPacketStream],
    ) -> None:
        frames_received = 0
        arrival_times: deque[float] = deque(maxlen=self.fps_window_size)
        trajectory_positions: deque[np.ndarray] = deque(maxlen=self.trajectory_window_size)
        trajectory_timestamps: deque[float] = deque(maxlen=self.trajectory_window_size)
        stream: Record3DPacketStream | None = None

        try:
            stream = stream_factory()
            with self._lock:
                self._active_stream = stream
            connected_target = stream.connect()
            source_label = self._format_source_label(
                transport=transport,
                source_descriptor=source_descriptor,
                connected_target=connected_target,
            )
            self._update_snapshot(
                transport=transport,
                state=Record3DStreamState.STREAMING,
                source_label=source_label,
                error_message="",
            )

            while not stop_event.is_set():
                try:
                    packet = stream.wait_for_packet(timeout_seconds=self.frame_timeout_seconds)
                except Record3DTimeoutError:
                    continue
                frames_received += 1
                arrival_times.append(packet.arrival_timestamp_s)
                camera_position = self._extract_camera_position(packet)
                if camera_position is not None:
                    trajectory_positions.append(camera_position)
                    trajectory_timestamps.append(packet.arrival_timestamp_s)
                self._update_snapshot(
                    transport=transport,
                    state=Record3DStreamState.STREAMING,
                    source_label=source_label,
                    latest_packet=packet,
                    received_frames=frames_received,
                    measured_fps=self._measure_fps(arrival_times),
                    trajectory_positions_xyz=self._to_positions_array(trajectory_positions),
                    trajectory_timestamps_s=np.asarray(tuple(trajectory_timestamps), dtype=np.float64),
                    error_message="",
                )
        except Exception as exc:
            if not stop_event.is_set():
                self._update_snapshot(
                    transport=transport,
                    state=Record3DStreamState.FAILED,
                    source_label=source_descriptor,
                    error_message=str(exc),
                )
        finally:
            if stream is not None:
                stream.disconnect()
            with self._lock:
                if self._active_stop_event is stop_event:
                    self._active_stream = None
                    self._active_stop_event = None
                    self._worker_thread = None
                if stop_event.is_set():
                    self._snapshot = Record3DStreamSnapshot()
                elif self._snapshot.state is Record3DStreamState.STREAMING:
                    self._snapshot = self._snapshot.model_copy(
                        update={
                            "state": Record3DStreamState.DISCONNECTED,
                            "latest_packet": None,
                            "received_frames": 0,
                            "measured_fps": 0.0,
                        }
                    )

    def _update_snapshot(
        self,
        *,
        transport: Record3DTransportId,
        state: Record3DStreamState,
        source_label: str,
        latest_packet: Any | None = None,
        received_frames: int = 0,
        measured_fps: float = 0.0,
        trajectory_positions_xyz: np.ndarray | None = None,
        trajectory_timestamps_s: np.ndarray | None = None,
        error_message: str = "",
    ) -> None:
        with self._lock:
            self._snapshot = Record3DStreamSnapshot(
                transport=transport,
                state=state,
                source_label=source_label,
                latest_packet=latest_packet,
                received_frames=received_frames,
                measured_fps=measured_fps,
                trajectory_positions_xyz=(
                    np.empty((0, 3), dtype=np.float64) if trajectory_positions_xyz is None else trajectory_positions_xyz
                ),
                trajectory_timestamps_s=(
                    np.empty((0,), dtype=np.float64) if trajectory_timestamps_s is None else trajectory_timestamps_s
                ),
                error_message=error_message,
            )

    @staticmethod
    def _default_usb_stream_factory(device_index: int, frame_timeout_seconds: float) -> Record3DPacketStream:
        stream = Record3DUSBPacketStreamConfig(
            stream=Record3DStreamConfig(
                device_index=device_index,
                frame_timeout_seconds=frame_timeout_seconds,
            )
        ).setup_target()
        if stream is None:
            raise Record3DConnectionError("Failed to initialize the USB Record3D packet stream.")
        return stream

    @staticmethod
    def _default_wifi_stream_factory(device_address: str, frame_timeout_seconds: float) -> Record3DPacketStream:
        stream = Record3DWiFiStreamConfig(
            device_address=device_address,
            frame_timeout_seconds=max(1.0, frame_timeout_seconds),
            signaling_timeout_seconds=10.0,
            setup_timeout_seconds=12.0,
        ).setup_target()
        if stream is None:
            raise Record3DConnectionError("Failed to initialize the Record3D Wi-Fi stream.")
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

    @staticmethod
    def _measure_fps(arrival_times: deque[float]) -> float:
        if len(arrival_times) < 2:
            return 0.0
        elapsed = arrival_times[-1] - arrival_times[0]
        if elapsed <= 0.0:
            return 0.0
        return float((len(arrival_times) - 1) / elapsed)

    @staticmethod
    def _extract_camera_position(packet: Any) -> np.ndarray | None:
        camera_pose = getattr(packet, "metadata", {}).get("camera_pose")
        if not isinstance(camera_pose, dict):
            return None
        try:
            position = np.array(
                [
                    float(camera_pose["tx"]),
                    float(camera_pose["ty"]),
                    float(camera_pose["tz"]),
                ],
                dtype=np.float64,
            )
        except (KeyError, TypeError, ValueError):
            return None
        if not np.all(np.isfinite(position)):
            return None
        return position

    @staticmethod
    def _to_positions_array(positions: deque[np.ndarray]) -> np.ndarray:
        if not positions:
            return np.empty((0, 3), dtype=np.float64)
        return np.vstack(tuple(positions)).astype(np.float64, copy=False)


__all__ = [
    "AdvioPreviewRuntimeController",
    "AdvioPreviewSnapshot",
    "AdvioPreviewStreamState",
    "Record3DAppService",
    "Record3DStreamRuntimeController",
]
