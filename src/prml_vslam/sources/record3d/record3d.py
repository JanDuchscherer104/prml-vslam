"""Record3D USB streaming integration for shared source observations.

This module owns the stable USB-backed Record3D ingress path. It turns the
upstream native bindings into normalized source observations.
"""

from __future__ import annotations

import importlib
import time
from collections.abc import Iterator
from enum import IntEnum
from threading import Event
from typing import Any

import numpy as np

from prml_vslam.interfaces import (
    CAMERA_RDF_FRAME,
    CameraIntrinsics,
    FrameTransform,
    Observation,
    ObservationProvenance,
)
from prml_vslam.sources.contracts import Record3DTransportId
from prml_vslam.utils import BaseConfig, BaseData, Console, FactoryConfig


class Record3DDeviceType(IntEnum):
    """Name the device classes exposed by the upstream Record3D bindings."""

    TRUEDEPTH = 0
    LIDAR = 1


class Record3DDevice(BaseData):
    """Describe one USB-connected Record3D device discovered through the bindings."""

    product_id: int
    """Apple product identifier reported by the device."""

    udid: str
    """Unique device identifier reported by the bindings."""


def _import_record3d_module() -> Any:
    """Import the optional native Record3D bindings."""
    try:
        return importlib.import_module("record3d")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The optional `record3d` package is required for streaming. "
            "Install it with `uv sync --extra streaming` and make sure the upstream prerequisites are installed "
            "(CMake, iTunes on macOS/Windows, or libusbmuxd on Linux)."
        ) from exc


class Record3DStreamConfig(BaseConfig, FactoryConfig["Record3DUSBPacketStream"]):
    """Configure one USB Record3D packet stream."""

    device_index: int = 0
    """Zero-based index into the list of connected Record3D devices."""

    frame_timeout_seconds: float = 5.0
    """Maximum time to wait for the next frame before failing."""

    @property
    def target_type(self) -> type[Record3DUSBPacketStream]:
        """Runtime type that exposes shared packet objects."""
        return Record3DUSBPacketStream


class Record3DUSBPacketStream:
    """Adapt the upstream USB stream to the shared packet-stream contract."""

    def __init__(self, config: Record3DStreamConfig) -> None:
        self.config = config
        self.console = Console(__name__).child(self.__class__.__name__)
        self._record3d = _import_record3d_module()
        self._event = Event()
        self._stream: Any | None = None
        self._stream_stopped = False
        self._observation_seq = 0

    def list_devices(self) -> list[Record3DDevice]:
        """List the currently connected USB Record3D devices."""
        return [self._device_from_binding(device) for device in self._get_connected_devices()]

    def connect(self) -> Record3DDevice:
        """Connect to the configured USB device and return its normalized device metadata."""
        devices = self._get_connected_devices()
        if not devices:
            raise RuntimeError(
                "No Record3D devices detected. Connect the iPhone via USB, open the Record3D app, "
                "and enable USB Streaming mode."
            )
        if self.config.device_index >= len(devices):
            raise RuntimeError(
                f"Configured device index {self.config.device_index} is out of range for {len(devices)} connected device(s)."
            )

        if self._stream is not None:
            self.disconnect()

        target_device = devices[self.config.device_index]
        stream = self._record3d.Record3DStream()
        stream.on_new_frame = self._on_new_frame
        stream.on_stream_stopped = self._on_stream_stopped
        self._event.clear()
        if not stream.connect(target_device):
            raise RuntimeError(f"Failed to connect to Record3D device at index {self.config.device_index}.")

        self._stream = stream
        self._stream_stopped = False
        self._observation_seq = 0
        device = self._device_from_binding(target_device)
        self.console.info("Connected to Record3D device %s (%s).", device.udid, device.product_id)
        return device

    def disconnect(self) -> None:
        """Disconnect the current USB device if one is active."""
        if self._stream is None:
            return

        self._stream.disconnect()
        self._stream = None
        self._stream_stopped = True
        self._event.clear()
        self._observation_seq = 0

    def wait_for_observation(self, timeout_seconds: float | None = None) -> Observation:
        """Wait for the next shared observation emitted by the USB device."""
        stream = self._require_stream()
        timeout = self.config.frame_timeout_seconds if timeout_seconds is None else timeout_seconds
        if not self._event.wait(timeout=timeout):
            raise RuntimeError(f"Timed out waiting {timeout:.2f}s for a Record3D frame.")
        if self._stream_stopped:
            raise RuntimeError("The Record3D stream stopped before a frame could be consumed.")

        timestamp_ns = time.time_ns()
        observation = self._observation_from_stream(
            stream,
            seq=self._observation_seq,
            timestamp_ns=timestamp_ns,
        )
        self._event.clear()
        self._observation_seq += 1
        return observation

    def iter_observations(self) -> Iterator[Observation]:
        """Yield shared observations indefinitely until the caller stops consuming them."""
        while True:
            yield self.wait_for_observation()

    def _require_stream(self) -> Any:
        if self._stream is None:
            raise RuntimeError("No active Record3D stream. Call `connect()` first.")
        return self._stream

    def _get_connected_devices(self) -> list[Any]:
        return list(self._record3d.Record3DStream.get_connected_devices())

    def _observation_from_stream(
        self,
        stream: Any,
        *,
        seq: int,
        timestamp_ns: int,
    ) -> Observation:
        device_type = Record3DDeviceType(stream.get_device_type())
        confidence = np.asarray(stream.get_confidence_frame(), dtype=np.uint8)
        return Observation(
            seq=seq,
            timestamp_ns=timestamp_ns,
            source_frame_index=seq,
            arrival_timestamp_s=timestamp_ns / 1e9,
            rgb=np.asarray(stream.get_rgb_frame(), dtype=np.uint8),
            depth_m=np.asarray(stream.get_depth_frame(), dtype=np.float32),
            intrinsics=self._intrinsics_from_binding(stream.get_intrinsic_mat()),
            T_world_camera=self._camera_pose_from_binding(stream.get_camera_pose()),
            confidence=confidence.astype(np.float32) if confidence.size else None,
            provenance=ObservationProvenance(
                source_id="record3d",
                transport=Record3DTransportId.USB.value,
                device_type=device_type.name.lower(),
            ),
        )

    def _on_new_frame(self) -> None:
        self._event.set()

    def _on_stream_stopped(self) -> None:
        self._stream_stopped = True
        self._event.set()

    @staticmethod
    def _device_from_binding(device: Any) -> Record3DDevice:
        return Record3DDevice(product_id=int(device.product_id), udid=str(device.udid))

    @staticmethod
    def _intrinsics_from_binding(coeffs: Any) -> CameraIntrinsics:
        return CameraIntrinsics(
            fx=float(coeffs.fx),
            fy=float(coeffs.fy),
            cx=float(coeffs.tx),
            cy=float(coeffs.ty),
        )

    @staticmethod
    def _camera_pose_from_binding(camera_pose: Any) -> FrameTransform:
        return FrameTransform(
            target_frame="record3d_world",
            source_frame=CAMERA_RDF_FRAME,
            qx=float(camera_pose.qx),
            qy=float(camera_pose.qy),
            qz=float(camera_pose.qz),
            qw=float(camera_pose.qw),
            tx=float(camera_pose.tx),
            ty=float(camera_pose.ty),
            tz=float(camera_pose.tz),
        )


def list_record3d_usb_devices() -> list[Record3DDevice]:
    """List currently connected USB devices through the canonical Record3D IO owner."""
    stream = Record3DStreamConfig().setup_target()
    if stream is None:
        raise RuntimeError("Failed to initialize the USB Record3D packet stream.")
    return stream.list_devices()


def open_record3d_usb_packet_stream(*, device_index: int, frame_timeout_seconds: float) -> Record3DUSBPacketStream:
    """Build one validated USB packet stream ready for the shared runtime seam."""
    stream = Record3DStreamConfig(
        device_index=device_index,
        frame_timeout_seconds=frame_timeout_seconds,
    ).setup_target()
    if stream is None:
        raise RuntimeError("Failed to initialize the USB Record3D packet stream.")
    return stream


def build_record3d_frame_details(observation: Observation, *, source_label: str = "") -> dict[str, object]:
    """Build the compact frame-details payload shown by Record3D consumers."""
    arrival_timestamp_s = observation.arrival_timestamp_s
    if arrival_timestamp_s is None:
        arrival_timestamp_s = observation.timestamp_ns / 1e9
    details: dict[str, object] = {"arrival_timestamp_s": round(arrival_timestamp_s, 3)}
    if source_label:
        details["source"] = source_label
    if observation.provenance.original_width is not None and observation.provenance.original_height is not None:
        details["original_size"] = [observation.provenance.original_width, observation.provenance.original_height]
    provenance_payload = observation.provenance.compact_payload()
    if provenance_payload:
        details["provenance"] = provenance_payload
    return details


__all__ = [
    "build_record3d_frame_details",
    "list_record3d_usb_devices",
    "open_record3d_usb_packet_stream",
    "Record3DDevice",
    "Record3DDeviceType",
    "Record3DStreamConfig",
    "Record3DTransportId",
    "Record3DUSBPacketStream",
]
