"""Shared normalized-store RGB raster preprocessing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from prml_vslam.interfaces import CameraIntrinsics
from prml_vslam.interfaces.camera import scale_camera_intrinsics


@dataclass(frozen=True)
class RgbPreprocessingResult:
    rgb: NDArray[np.uint8]
    scale_x: float
    scale_y: float
    original_width: int
    original_height: int

    @property
    def width(self) -> int:
        return int(self.rgb.shape[1])

    @property
    def height(self) -> int:
        return int(self.rgb.shape[0])


def preprocess_rgb_for_normalized_store(
    image_rgb: NDArray[np.uint8],
    *,
    max_width_px: int,
    dimension_multiple: int,
) -> RgbPreprocessingResult:
    """Downscale one RGB raster into the canonical normalized-store cache size."""
    if max_width_px < 1:
        raise ValueError("max_width_px must be >= 1.")
    if dimension_multiple < 1:
        raise ValueError("dimension_multiple must be >= 1.")
    source_height, source_width = image_rgb.shape[:2]
    if source_width <= 0 or source_height <= 0:
        raise ValueError("RGB raster must be non-empty.")

    target_width = _round_down_to_multiple(min(source_width, max_width_px), dimension_multiple)
    scale = target_width / source_width
    target_height = _round_to_multiple(source_height * scale, dimension_multiple)
    resized = cv2.resize(image_rgb, (target_width, target_height), interpolation=cv2.INTER_AREA)
    return RgbPreprocessingResult(
        rgb=np.asarray(resized, dtype=np.uint8),
        scale_x=target_width / source_width,
        scale_y=target_height / source_height,
        original_width=source_width,
        original_height=source_height,
    )


def resize_depth_to_rgb_preprocessing(depth: NDArray, preprocessing: RgbPreprocessingResult) -> NDArray:
    """Resize a depth raster to the preprocessed RGB shape without changing depth units."""
    resized = cv2.resize(depth, (preprocessing.width, preprocessing.height), interpolation=cv2.INTER_NEAREST)
    return np.asarray(resized, dtype=depth.dtype)


def scale_intrinsics_for_rgb_preprocessing(
    intrinsics: CameraIntrinsics,
    preprocessing: RgbPreprocessingResult,
) -> CameraIntrinsics:
    """Scale camera intrinsics into the preprocessed normalized-store raster."""
    return scale_camera_intrinsics(
        intrinsics,
        scale_x=preprocessing.scale_x,
        scale_y=preprocessing.scale_y,
        width_px=preprocessing.width,
        height_px=preprocessing.height,
    )


def write_preprocessed_rgb_png(path: Path, image_rgb: NDArray[np.uint8]) -> None:
    """Write a normalized-store RGB PNG with high compression."""
    if not cv2.imwrite(str(path), cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 9]):
        raise RuntimeError(f"Failed to write RGB PNG: {path}")


def _round_down_to_multiple(value: int, multiple: int) -> int:
    if value < multiple:
        return max(1, value)
    return max(multiple, int(value) // multiple * multiple)


def _round_to_multiple(value: float, multiple: int) -> int:
    if value < multiple:
        return max(1, int(round(value)))
    return max(multiple, int(round(value / multiple)) * multiple)
