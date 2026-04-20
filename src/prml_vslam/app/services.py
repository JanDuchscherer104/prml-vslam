"""Reusable live-preview services for the packaged Streamlit app. Every component of the app must define its own service layer derived from shared service interfaces / protocols."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event
from typing import TypeVar

from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.interfaces import FramePacket
from prml_vslam.io.record3d import (
    Record3DDevice,
    Record3DTransportId,
    open_record3d_usb_packet_stream,
)
from prml_vslam.io.wifi_packets import Record3DWiFiMetadata
from prml_vslam.io.wifi_session import Record3DWiFiPreviewStreamConfig
from prml_vslam.protocols import FramePacketStream

from .models import (
    AdvioPreviewSnapshot,
    PreviewSessionSnapshot,
    PreviewStreamState,
    Record3DStreamSnapshot,
)
from .preview_runtime import PacketSessionMetrics, PacketSessionRuntime, extract_pose_position

SnapshotT = TypeVar("SnapshotT", bound=PreviewSessionSnapshot)


@dataclass(frozen=True, slots=True)
class _PacketObservation:
    """One packet plus the timing metadata needed by shared preview metrics."""

    packet: FramePacket
    arrival_time_s: float
    trajectory_time_s: float | None


def _disconnect_snapshot(snapshot: SnapshotT) -> SnapshotT:
    """Drop live packet fields while preserving the last non-live session summary."""
    return snapshot.model_copy(
        update={
            "state": PreviewStreamState.DISCONNECTED
            if snapshot.state is PreviewStreamState.STREAMING
            else snapshot.state,
            "latest_packet": None,
            "received_frames": 0,
            "measured_fps": 0.0,
        }
    )


def _run_packet_stream_worker(
    runtime: PacketSessionRuntime[SnapshotT],
    *,
    stop_event: Event,
    stream_factory: Callable[[], FramePacketStream],
    fps_window_size: int,
    trajectory_window_size: int,
    connect_snapshot: Callable[[SnapshotT, FramePacketStream], SnapshotT],
    read_observation: Callable[[FramePacketStream], _PacketObservation | None],
    streaming_snapshot: Callable[[SnapshotT, _PacketObservation, PacketSessionMetrics], SnapshotT],
    failure_snapshot: Callable[[SnapshotT, str], SnapshotT],
    empty_snapshot: Callable[[], SnapshotT],
) -> None:
    """Run the shared threaded preview loop used by app-owned packet consumers."""
    metrics = PacketSessionMetrics(
        fps_window_size=fps_window_size,
        trajectory_window_size=trajectory_window_size,
    )
    try:
        stream = stream_factory()
        runtime.register_stream(stop_event=stop_event, stream=stream)
        runtime.update_snapshot(lambda snapshot: connect_snapshot(snapshot, stream))
        while not stop_event.is_set():
            observation = read_observation(stream)
            if observation is None:
                continue
            metrics.record(
                arrival_time_s=observation.arrival_time_s,
                position_xyz=extract_pose_position(observation.packet),
                trajectory_time_s=observation.trajectory_time_s,
            )
            runtime.update_snapshot(
                lambda snapshot, observation=observation: streaming_snapshot(snapshot, observation, metrics)
            )
    except Exception as exc:
        if not stop_event.is_set():
            error_message = str(exc)
            runtime.update_snapshot(
                lambda snapshot, error_message=error_message: failure_snapshot(snapshot, error_message)
            )
    finally:
        runtime.finalize(
            stop_event=stop_event,
            snapshot_update=lambda snapshot: empty_snapshot()
            if stop_event.is_set()
            else _disconnect_snapshot(snapshot),
        )


class AdvioPreviewRuntimeController(PacketSessionRuntime[AdvioPreviewSnapshot]):
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
        super().__init__(
            empty_snapshot=AdvioPreviewSnapshot,
            stop_timeout_message="Timed out stopping the ADVIO preview worker thread.",
        )

    def start(
        self,
        *,
        sequence_id: int,
        sequence_label: str,
        pose_source: AdvioPoseSource,
        stream: FramePacketStream,
    ) -> None:
        self.launch(
            connecting_snapshot=AdvioPreviewSnapshot(
                state=PreviewStreamState.CONNECTING,
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

    def _run_stream_worker(
        self,
        *,
        sequence_id: int,
        sequence_label: str,
        pose_source: AdvioPoseSource,
        stream: FramePacketStream,
        stop_event: Event,
    ) -> None:
        first_packet_timestamp_ns: int | None = None

        def _connect_snapshot(snapshot: AdvioPreviewSnapshot, active_stream: FramePacketStream) -> AdvioPreviewSnapshot:
            active_stream.connect()
            return snapshot.model_copy(
                update={
                    "state": PreviewStreamState.STREAMING,
                    "sequence_id": sequence_id,
                    "sequence_label": sequence_label,
                    "pose_source": pose_source,
                    "error_message": "",
                }
            )

        def _read_observation(active_stream: FramePacketStream) -> _PacketObservation:
            nonlocal first_packet_timestamp_ns
            packet = active_stream.wait_for_packet(timeout_seconds=self.frame_timeout_seconds)
            if first_packet_timestamp_ns is None:
                first_packet_timestamp_ns = packet.timestamp_ns
            return _PacketObservation(
                packet=packet,
                arrival_time_s=time.monotonic(),
                trajectory_time_s=max(packet.timestamp_ns - first_packet_timestamp_ns, 0) / 1e9,
            )

        def _streaming_snapshot(
            snapshot: AdvioPreviewSnapshot,
            observation: _PacketObservation,
            metrics: PacketSessionMetrics,
        ) -> AdvioPreviewSnapshot:
            return snapshot.model_copy(
                update={
                    "state": PreviewStreamState.STREAMING,
                    "sequence_id": sequence_id,
                    "sequence_label": sequence_label,
                    "pose_source": pose_source,
                    "latest_packet": observation.packet,
                    "error_message": "",
                    **metrics.snapshot_fields(),
                }
            )

        def _failure_snapshot(snapshot: AdvioPreviewSnapshot, error_message: str) -> AdvioPreviewSnapshot:
            return snapshot.model_copy(
                update={
                    "state": PreviewStreamState.FAILED,
                    "sequence_id": sequence_id,
                    "sequence_label": sequence_label,
                    "pose_source": pose_source,
                    "error_message": error_message,
                }
            )

        _run_packet_stream_worker(
            self,
            stop_event=stop_event,
            stream_factory=lambda: stream,
            fps_window_size=self.fps_window_size,
            trajectory_window_size=self.trajectory_window_size,
            connect_snapshot=_connect_snapshot,
            read_observation=_read_observation,
            streaming_snapshot=_streaming_snapshot,
            failure_snapshot=_failure_snapshot,
            empty_snapshot=AdvioPreviewSnapshot,
        )


class Record3DStreamRuntimeController(PacketSessionRuntime[Record3DStreamSnapshot]):
    def __init__(
        self,
        *,
        frame_timeout_seconds: float = 0.5,
        fps_window_size: int = 30,
        trajectory_window_size: int = 512,
        usb_stream_factory: Callable[[int, float], FramePacketStream] | None = None,
        wifi_preview_stream_factory: Callable[[str, float], FramePacketStream] | None = None,
    ) -> None:
        self.frame_timeout_seconds = frame_timeout_seconds
        self.fps_window_size = fps_window_size
        self.trajectory_window_size = trajectory_window_size
        self.usb_stream_factory = usb_stream_factory or (
            lambda device_index, timeout_seconds: open_record3d_usb_packet_stream(
                device_index=device_index,
                frame_timeout_seconds=timeout_seconds,
            )
        )
        self.wifi_preview_stream_factory = wifi_preview_stream_factory or (
            lambda device_address, timeout_seconds: Record3DWiFiPreviewStreamConfig(
                device_address=device_address,
                frame_timeout_seconds=max(1.0, timeout_seconds),
                signaling_timeout_seconds=10.0,
                setup_timeout_seconds=12.0,
            ).setup_target()
        )
        super().__init__(
            empty_snapshot=Record3DStreamSnapshot,
            stop_timeout_message="Timed out stopping the Record3D runtime worker thread.",
        )

    def start_usb(self, *, device_index: int) -> None:
        self.launch(
            connecting_snapshot=Record3DStreamSnapshot(
                transport=Record3DTransportId.USB,
                state=PreviewStreamState.CONNECTING,
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

    def start_wifi_preview(self, *, device_address: str) -> None:
        self.launch(
            connecting_snapshot=Record3DStreamSnapshot(
                transport=Record3DTransportId.WIFI,
                state=PreviewStreamState.CONNECTING,
                source_label=device_address,
            ),
            thread_name=f"Record3D-{Record3DTransportId.WIFI.value}-worker",
            worker_target=lambda stop_event: self._run_stream_worker(
                transport=Record3DTransportId.WIFI,
                source_descriptor=device_address,
                stop_event=stop_event,
                stream_factory=lambda: self.wifi_preview_stream_factory(device_address, self.frame_timeout_seconds),
            ),
        )

    def _run_stream_worker(
        self,
        *,
        transport: Record3DTransportId,
        source_descriptor: str,
        stop_event: Event,
        stream_factory: Callable[[], FramePacketStream],
    ) -> None:
        def _connect_snapshot(
            snapshot: Record3DStreamSnapshot,
            active_stream: FramePacketStream,
        ) -> Record3DStreamSnapshot:
            connected_target = active_stream.connect()
            return snapshot.model_copy(
                update={
                    "transport": transport,
                    "state": PreviewStreamState.STREAMING,
                    "source_label": self._format_source_label(
                        transport=transport,
                        source_descriptor=source_descriptor,
                        connected_target=connected_target,
                    ),
                    "error_message": "",
                }
            )

        def _read_observation(active_stream: FramePacketStream) -> _PacketObservation | None:
            try:
                packet = active_stream.wait_for_packet(timeout_seconds=self.frame_timeout_seconds)
            except RuntimeError as exc:
                message = str(exc)
                if message.startswith("Timed out waiting ") and "Record3D" in message and " frame." in message:
                    return
                raise
            arrival_time_s = packet.arrival_timestamp_s if packet.arrival_timestamp_s is not None else time.time()
            trajectory_time_s = arrival_time_s if extract_pose_position(packet) is not None else None
            return _PacketObservation(
                packet=packet,
                arrival_time_s=arrival_time_s,
                trajectory_time_s=trajectory_time_s,
            )

        def _streaming_snapshot(
            snapshot: Record3DStreamSnapshot,
            observation: _PacketObservation,
            metrics: PacketSessionMetrics,
        ) -> Record3DStreamSnapshot:
            return snapshot.model_copy(
                update={
                    "transport": transport,
                    "state": PreviewStreamState.STREAMING,
                    "source_label": snapshot.source_label or source_descriptor,
                    "latest_packet": observation.packet,
                    "error_message": "",
                    **metrics.snapshot_fields(),
                }
            )

        def _failure_snapshot(snapshot: Record3DStreamSnapshot, error_message: str) -> Record3DStreamSnapshot:
            return snapshot.model_copy(
                update={
                    "transport": transport,
                    "state": PreviewStreamState.FAILED,
                    "source_label": source_descriptor,
                    "error_message": error_message,
                }
            )

        _run_packet_stream_worker(
            self,
            stop_event=stop_event,
            stream_factory=stream_factory,
            fps_window_size=self.fps_window_size,
            trajectory_window_size=self.trajectory_window_size,
            connect_snapshot=_connect_snapshot,
            read_observation=_read_observation,
            streaming_snapshot=_streaming_snapshot,
            failure_snapshot=_failure_snapshot,
            empty_snapshot=Record3DStreamSnapshot,
        )

    @staticmethod
    def _format_source_label(
        *,
        transport: Record3DTransportId,
        source_descriptor: str,
        connected_target: Record3DDevice | Record3DWiFiMetadata | None,
    ) -> str:
        if transport is Record3DTransportId.USB and isinstance(connected_target, Record3DDevice):
            return f"{connected_target.udid} ({connected_target.product_id})"
        if transport is Record3DTransportId.WIFI and isinstance(connected_target, Record3DWiFiMetadata):
            return connected_target.device_address
        return source_descriptor


__all__ = [
    "AdvioPreviewRuntimeController",
    "Record3DStreamRuntimeController",
]
