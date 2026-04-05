"""Record3D streaming integration for shared packet ingestion."""

from __future__ import annotations

import importlib
import time
from enum import IntEnum, StrEnum
from threading import Event
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from prml_vslam.interfaces import CameraIntrinsics, FramePacket, SE3Pose
from prml_vslam.utils import BaseConfig, BaseData, Console

if TYPE_CHECKING:
    from collections.abc import Iterator


class Record3DTransportId(StrEnum):
    """Stable transport identifiers used by the app and IO layers."""

    USB = "usb"
    WIFI = "wifi"

    @property
    def label(self) -> str:
        """Return the user-facing transport label."""
        return {
            Record3DTransportId.USB: "USB",
            Record3DTransportId.WIFI: "Wi-Fi",
        }[self]


class Record3DStreamState(StrEnum):
    """Lifecycle states for one live Record3D transport."""

    IDLE = "idle"
    CONNECTING = "connecting"
    STREAMING = "streaming"
    DISCONNECTED = "disconnected"
    FAILED = "failed"


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


class Record3DFrame(BaseData):
    """One RGBD frame sampled from the USB Record3D stream."""

    rgb: NDArray[np.uint8]
    """RGB image in HxWx3 layout."""

    depth: NDArray[np.float32]
    """Depth image in meters."""

    confidence: NDArray[np.uint8]
    """Per-pixel confidence map aligned with the depth image."""

    intrinsics: CameraIntrinsics
    """Camera intrinsics associated with the RGB frame."""

    pose: SE3Pose
    """Camera pose associated with the current frame."""

    device_type: Record3DDeviceType
    """Source camera type used for the stream."""


class Record3DStreamSnapshot(BaseData):
    """Latest live-stream snapshot shared between IO and app layers."""

    transport: Record3DTransportId | None = None
    """Transport currently backing the snapshot, when active."""

    state: Record3DStreamState = Record3DStreamState.IDLE
    """Current lifecycle state of the live transport."""

    source_label: str = ""
    """Human-readable source descriptor such as a UDID or Wi-Fi address."""

    received_frames: int = 0
    """Number of frame packets consumed since the current run started."""

    measured_fps: float = 0.0
    """Rolling transport frame rate measured at the packet sink."""

    latest_packet: FramePacket | None = None
    """Most recent frame packet, if any."""

    trajectory_positions_xyz: NDArray[np.float64] = Field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))
    """Bounded live ego-trajectory history in world coordinates."""

    trajectory_timestamps_s: NDArray[np.float64] = Field(default_factory=lambda: np.empty((0,), dtype=np.float64))
    """Arrival timestamps associated with `trajectory_positions_xyz`."""

    error_message: str = ""
    """Last surfaced error message."""


def record3d_frame_to_packet(
    frame: Record3DFrame,
    *,
    seq: int,
    timestamp_ns: int | None = None,
    arrival_timestamp_s: float | None = None,
) -> FramePacket:
    """Adapt a USB `Record3DFrame` into the shared packet contract.

    Args:
        frame: Low-level USB Record3D frame emitted by the native bindings.
        arrival_timestamp_s: Optional wall-clock timestamp override.

    Returns:
        Shared packet payload that can be consumed uniformly by the app.
    """
    if timestamp_ns is None:
        timestamp_ns = time.time_ns()
    if arrival_timestamp_s is None:
        arrival_timestamp_s = timestamp_ns / 1e9

    return FramePacket(
        seq=seq,
        timestamp_ns=timestamp_ns,
        arrival_timestamp_s=arrival_timestamp_s,
        rgb=frame.rgb,
        depth=frame.depth,
        intrinsics=frame.intrinsics,
        pose=frame.pose,
        uncertainty=frame.confidence.astype(np.float32) if frame.confidence.size else None,
        metadata={
            "transport": Record3DTransportId.USB.value,
            "device_type": frame.device_type.value,
        },
    )


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


class Record3DStreamConfig(BaseConfig):
    """Configuration for a USB Record3D streaming session."""

    device_index: int = 0
    """Zero-based index into the list of connected Record3D devices."""

    frame_timeout_seconds: float = 5.0
    """Maximum time to wait for the next frame before failing."""

    @property
    def target_type(self) -> type[Record3DStreamSession]:
        """Runtime type used to manage one Record3D stream."""
        return Record3DStreamSession


class Record3DUSBPacketStreamConfig(BaseConfig):
    """Configuration for the USB packet adapter used by the Streamlit app."""

    stream: Record3DStreamConfig = Field(default_factory=Record3DStreamConfig)
    """Nested low-level USB stream configuration."""

    @property
    def target_type(self) -> type[Record3DUSBPacketStream]:
        """Runtime type that exposes shared packet objects."""
        return Record3DUSBPacketStream


class Record3DStreamSession:
    """Manage one USB-connected Record3D session."""

    def __init__(self, config: Record3DStreamConfig) -> None:
        self.config = config
        self.console = Console(__name__).child(self.__class__.__name__)
        self._record3d = _import_record3d_module()
        self._event = Event()
        self._stream: Any | None = None
        self._stream_stopped = False

    def list_devices(self) -> list[Record3DDevice]:
        """Return the currently connected Record3D devices."""
        return [self._device_from_binding(device) for device in self._get_connected_devices()]

    def connect(self) -> Record3DDevice:
        """Connect to the configured Record3D device and start streaming."""
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

        target_device = devices[self.config.device_index]
        stream = self._record3d.Record3DStream()
        stream.on_new_frame = self._on_new_frame
        stream.on_stream_stopped = self._on_stream_stopped

        if not stream.connect(target_device):
            raise RuntimeError(f"Failed to connect to Record3D device at index {self.config.device_index}.")

        self._stream = stream
        self._stream_stopped = False
        device = self._device_from_binding(target_device)
        self.console.info("Connected to Record3D device %s (%s).", device.udid, device.product_id)
        return device

    def disconnect(self) -> None:
        """Disconnect the active Record3D stream if present."""
        if self._stream is None:
            return

        self._stream.disconnect()
        self._stream = None
        self._stream_stopped = True
        self._event.clear()

    def wait_for_frame(self, timeout_seconds: float | None = None) -> Record3DFrame:
        """Wait for the next frame and return it as a typed container.

        Args:
            timeout_seconds: Optional timeout override. Defaults to the config value.

        Returns:
            The latest RGBD frame emitted by the device.
        """
        if self._stream is None:
            raise RuntimeError("No active Record3D stream. Call `connect()` first.")

        timeout = self.config.frame_timeout_seconds if timeout_seconds is None else timeout_seconds
        if not self._event.wait(timeout=timeout):
            raise RuntimeError(f"Timed out waiting {timeout:.2f}s for a Record3D frame.")

        if self._stream_stopped:
            raise RuntimeError("The Record3D stream stopped before a frame could be consumed.")

        frame = Record3DFrame(
            rgb=np.asarray(self._stream.get_rgb_frame(), dtype=np.uint8),
            depth=np.asarray(self._stream.get_depth_frame(), dtype=np.float32),
            confidence=np.asarray(self._stream.get_confidence_frame(), dtype=np.uint8),
            intrinsics=self._intrinsics_from_binding(self._stream.get_intrinsic_mat()),
            pose=self._camera_pose_from_binding(self._stream.get_camera_pose()),
            device_type=Record3DDeviceType(self._stream.get_device_type()),
        )
        self._event.clear()
        return frame

    def iter_frames(self) -> Iterator[Record3DFrame]:
        """Yield frames indefinitely until the caller stops consuming them."""
        while True:
            yield self.wait_for_frame()

    def _get_connected_devices(self) -> list[Any]:
        return list(self._record3d.Record3DStream.get_connected_devices())

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
    def _camera_pose_from_binding(camera_pose: Any) -> SE3Pose:
        return SE3Pose(
            qx=float(camera_pose.qx),
            qy=float(camera_pose.qy),
            qz=float(camera_pose.qz),
            qw=float(camera_pose.qw),
            tx=float(camera_pose.tx),
            ty=float(camera_pose.ty),
            tz=float(camera_pose.tz),
        )


class Record3DUSBPacketStream:
    """Adapt the blocking USB stream session into shared packet objects."""

    def __init__(self, config: Record3DUSBPacketStreamConfig) -> None:
        self.config = config
        self.session = config.stream.setup_target()
        self._packet_seq = 0

    def _require_session(self) -> Record3DStreamSession:
        if self.session is None:
            raise RuntimeError("Failed to initialize the USB Record3D stream session.")
        return self.session

    def list_devices(self) -> list[Record3DDevice]:
        """List the currently connected USB Record3D devices."""
        return self._require_session().list_devices()

    def connect(self) -> Record3DDevice:
        """Connect to the configured USB device."""
        self._packet_seq = 0
        return self._require_session().connect()

    def disconnect(self) -> None:
        """Disconnect the current USB device if one is active."""
        if self.session is not None:
            self.session.disconnect()
        self._packet_seq = 0

    def wait_for_packet(self, timeout_seconds: float | None = None) -> FramePacket:
        """Wait for the next shared packet emitted by the USB device."""
        timestamp_ns = time.time_ns()
        packet = record3d_frame_to_packet(
            self._require_session().wait_for_frame(timeout_seconds=timeout_seconds),
            seq=self._packet_seq,
            timestamp_ns=timestamp_ns,
            arrival_timestamp_s=timestamp_ns / 1e9,
        )
        self._packet_seq += 1
        return packet

    def iter_packets(self) -> Iterator[FramePacket]:
        """Yield shared packets indefinitely until the caller stops consuming them."""
        while True:
            yield self.wait_for_packet()


__all__ = [
    "Record3DDevice",
    "Record3DDeviceType",
    "Record3DFrame",
    "Record3DStreamConfig",
    "Record3DStreamSession",
    "Record3DStreamSnapshot",
    "Record3DStreamState",
    "Record3DTransportId",
    "Record3DUSBPacketStream",
    "Record3DUSBPacketStreamConfig",
    "record3d_frame_to_packet",
]
