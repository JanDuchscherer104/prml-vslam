"""Metadata parsing and packet decoding for Record3D Wi-Fi streaming."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from prml_vslam.utils import BaseData

from .record3d import (
    Record3DError,
    Record3DFramePacket,
    Record3DIntrinsicMatrix,
    Record3DTransportId,
)


class Record3DWiFiMetadata(BaseData):
    """Typed metadata returned by the Record3D Wi-Fi HTTP API."""

    device_address: str
    """Normalized device base URL used for signaling."""

    intrinsic_matrix: Record3DIntrinsicMatrix | None = None
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
            intrinsic_matrix=_parse_intrinsic_matrix(payload),
            original_width=original_width,
            original_height=original_height,
            depth_max_meters=_parse_depth_range(payload),
            raw_metadata=dict(payload),
        )


def _parse_intrinsic_matrix(payload: dict[str, Any]) -> Record3DIntrinsicMatrix | None:
    raw_matrix = payload.get("K")
    if raw_matrix is None:
        return None

    matrix = np.asarray(raw_matrix, dtype=np.float64)
    if matrix.shape == (9,):
        matrix = matrix.reshape(3, 3)
    if matrix.shape != (3, 3):
        raise Record3DError(
            "Record3D Wi-Fi metadata field `K` must be a flat 9-vector or a 3x3 matrix, "
            f"but received shape {tuple(matrix.shape)}."
        )

    return Record3DIntrinsicMatrix(
        fx=float(matrix[0, 0]),
        fy=float(matrix[1, 1]),
        tx=float(matrix[0, 2]),
        ty=float(matrix[1, 2]),
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
    normalized = depth_rgb.astype(np.float32) / 255.0
    red = normalized[..., 0]
    green = normalized[..., 1]
    blue = normalized[..., 2]

    maximum = np.max(normalized, axis=2)
    minimum = np.min(normalized, axis=2)
    delta = maximum - minimum

    hue = np.zeros_like(maximum, dtype=np.float32)
    has_delta = delta > 0.0
    red_max = has_delta & (maximum == red)
    green_max = has_delta & (maximum == green)
    blue_max = has_delta & (maximum == blue)

    hue[red_max] = np.mod((green[red_max] - blue[red_max]) / delta[red_max], 6.0) / 6.0
    hue[green_max] = (((blue[green_max] - red[green_max]) / delta[green_max]) + 2.0) / 6.0
    hue[blue_max] = (((red[blue_max] - green[blue_max]) / delta[blue_max]) + 4.0) / 6.0
    depth = np.where(hue <= 1e-6, depth_max_meters, depth_max_meters * hue)
    return depth.astype(np.float32)


def record3d_wifi_packet_from_video_frame(
    video_frame: Any,
    *,
    metadata: Record3DWiFiMetadata,
) -> Record3DFramePacket:
    """Convert one Record3D composite WebRTC frame into the shared packet contract."""
    composite_frame = np.asarray(video_frame.to_ndarray(format="rgb24"), dtype=np.uint8)
    if composite_frame.ndim != 3 or composite_frame.shape[2] != 3:
        raise Record3DError("Record3D Wi-Fi video frames must be RGB images with shape `(height, width, 3)`.")
    if composite_frame.shape[1] < 2:
        raise Record3DError("Record3D Wi-Fi composite frames must contain both depth and RGB halves.")

    half_width = composite_frame.shape[1] // 2
    packet_metadata = dict(metadata.raw_metadata)
    packet_metadata["device_address"] = metadata.device_address
    if metadata.original_width is not None and metadata.original_height is not None:
        packet_metadata["original_size"] = [metadata.original_width, metadata.original_height]

    return Record3DFramePacket(
        transport=Record3DTransportId.WIFI,
        rgb=composite_frame[:, -half_width:, :],
        depth=decode_record3d_wifi_depth(
            composite_frame[:, :half_width, :],
            depth_max_meters=metadata.depth_max_meters,
        ),
        intrinsic_matrix=metadata.intrinsic_matrix,
        uncertainty=None,
        metadata=packet_metadata,
        arrival_timestamp_s=time.time(),
    )
