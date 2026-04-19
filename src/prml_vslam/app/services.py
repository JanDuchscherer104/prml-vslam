"""Reusable live-preview services for the packaged Streamlit app. Every component of the app must define its own service layer derived from shared service interfaces / protocols."""

from __future__ import annotations

import time
from collections.abc import Callable
from threading import Event

from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.io.record3d import (
    Record3DDevice,
    Record3DTransportId,
    open_record3d_usb_packet_stream,
)
from prml_vslam.io.wifi_packets import Record3DWiFiMetadata
from prml_vslam.io.wifi_session import open_record3d_wifi_preview_stream
from prml_vslam.protocols import FramePacketStream

from .models import (
    AdvioPreviewSnapshot,
    PreviewStreamState,
    Record3DStreamSnapshot,
)
from .preview_runtime import PacketSessionMetrics, PacketSessionRuntime, extract_pose_position


def _is_record3d_frame_timeout(error: RuntimeError) -> bool:
    message = str(error)
    return message.startswith("Timed out waiting ") and "Record3D" in message and " frame." in message


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
        metrics = PacketSessionMetrics(
            fps_window_size=self.fps_window_size,
            trajectory_window_size=self.trajectory_window_size,
        )
        first_packet_timestamp_ns: int | None = None

        def _consume_packet(active_stream: FramePacketStream) -> None:
            nonlocal first_packet_timestamp_ns
            packet = active_stream.wait_for_packet(timeout_seconds=self.frame_timeout_seconds)
            if first_packet_timestamp_ns is None:
                first_packet_timestamp_ns = packet.timestamp_ns
            camera_position = extract_pose_position(packet)
            metrics.record(
                arrival_time_s=time.monotonic(),
                position_xyz=camera_position,
                trajectory_time_s=(
                    None
                    if first_packet_timestamp_ns is None
                    else max(packet.timestamp_ns - first_packet_timestamp_ns, 0) / 1e9
                ),
            )
            self.update_snapshot(
                lambda snapshot: snapshot.model_copy(
                    update={
                        "state": PreviewStreamState.STREAMING,
                        "sequence_id": sequence_id,
                        "sequence_label": sequence_label,
                        "pose_source": pose_source,
                        "latest_packet": packet,
                        "error_message": "",
                        **metrics.snapshot_fields(),
                    }
                )
            )

        try:
            self.register_stream(stop_event=stop_event, stream=stream)
            stream.connect()
            (
                self.update_snapshot(
                    lambda snapshot: snapshot.model_copy(
                        update={
                            "state": PreviewStreamState.STREAMING,
                            "sequence_id": sequence_id,
                            "sequence_label": sequence_label,
                            "pose_source": pose_source,
                            "error_message": "",
                        }
                    )
                ),
            )
            while not stop_event.is_set():
                _consume_packet(stream)
        except Exception as exc:
            if not stop_event.is_set():
                error_message = str(exc)
                self.update_snapshot(
                    lambda snapshot: snapshot.model_copy(
                        update={
                            "state": PreviewStreamState.FAILED,
                            "sequence_id": sequence_id,
                            "sequence_label": sequence_label,
                            "pose_source": pose_source,
                            "error_message": error_message,
                        }
                    )
                )
        finally:
            self.finalize(
                stop_event=stop_event,
                snapshot_update=lambda snapshot: (
                    AdvioPreviewSnapshot()
                    if stop_event.is_set()
                    else snapshot.model_copy(
                        update={
                            "state": (
                                PreviewStreamState.DISCONNECTED
                                if snapshot.state is PreviewStreamState.STREAMING
                                else snapshot.state
                            ),
                            "latest_packet": None,
                            "received_frames": 0,
                            "measured_fps": 0.0,
                        }
                    )
                ),
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
            lambda device_address, timeout_seconds: open_record3d_wifi_preview_stream(
                device_address=device_address,
                frame_timeout_seconds=timeout_seconds,
            )
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
        metrics = PacketSessionMetrics(
            fps_window_size=self.fps_window_size,
            trajectory_window_size=self.trajectory_window_size,
        )
        source_label = source_descriptor

        def _consume_packet(active_stream: FramePacketStream) -> None:
            try:
                packet = active_stream.wait_for_packet(timeout_seconds=self.frame_timeout_seconds)
            except RuntimeError as exc:
                if _is_record3d_frame_timeout(exc):
                    return
                raise
            arrival_time_s = packet.arrival_timestamp_s if packet.arrival_timestamp_s is not None else time.time()
            camera_position = extract_pose_position(packet)
            metrics.record(
                arrival_time_s=arrival_time_s,
                position_xyz=camera_position,
                trajectory_time_s=arrival_time_s if camera_position is not None else None,
            )
            self.update_snapshot(
                lambda snapshot: snapshot.model_copy(
                    update={
                        "transport": transport,
                        "state": PreviewStreamState.STREAMING,
                        "source_label": source_label,
                        "latest_packet": packet,
                        "error_message": "",
                        **metrics.snapshot_fields(),
                    }
                )
            )

        try:
            stream = stream_factory()
            self.register_stream(stop_event=stop_event, stream=stream)
            connected_target = stream.connect()
            source_label = self._format_source_label(
                transport=transport,
                source_descriptor=source_descriptor,
                connected_target=connected_target,
            )
            self.update_snapshot(
                lambda snapshot: snapshot.model_copy(
                    update={
                        "transport": transport,
                        "state": PreviewStreamState.STREAMING,
                        "source_label": source_label,
                        "error_message": "",
                    }
                )
            )
            while not stop_event.is_set():
                _consume_packet(stream)
        except Exception as exc:
            if not stop_event.is_set():
                error_message = str(exc)
                self.update_snapshot(
                    lambda snapshot: snapshot.model_copy(
                        update={
                            "transport": transport,
                            "state": PreviewStreamState.FAILED,
                            "source_label": source_descriptor,
                            "error_message": error_message,
                        }
                    )
                )
        finally:
            self.finalize(
                stop_event=stop_event,
                snapshot_update=lambda snapshot: (
                    Record3DStreamSnapshot()
                    if stop_event.is_set()
                    else snapshot.model_copy(
                        update={
                            "state": (
                                PreviewStreamState.DISCONNECTED
                                if snapshot.state is PreviewStreamState.STREAMING
                                else snapshot.state
                            ),
                            "latest_packet": None,
                            "received_frames": 0,
                            "measured_fps": 0.0,
                        }
                    )
                ),
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
