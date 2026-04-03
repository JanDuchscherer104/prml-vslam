"""Record3D streaming integration for local RGBD preview and app ingestion."""

from __future__ import annotations

import importlib
import time
from enum import IntEnum, StrEnum
from threading import Event
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from prml_vslam.utils import BaseConfig, BaseData, Console

if TYPE_CHECKING:
    from collections.abc import Iterator


# TODO: do not refine custom errors, this is overkill.
class Record3DError(RuntimeError):
    """Base exception for Record3D integration failures."""


class Record3DDependencyError(Record3DError):
    """Raised when the optional Record3D dependency is unavailable."""


class Record3DConnectionError(Record3DError):
    """Raised when a Record3D device cannot be connected."""


class Record3DTimeoutError(Record3DError):
    """Raised when waiting for a streamed frame exceeds the configured timeout."""


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


# TODO: use IntEnum
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


class Record3DIntrinsicMatrix(BaseData):
    """Intrinsic matrix coefficients of the current RGB frame."""

    fx: float
    """Focal length in pixels along the x axis."""

    fy: float
    """Focal length in pixels along the y axis."""

    tx: float
    """Principal point x coordinate in pixels."""

    ty: float
    """Principal point y coordinate in pixels."""

    def as_matrix(self) -> NDArray[np.float64]:
        """Return the intrinsic coefficients as a 3x3 camera matrix."""
        return np.array(
            [
                [self.fx, 0.0, self.tx],
                [0.0, self.fy, self.ty],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )


class Record3DCameraPose(BaseData):
    """Camera pose reported by Record3D for the current frame."""

    qx: float
    """Quaternion x component."""

    qy: float
    """Quaternion y component."""

    qz: float
    """Quaternion z component."""

    qw: float
    """Quaternion w component."""

    tx: float
    """Translation x component in world coordinates."""

    ty: float
    """Translation y component in world coordinates."""

    tz: float
    """Translation z component in world coordinates."""


class Record3DFrame(BaseData):
    """One RGBD frame sampled from the USB Record3D stream."""

    rgb: NDArray[np.uint8]
    """RGB image in HxWx3 layout."""

    depth: NDArray[np.float32]
    """Depth image in meters."""

    confidence: NDArray[np.uint8]
    """Per-pixel confidence map aligned with the depth image."""

    intrinsic_matrix: Record3DIntrinsicMatrix
    """Camera intrinsics associated with the RGB frame."""

    camera_pose: Record3DCameraPose
    """Camera pose associated with the current frame."""

    device_type: Record3DDeviceType
    """Source camera type used for the stream."""


class Record3DFramePacket(BaseData):
    """Transport-agnostic frame packet exposed to the Streamlit app."""

    transport: Record3DTransportId
    """Transport that emitted the packet."""

    rgb: NDArray[np.uint8]
    """RGB image in HxWx3 layout."""

    depth: NDArray[np.float32]
    """Depth image aligned with the RGB frame."""

    intrinsic_matrix: Record3DIntrinsicMatrix | None = None
    """Camera intrinsics associated with the packet when available."""

    uncertainty: NDArray[np.float32] | None = None
    """Optional uncertainty or confidence image aligned with `depth`."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Extra transport-specific metadata associated with the packet."""

    arrival_timestamp_s: float
    """Local wall-clock timestamp when the packet reached Python."""


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

    latest_packet: Record3DFramePacket | None = None
    """Most recent frame packet, if any."""

    trajectory_positions_xyz: NDArray[np.float64] = Field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))
    """Bounded live ego-trajectory history in world coordinates."""

    trajectory_timestamps_s: NDArray[np.float64] = Field(default_factory=lambda: np.empty((0,), dtype=np.float64))
    """Arrival timestamps associated with `trajectory_positions_xyz`."""

    error_message: str = ""
    """Last surfaced error message."""


class Record3DPacketStream(Protocol):
    """Common blocking packet-stream interface used by app runtimes."""

    def connect(self) -> Any:
        """Connect to the configured transport and start streaming."""

    def disconnect(self) -> None:
        """Disconnect the current transport session."""

    def wait_for_packet(self, timeout_seconds: float | None = None) -> Record3DFramePacket:
        """Wait for the next transport packet."""


def record3d_frame_to_packet(
    frame: Record3DFrame,
    *,
    arrival_timestamp_s: float | None = None,
) -> Record3DFramePacket:
    """Adapt a USB `Record3DFrame` into the shared packet contract.

    Args:
        frame: Low-level USB Record3D frame emitted by the native bindings.
        arrival_timestamp_s: Optional wall-clock timestamp override.

    Returns:
        Shared packet payload that can be consumed uniformly by the app.
    """
    return Record3DFramePacket(
        transport=Record3DTransportId.USB,
        rgb=frame.rgb,
        depth=frame.depth,
        intrinsic_matrix=frame.intrinsic_matrix,
        uncertainty=frame.confidence.astype(np.float32) if frame.confidence.size else None,
        metadata={
            "camera_pose": frame.camera_pose.model_dump(mode="python"),
            "device_type": frame.device_type.value,
        },
        arrival_timestamp_s=time.time() if arrival_timestamp_s is None else arrival_timestamp_s,
    )


def _import_record3d_module() -> Any:
    """Import the optional native Record3D bindings."""
    try:
        return importlib.import_module("record3d")
    except ModuleNotFoundError as exc:
        raise Record3DDependencyError(
            "The optional `record3d` package is required for streaming. "
            "Install it with `uv sync --extra streaming` and make sure the upstream prerequisites are installed "
            "(CMake, iTunes on macOS/Windows, or libusbmuxd on Linux)."
        ) from exc


def _import_cv2_module() -> Any:
    """Import OpenCV lazily so Wi-Fi streaming does not load FFmpeg twice."""
    try:
        return importlib.import_module("cv2")
    except ModuleNotFoundError as exc:
        raise Record3DDependencyError(
            "The optional `opencv-python` package is required for the Record3D preview. "
            "Install the project dependencies with `uv sync`."
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


class Record3DPreviewConfig(BaseConfig):
    """Configuration for the OpenCV-based Record3D preview consumer."""

    stream: Record3DStreamConfig = Field(default_factory=Record3DStreamConfig)
    """Nested stream configuration describing the USB device and timeouts."""

    window_prefix: str = "Record3D"
    """Prefix used for the preview window titles."""

    show_confidence: bool = True
    """Whether to open a preview window for the confidence map."""

    wait_key_millis: int = 1
    """Delay passed into ``cv2.waitKey`` for UI refresh."""

    exit_key: str = "q"
    """Single-character key that stops the preview loop."""

    max_frames: int | None = None
    """Optional hard limit for the number of frames displayed."""

    @property
    def target_type(self) -> type[Record3DPreviewApp]:
        """Runtime type used to preview the live stream."""
        return Record3DPreviewApp


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
            raise Record3DConnectionError(
                "No Record3D devices detected. Connect the iPhone via USB, open the Record3D app, "
                "and enable USB Streaming mode."
            )

        if self.config.device_index >= len(devices):
            raise Record3DConnectionError(
                f"Configured device index {self.config.device_index} is out of range for {len(devices)} connected device(s)."
            )

        target_device = devices[self.config.device_index]
        stream = self._record3d.Record3DStream()
        stream.on_new_frame = self._on_new_frame
        stream.on_stream_stopped = self._on_stream_stopped

        if not stream.connect(target_device):
            raise Record3DConnectionError(f"Failed to connect to Record3D device at index {self.config.device_index}.")

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
            raise Record3DConnectionError("No active Record3D stream. Call `connect()` first.")

        timeout = self.config.frame_timeout_seconds if timeout_seconds is None else timeout_seconds
        if not self._event.wait(timeout=timeout):
            raise Record3DTimeoutError(f"Timed out waiting {timeout:.2f}s for a Record3D frame.")

        if self._stream_stopped:
            raise Record3DConnectionError("The Record3D stream stopped before a frame could be consumed.")

        frame = Record3DFrame(
            rgb=np.asarray(self._stream.get_rgb_frame(), dtype=np.uint8),
            depth=np.asarray(self._stream.get_depth_frame(), dtype=np.float32),
            confidence=np.asarray(self._stream.get_confidence_frame(), dtype=np.uint8),
            intrinsic_matrix=self._intrinsics_from_binding(self._stream.get_intrinsic_mat()),
            camera_pose=self._camera_pose_from_binding(self._stream.get_camera_pose()),
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
    def _intrinsics_from_binding(coeffs: Any) -> Record3DIntrinsicMatrix:
        return Record3DIntrinsicMatrix(
            fx=float(coeffs.fx),
            fy=float(coeffs.fy),
            tx=float(coeffs.tx),
            ty=float(coeffs.ty),
        )

    @staticmethod
    def _camera_pose_from_binding(camera_pose: Any) -> Record3DCameraPose:
        return Record3DCameraPose(
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

    def _require_session(self) -> Record3DStreamSession:
        if self.session is None:
            raise Record3DConnectionError("Failed to initialize the USB Record3D stream session.")
        return self.session

    def list_devices(self) -> list[Record3DDevice]:
        """List the currently connected USB Record3D devices."""
        return self._require_session().list_devices()

    def connect(self) -> Record3DDevice:
        """Connect to the configured USB device."""
        return self._require_session().connect()

    def disconnect(self) -> None:
        """Disconnect the current USB device if one is active."""
        if self.session is not None:
            self.session.disconnect()

    def wait_for_packet(self, timeout_seconds: float | None = None) -> Record3DFramePacket:
        """Wait for the next shared packet emitted by the USB device."""
        return record3d_frame_to_packet(self._require_session().wait_for_frame(timeout_seconds=timeout_seconds))

    def iter_packets(self) -> Iterator[Record3DFramePacket]:
        """Yield shared packets indefinitely until the caller stops consuming them."""
        while True:
            yield self.wait_for_packet()


class Record3DPreviewApp:
    """Preview the Record3D RGBD stream through OpenCV windows."""

    def __init__(self, config: Record3DPreviewConfig) -> None:
        self.config = config
        self.console = Console(__name__).child(self.__class__.__name__)
        self.stream = config.stream.setup_target()
        self._cv2 = _import_cv2_module()

    def run(self) -> None:
        """Connect to Record3D and show the live RGBD preview."""
        if self.stream is None:
            raise Record3DConnectionError("Failed to initialize the Record3D stream session.")

        self.stream.connect()
        frames_seen = 0

        try:
            for frame in self.stream.iter_frames():
                self._show_frame(frame)
                frames_seen += 1

                key_code = self._cv2.waitKey(self.config.wait_key_millis) & 0xFF
                if key_code == ord(self.config.exit_key):
                    self.console.info("Stopping Record3D preview after exit key `%s`.", self.config.exit_key)
                    break

                if self.config.max_frames is not None and frames_seen >= self.config.max_frames:
                    self.console.info("Stopping Record3D preview after %s frame(s).", self.config.max_frames)
                    break
        finally:
            self.stream.disconnect()
            self._cv2.destroyAllWindows()

    def _show_frame(self, frame: Record3DFrame) -> None:
        rgb = frame.rgb
        depth = frame.depth
        confidence = frame.confidence

        if frame.device_type is Record3DDeviceType.TRUEDEPTH:
            rgb = self._cv2.flip(rgb, 1)
            depth = self._cv2.flip(depth, 1)
            confidence = self._cv2.flip(confidence, 1) if confidence.size else confidence

        rgb_bgr = self._cv2.cvtColor(rgb, self._cv2.COLOR_RGB2BGR)
        self._cv2.imshow(f"{self.config.window_prefix} RGB", rgb_bgr)
        self._cv2.imshow(f"{self.config.window_prefix} Depth", self._render_depth(depth))

        if self.config.show_confidence and confidence.size:
            self._cv2.imshow(f"{self.config.window_prefix} Confidence", self._render_confidence(confidence))

    @staticmethod
    def _render_depth(depth: NDArray[np.float32]) -> NDArray[np.uint8]:
        if depth.size == 0:
            return np.zeros((1, 1), dtype=np.uint8)

        cv2_module = _import_cv2_module()
        normalized = cv2_module.normalize(depth, None, alpha=0, beta=255, norm_type=cv2_module.NORM_MINMAX)
        return normalized.astype(np.uint8)

    @staticmethod
    def _render_confidence(confidence: NDArray[np.uint8]) -> NDArray[np.uint8]:
        if confidence.size == 0:
            return np.zeros((1, 1), dtype=np.uint8)
        return (confidence.astype(np.uint16) * 100).clip(0, 255).astype(np.uint8)


__all__ = [
    "Record3DCameraPose",
    "Record3DConnectionError",
    "Record3DDependencyError",
    "Record3DDevice",
    "Record3DDeviceType",
    "Record3DError",
    "Record3DFrame",
    "Record3DFramePacket",
    "Record3DIntrinsicMatrix",
    "Record3DPacketStream",
    "Record3DPreviewApp",
    "Record3DPreviewConfig",
    "Record3DStreamConfig",
    "Record3DStreamSession",
    "Record3DStreamSnapshot",
    "Record3DStreamState",
    "Record3DTimeoutError",
    "Record3DTransportId",
    "Record3DUSBPacketStream",
    "Record3DUSBPacketStreamConfig",
    "record3d_frame_to_packet",
]
