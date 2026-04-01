"""Typed Record3D streaming helpers for optional USB preview and metadata parsing."""

import importlib
from collections.abc import Iterator
from enum import IntEnum
from threading import Event
from typing import Any, Self

import cv2
import numpy as np
from jaxtyping import Float, UInt8
from pydantic import Field

from prml_vslam.utils.base_config import BaseConfig
from prml_vslam.utils.console import Console


class Record3DError(RuntimeError):
    """Base exception for Record3D integration failures."""


class Record3DDependencyError(Record3DError):
    """Raised when the optional Record3D dependency is unavailable."""


class Record3DConnectionError(Record3DError):
    """Raised when a Record3D device cannot be connected."""


class Record3DTimeoutError(Record3DError):
    """Raised when waiting for a streamed frame exceeds the configured timeout."""


class Record3DDeviceType(IntEnum):
    """Device types exposed by the Record3D bindings."""

    TRUEDEPTH = 0
    LIDAR = 1


class Record3DDevice(BaseConfig):
    """One USB-connected Record3D device."""

    product_id: int
    """Apple product identifier reported by the device."""

    udid: str
    """Unique device identifier reported by the bindings."""


class Record3DIntrinsicMatrix(BaseConfig):
    """Camera intrinsic parameters reported by Record3D."""

    fx: float
    """Focal length in pixels along the x axis."""

    fy: float
    """Focal length in pixels along the y axis."""

    tx: float
    """Principal point x coordinate in pixels."""

    ty: float
    """Principal point y coordinate in pixels."""

    def as_matrix(self) -> Float[np.ndarray, "3 3"]:  # noqa: F722
        """Return the intrinsic coefficients as a 3x3 camera matrix."""
        return np.array(
            [
                [self.fx, 0.0, self.tx],
                [0.0, self.fy, self.ty],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

    def to_markdown_latex(self, name: str = "K") -> str:
        """Render the intrinsic matrix as Markdown-hosted LaTeX."""
        rows = r" \\ ".join(" & ".join(f"{value:.3f}" for value in row) for row in self.as_matrix())
        return rf"$$ {name} = \begin{{bmatrix}} {rows} \end{{bmatrix}} $$"

    @classmethod
    def from_matrix_payload(cls, payload: Any) -> Self | None:
        """Build intrinsics from a Record3D matrix payload when possible.

        Args:
            payload: Flat or nested matrix payload from Record3D metadata.

        Returns:
            A parsed intrinsic matrix when the payload shape is supported; otherwise ``None``.
        """
        rows = _coerce_matrix_rows(payload)
        if rows is None:
            return None
        return cls(
            fx=rows[0][0],
            fy=rows[1][1],
            tx=rows[0][2],
            ty=rows[1][2],
        )


class Record3DCameraPose(BaseConfig):
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


class Record3DFrame(BaseConfig):
    """One RGBD frame sampled from the Record3D stream."""

    rgb: UInt8[np.ndarray, "height width 3"]  # noqa: F722
    """RGB image in HxWx3 layout."""

    depth: Float[np.ndarray, "height width"]  # noqa: F722
    """Depth image in meters."""

    confidence: UInt8[np.ndarray, "height width"]  # noqa: F722
    """Per-pixel confidence map aligned with the depth image."""

    intrinsic_matrix: Record3DIntrinsicMatrix
    """Camera intrinsics associated with the RGB frame."""

    camera_pose: Record3DCameraPose
    """Camera pose associated with the current frame."""

    device_type: Record3DDeviceType
    """Source camera type used for the stream."""


class Record3DUSBStatus(BaseConfig):
    """Current USB availability summary for Record3D."""

    dependency_available: bool = True
    """Whether the optional native Record3D bindings are installed."""

    devices: list[Record3DDevice] = Field(default_factory=list)
    """USB devices currently visible to the Record3D bindings."""

    error_message: str = ""
    """Optional dependency or discovery error surfaced to the app."""


def _coerce_matrix_rows(payload: Any) -> list[list[float]] | None:
    """Normalize a flat or nested 3x3 matrix payload into row-major rows."""
    if isinstance(payload, list) and len(payload) == 9 and all(isinstance(value, int | float) for value in payload):
        return [
            [float(payload[0]), float(payload[3]), float(payload[6])],
            [float(payload[1]), float(payload[4]), float(payload[7])],
            [float(payload[2]), float(payload[5]), float(payload[8])],
        ]

    if (
        isinstance(payload, list)
        and len(payload) == 3
        and all(isinstance(row, list) and len(row) == 3 for row in payload)
        and all(isinstance(value, int | float) for row in payload for value in row)
    ):
        return [[float(value) for value in row] for row in payload]

    return None


def _import_record3d_module() -> Any:
    """Import the optional native Record3D bindings."""
    try:
        return importlib.import_module("record3d")
    except ModuleNotFoundError as exc:
        msg = (
            "The optional `record3d` package is required for USB streaming. Install it with "
            "`uv sync --extra streaming` and satisfy the upstream native prerequisites."
        )
        raise Record3DDependencyError(msg) from exc


class Record3DStreamConfig(BaseConfig):
    """Configuration for a USB Record3D streaming session."""

    device_index: int = 0
    """Zero-based index into the list of connected Record3D devices."""

    frame_timeout_seconds: float = 5.0
    """Maximum time to wait for the next frame before failing."""

    @property
    def target_type(self) -> type["Record3DStreamSession"]:
        """Runtime type used to manage one Record3D stream."""
        return Record3DStreamSession


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
    def target_type(self) -> type["Record3DPreviewApp"]:
        """Runtime type used to preview the live stream."""
        return Record3DPreviewApp


class Record3DStreamSession:
    """Manage one USB-connected Record3D session."""

    def __init__(self, config: Record3DStreamConfig) -> None:
        self.config = config
        self.console = Console(f"{__name__}.{self.__class__.__name__}")
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
            msg = "No Record3D devices detected. Connect the iPhone via USB and enable USB Streaming mode."
            raise Record3DConnectionError(msg)

        if self.config.device_index >= len(devices):
            msg = (
                f"Configured device index {self.config.device_index} is out of range for "
                f"{len(devices)} connected device(s)."
            )
            raise Record3DConnectionError(msg)

        target_device = devices[self.config.device_index]
        stream = self._record3d.Record3DStream()
        stream.on_new_frame = self._on_new_frame
        stream.on_stream_stopped = self._on_stream_stopped
        if not stream.connect(target_device):
            msg = f"Failed to connect to Record3D device at index {self.config.device_index}."
            raise Record3DConnectionError(msg)

        self._stream = stream
        self._stream_stopped = False
        return self._device_from_binding(target_device)

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
        """Yield frames until the caller stops consuming them."""
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


class Record3DPreviewApp:
    """Preview the Record3D RGBD stream through OpenCV windows."""

    def __init__(self, config: Record3DPreviewConfig) -> None:
        self.config = config
        self.stream = config.stream.setup_target()

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
                key_code = cv2.waitKey(self.config.wait_key_millis) & 0xFF
                if key_code == ord(self.config.exit_key):
                    break
                if self.config.max_frames is not None and frames_seen >= self.config.max_frames:
                    break
        finally:
            self.stream.disconnect()
            cv2.destroyAllWindows()

    def _show_frame(self, frame: Record3DFrame) -> None:
        rgb = frame.rgb
        depth = frame.depth
        confidence = frame.confidence
        if frame.device_type is Record3DDeviceType.TRUEDEPTH:
            rgb = cv2.flip(rgb, 1)
            depth = cv2.flip(depth, 1)
            confidence = cv2.flip(confidence, 1) if confidence.size else confidence

        cv2.imshow(f"{self.config.window_prefix} RGB", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        cv2.imshow(f"{self.config.window_prefix} Depth", self._render_depth(depth))
        if self.config.show_confidence and confidence.size:
            cv2.imshow(f"{self.config.window_prefix} Confidence", self._render_confidence(confidence))

    @staticmethod
    def _render_depth(depth: Float[np.ndarray, "height width"]) -> UInt8[np.ndarray, "height width"]:  # noqa: F722
        if depth.size == 0:
            return np.zeros((1, 1), dtype=np.uint8)
        normalized = cv2.normalize(depth, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
        return normalized.astype(np.uint8)

    @staticmethod
    def _render_confidence(confidence: UInt8[np.ndarray, "height width"]) -> UInt8[np.ndarray, "height width"]:  # noqa: F722
        if confidence.size == 0:
            return np.zeros((1, 1), dtype=np.uint8)
        return (confidence.astype(np.uint16) * 100).clip(0, 255).astype(np.uint8)


def probe_record3d_usb_status() -> Record3DUSBStatus:
    """Probe optional USB Record3D availability without raising into the app."""
    try:
        session = Record3DStreamConfig().setup_target()
        if session is None:
            return Record3DUSBStatus(
                dependency_available=False,
                error_message="Failed to initialize the optional Record3D USB session.",
            )
        return Record3DUSBStatus(
            dependency_available=True,
            devices=session.list_devices(),
        )
    except Record3DDependencyError as exc:
        return Record3DUSBStatus(
            dependency_available=False,
            error_message=str(exc),
        )
    except Record3DError as exc:
        return Record3DUSBStatus(
            dependency_available=True,
            error_message=str(exc),
        )


__all__ = [
    "Record3DCameraPose",
    "Record3DConnectionError",
    "Record3DDependencyError",
    "Record3DDevice",
    "Record3DDeviceType",
    "Record3DError",
    "Record3DFrame",
    "Record3DIntrinsicMatrix",
    "Record3DPreviewApp",
    "Record3DPreviewConfig",
    "Record3DStreamConfig",
    "Record3DStreamSession",
    "Record3DTimeoutError",
    "Record3DUSBStatus",
    "probe_record3d_usb_status",
]
