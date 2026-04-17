"""Record3D streaming integration for shared packet ingestion."""

from __future__ import annotations

import importlib
import time
from collections.abc import Iterator
from enum import IntEnum, StrEnum
from threading import Event
from typing import Any

import numpy as np

from prml_vslam.interfaces import CameraIntrinsics, FramePacket, FrameTransform
from prml_vslam.utils import BaseConfig, BaseData, Console, FactoryConfig


class Record3DTransportId(StrEnum):
    """Stable transport identifiers used by the app preview and capture layers."""

    USB = "usb"
    WIFI = "wifi"

    @property
    def label(self) -> str:
        """Return the user-facing transport label."""
        return "Wi-Fi Preview" if self is Record3DTransportId.WIFI else self.value.upper()

    def stream_hint(self) -> str:
        """Return the short transport-specific helper text."""
        match self:
            case Record3DTransportId.USB:
                return (
                    "USB capture uses the native `record3d` Python bindings and is the canonical programmatic ingress "
                    "for Record3D in this repo. It can expose RGB, depth, intrinsics, pose, and confidence."
                )
            case Record3DTransportId.WIFI:
                return (
                    "Wi-Fi Preview uses a Python-side WebRTC receiver. It is an optional lower-fidelity preview path "
                    "for the app, not the canonical ingestion boundary. Enter the device address shown in the iPhone "
                    "app."
                )
            case _:
                raise ValueError(f"Unsupported Record3D transport: {self}")


class Record3DDeviceType(IntEnum):
    """Device types exposed by the Record3D bindings."""

    TRUEDEPTH = 0
    LIDAR = 1


class Record3DDevice(BaseData):
    """One USB-connected Record3D device."""

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
    """Configuration for a USB Record3D streaming session."""

    device_index: int = 0
    """Zero-based index into the list of connected Record3D devices."""

    frame_timeout_seconds: float = 5.0
    """Maximum time to wait for the next frame before failing."""

    @property
    def target_type(self) -> type[Record3DUSBPacketStream]:
        """Runtime type that exposes shared packet objects."""
        return Record3DUSBPacketStream


class Record3DUSBPacketStream:
    """Thin packet-stream adapter around the upstream `record3d.Record3DStream`."""

    def __init__(self, config: Record3DStreamConfig) -> None:
        self.config = config
        self.console = Console(__name__).child(self.__class__.__name__)
        self._record3d = _import_record3d_module()
        self._event = Event()
        self._stream: Any | None = None
        self._stream_stopped = False
        self._packet_seq = 0

    def list_devices(self) -> list[Record3DDevice]:
        """List the currently connected USB Record3D devices."""
        return [self._device_from_binding(device) for device in self._get_connected_devices()]

    def connect(self) -> Record3DDevice:
        """Connect to the configured USB device."""
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
        self._packet_seq = 0
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
        self._packet_seq = 0

    def wait_for_packet(self, timeout_seconds: float | None = None) -> FramePacket:
        """Wait for the next shared packet emitted by the USB device."""
        stream = self._require_stream()
        timeout = self.config.frame_timeout_seconds if timeout_seconds is None else timeout_seconds
        if not self._event.wait(timeout=timeout):
            raise RuntimeError(f"Timed out waiting {timeout:.2f}s for a Record3D frame.")
        if self._stream_stopped:
            raise RuntimeError("The Record3D stream stopped before a frame could be consumed.")

        timestamp_ns = time.time_ns()
        packet = self._packet_from_stream(
            stream,
            seq=self._packet_seq,
            timestamp_ns=timestamp_ns,
        )
        self._event.clear()
        self._packet_seq += 1
        return packet

    def iter_packets(self) -> Iterator[FramePacket]:
        """Yield shared packets indefinitely until the caller stops consuming them."""
        while True:
            yield self.wait_for_packet()

    def _require_stream(self) -> Any:
        if self._stream is None:
            raise RuntimeError("No active Record3D stream. Call `connect()` first.")
        return self._stream

    def _get_connected_devices(self) -> list[Any]:
        return list(self._record3d.Record3DStream.get_connected_devices())

    def _packet_from_stream(
        self,
        stream: Any,
        *,
        seq: int,
        timestamp_ns: int,
    ) -> FramePacket:
        device_type = Record3DDeviceType(stream.get_device_type())
        confidence = np.asarray(stream.get_confidence_frame(), dtype=np.uint8)
        return FramePacket(
            seq=seq,
            timestamp_ns=timestamp_ns,
            arrival_timestamp_s=timestamp_ns / 1e9,
            rgb=np.asarray(stream.get_rgb_frame(), dtype=np.uint8),
            depth=np.asarray(stream.get_depth_frame(), dtype=np.float32),
            intrinsics=self._intrinsics_from_binding(stream.get_intrinsic_mat()),
            pose=self._camera_pose_from_binding(stream.get_camera_pose()),
            confidence=confidence.astype(np.float32) if confidence.size else None,
            metadata={
                "transport": Record3DTransportId.USB.value,
                "device_type": device_type.value,
            },
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
            qx=float(camera_pose.qx),
            qy=float(camera_pose.qy),
            qz=float(camera_pose.qz),
            qw=float(camera_pose.qw),
            tx=float(camera_pose.tx),
            ty=float(camera_pose.ty),
            tz=float(camera_pose.tz),
        )


def list_record3d_usb_devices() -> list[Record3DDevice]:
    """List currently connected Record3D USB devices through the canonical IO owner."""
    stream = Record3DStreamConfig().setup_target()
    if stream is None:
        raise RuntimeError("Failed to initialize the USB Record3D packet stream.")
    return stream.list_devices()


def open_record3d_usb_packet_stream(*, device_index: int, frame_timeout_seconds: float) -> Record3DUSBPacketStream:
    """Build one shared USB packet stream with explicit runtime validation."""
    stream = Record3DStreamConfig(
        device_index=device_index,
        frame_timeout_seconds=frame_timeout_seconds,
    ).setup_target()
    if stream is None:
        raise RuntimeError("Failed to initialize the USB Record3D packet stream.")
    return stream


def build_record3d_frame_details(packet: FramePacket, *, source_label: str = "") -> dict[str, object]:
    """Build the compact frame-details payload shown by Record3D consumers."""
    arrival_timestamp_s = packet.arrival_timestamp_s
    if arrival_timestamp_s is None:
        arrival_timestamp_s = packet.timestamp_ns / 1e9
    details: dict[str, object] = {"arrival_timestamp_s": round(arrival_timestamp_s, 3)}
    if source_label:
        details["source"] = source_label
    if "original_size" in packet.metadata:
        details["original_size"] = packet.metadata["original_size"]
    if packet.metadata:
        details["metadata"] = packet.metadata
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
