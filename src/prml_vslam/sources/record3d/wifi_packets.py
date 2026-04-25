"""Metadata parsing and packet decoding for Record3D Wi-Fi streaming."""

from __future__ import annotations

import time
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from prml_vslam.interfaces import CameraIntrinsics, Observation, ObservationProvenance
from prml_vslam.sources.contracts import Record3DTransportId
from prml_vslam.utils import BaseData


class Record3DWiFiMetadata(BaseData):
    """Typed metadata returned by the Record3D Wi-Fi HTTP API."""

    device_address: str
    """Normalized device base URL used for signaling."""

    intrinsics: CameraIntrinsics | None = None
    """Camera intrinsic matrix reported by the device when available."""

    original_width: int | None = None
    """Original composite-frame width reported by the device."""

    original_height: int | None = None
    """Original composite-frame height reported by the device."""

    depth_max_meters: float = 3.0
    """Depth range upper bound used by the HSV transport encoding."""

    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    """Raw metadata payload returned by the Record3D endpoint."""

    @classmethod
    def from_api_payload(cls, *, device_address: str, payload: dict[str, Any]) -> Record3DWiFiMetadata:
        """Parse the raw Record3D metadata payload."""
        original_width, original_height = _parse_original_size(payload)
        return cls(
            device_address=device_address,
            intrinsics=_parse_intrinsic_matrix(
                payload,
                width_px=original_width,
                height_px=original_height,
            ),
            original_width=original_width,
            original_height=original_height,
            depth_max_meters=_parse_depth_range(payload),
            raw_metadata=dict(payload),
        )


def _parse_intrinsic_matrix(
    payload: dict[str, Any],
    *,
    width_px: int | None,
    height_px: int | None,
) -> CameraIntrinsics | None:
    raw_matrix = payload.get("K")
    if raw_matrix is None:
        return None

    matrix = np.asarray(raw_matrix, dtype=np.float64)
    if matrix.shape == (9,):
        matrix = matrix.reshape(3, 3)
    if matrix.shape != (3, 3):
        raise RuntimeError(
            "Record3D Wi-Fi metadata field `K` must be a flat 9-vector or a 3x3 matrix, "
            f"but received shape {tuple(matrix.shape)}."
        )

    return CameraIntrinsics(
        fx=float(matrix[0, 0]),
        fy=float(matrix[1, 1]),
        cx=float(matrix[0, 2]),
        cy=float(matrix[1, 2]),
        width_px=width_px,
        height_px=height_px,
    )


def _parse_original_size(payload: dict[str, Any]) -> tuple[int | None, int | None]:
    raw_size = payload.get("originalSize")
    if isinstance(raw_size, dict):
        width = raw_size.get("width")
        height = raw_size.get("height")
    elif isinstance(raw_size, list | tuple) and len(raw_size) >= 2:
        width, height = raw_size[:2]
    else:
        width = payload.get("width") or payload.get("rgbWidth")
        height = payload.get("height") or payload.get("rgbHeight")
    return (int(width) if width is not None else None, int(height) if height is not None else None)


def _parse_depth_range(payload: dict[str, Any]) -> float:
    for key in ("depthMaxMeters", "depth_max_meters", "maxDepthMeters", "maxDepth"):
        value = payload.get(key)
        if value is not None:
            return float(value)
    return 3.0


def decode_record3d_wifi_depth(
    depth_rgb: NDArray[np.uint8],
    *,
    depth_max_meters: float,
) -> NDArray[np.float32]:
    """Decode the HSV-encoded Record3D Wi-Fi depth half into a depth map."""
    hue = cv2.cvtColor(depth_rgb, cv2.COLOR_RGB2HSV)[..., 0].astype(np.float32) / 180.0
    depth = np.where(hue <= 1e-6, depth_max_meters, depth_max_meters * hue)
    return depth.astype(np.float32, copy=False)


def record3d_wifi_observation_from_video_frame(
    video_frame: Any,
    *,
    metadata: Record3DWiFiMetadata,
    seq: int,
    timestamp_ns: int | None = None,
) -> Observation:
    """Convert one Record3D composite WebRTC frame into the shared source contract."""
    composite_frame = np.asarray(video_frame.to_ndarray(format="rgb24"), dtype=np.uint8)
    if composite_frame.ndim != 3 or composite_frame.shape[2] != 3:
        raise RuntimeError("Record3D Wi-Fi video frames must be RGB images with shape `(height, width, 3)`.")
    if composite_frame.shape[1] < 2:
        raise RuntimeError("Record3D Wi-Fi composite frames must contain both depth and RGB halves.")

    half_width = composite_frame.shape[1] // 2
    if timestamp_ns is None:
        timestamp_ns = time.time_ns()

    return Observation(
        seq=seq,
        timestamp_ns=timestamp_ns,
        source_frame_index=seq,
        arrival_timestamp_s=timestamp_ns / 1e9,
        rgb=composite_frame[:, -half_width:, :],
        intrinsics=metadata.intrinsics,
        confidence=None,
        provenance=ObservationProvenance(
            source_id="record3d",
            transport=Record3DTransportId.WIFI.value,
            device_address=metadata.device_address,
            original_width=metadata.original_width,
            original_height=metadata.original_height,
        ),
    )
