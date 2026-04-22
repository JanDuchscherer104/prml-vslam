"""Canonical camera-intrinsics DTO shared across the package.

This module owns :class:`CameraIntrinsics`, the repo-wide representation of a
pinhole camera model plus optional raster and distortion metadata. Dataset
loaders, IO transports, method wrappers, visualization helpers, and the
pipeline all use this DTO when they need a shared description of one camera
raster. It does not own frame transforms or runtime packets; see
:mod:`prml_vslam.interfaces.transforms` and :mod:`prml_vslam.interfaces.runtime`
for those boundaries.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Self

import numpy as np
import yaml
from numpy.typing import NDArray
from pydantic import ConfigDict, Field

from prml_vslam.utils.base_data import BaseData


class CameraIntrinsics(BaseData):
    """Describe one camera raster in a backend- and dataset-neutral way.

    Use this DTO whenever a package boundary needs stable focal lengths,
    principal point, optional raster size, and optional distortion metadata
    without depending on an upstream-specific calibration format. The object is
    shared by :class:`prml_vslam.interfaces.FramePacket`,
    :class:`prml_vslam.datasets.contracts.AdvioManifestAssets`, and method live
    updates such as :class:`prml_vslam.methods.updates.SlamUpdate`.
    """

    model_config = ConfigDict(frozen=True)

    fx: float
    fy: float
    cx: float
    cy: float
    width_px: int | None = None
    height_px: int | None = None
    distortion_model: str | None = None
    distortion_coefficients: tuple[float, ...] = ()

    def as_matrix(self) -> NDArray[np.float64]:
        """Return the canonical 3x3 pinhole matrix for downstream math."""
        return np.array(
            [
                [self.fx, 0.0, self.cx],
                [0.0, self.fy, self.cy],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

    def to_latex(self) -> str:
        """Render the shared intrinsics matrix in the compact LaTeX form used by UI surfaces."""
        return (
            "K = \\begin{bmatrix}"
            f"{self.fx:.3f} & 0.000 & {self.cx:.3f} \\\\ "
            f"0.000 & {self.fy:.3f} & {self.cy:.3f} \\\\ "
            "0.000 & 0.000 & 1.000"
            "\\end{bmatrix}"
        )

    @classmethod
    def from_matrix(
        cls,
        matrix: NDArray[np.float64] | list[list[float]],
        *,
        width_px: int | None = None,
        height_px: int | None = None,
        distortion_model: str | None = None,
        distortion_coefficients: Sequence[float] = (),
    ) -> Self:
        """Build the shared DTO from a conventional 3x3 row-major camera matrix."""
        matrix_array = np.asarray(matrix, dtype=np.float64)
        if matrix_array.shape != (3, 3):
            raise ValueError(f"Expected a 3x3 intrinsic matrix, got shape {matrix_array.shape}.")
        return cls(
            fx=float(matrix_array[0, 0]),
            fy=float(matrix_array[1, 1]),
            cx=float(matrix_array[0, 2]),
            cy=float(matrix_array[1, 2]),
            width_px=width_px,
            height_px=height_px,
            distortion_model=distortion_model,
            distortion_coefficients=tuple(float(value) for value in distortion_coefficients),
        )

    @classmethod
    def from_column_major_flat_k(
        cls,
        values: Sequence[float],
        **kwargs: int | str | Sequence[float] | None,
    ) -> Self:
        """Build the shared DTO from a flat 9-value column-major payload."""
        if len(values) != 9:
            raise ValueError(f"Expected 9 values for a flat intrinsic matrix, got {len(values)}.")
        matrix = np.asarray(values, dtype=np.float64).reshape((3, 3), order="F")
        return cls.from_matrix(matrix, **kwargs)

    @classmethod
    def from_row_major_flat_k(
        cls,
        values: Sequence[float],
        **kwargs: int | str | Sequence[float] | None,
    ) -> Self:
        """Build the shared DTO from a flat 9-value row-major payload."""
        if len(values) != 9:
            raise ValueError(f"Expected 9 values for a flat intrinsic matrix, got {len(values)}.")
        matrix = np.asarray(values, dtype=np.float64).reshape((3, 3))
        return cls.from_matrix(matrix, **kwargs)


class CameraIntrinsicsSample(BaseData):
    """One camera model sample in a per-frame or per-keyframe intrinsics series."""

    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=0)
    """Monotonic sample index in the series."""

    intrinsics: CameraIntrinsics
    """Camera model for this sample's raster."""

    keyframe_index: int | None = Field(default=None, ge=0)
    """Backend keyframe index when the sample comes from a SLAM backend."""

    timestamp_ns: int | None = Field(default=None, ge=0)
    """Source-aligned timestamp in nanoseconds, when known."""

    view_name: str = ""
    """Backend view name, when available."""


class CameraIntrinsicsSeries(BaseData):
    """Typed artifact for a sequence of camera intrinsics in one raster space."""

    model_config = ConfigDict(frozen=True)

    raster_space: str
    """Raster space represented by every sample, such as `source` or `vista_model`."""

    source: str
    """Source artifact or subsystem that produced the series."""

    method_id: str = ""
    """Method/backend id when the series is method-derived."""

    width_px: int | None = Field(default=None, ge=0)
    """Shared raster width in pixels, when known."""

    height_px: int | None = Field(default=None, ge=0)
    """Shared raster height in pixels, when known."""

    samples: list[CameraIntrinsicsSample] = Field(default_factory=list)
    """Ordered per-frame or per-keyframe camera samples."""

    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    """Small JSON-friendly provenance values that do not deserve dedicated fields."""

    @classmethod
    def from_matrices(
        cls,
        matrices: NDArray[np.float64],
        *,
        raster_space: str,
        source: str,
        method_id: str = "",
        width_px: int | None = None,
        height_px: int | None = None,
        keyframe_indices: Sequence[int | None] | None = None,
        timestamps_ns: Sequence[int | None] | None = None,
        view_names: Sequence[str] | None = None,
        metadata: dict[str, str | int | float | bool | None] | None = None,
    ) -> Self:
        """Build an intrinsics series from a stack of 3x3 camera matrices."""
        matrix_stack = np.asarray(matrices, dtype=np.float64)
        if matrix_stack.ndim != 3 or matrix_stack.shape[1:] != (3, 3):
            raise ValueError(f"Expected intrinsics shape (N, 3, 3), got {matrix_stack.shape}.")
        sample_count = len(matrix_stack)
        keyframe_values = _optional_sequence(keyframe_indices, count=sample_count, name="keyframe_indices")
        timestamp_values = _optional_sequence(timestamps_ns, count=sample_count, name="timestamps_ns")
        view_name_values = _optional_sequence(view_names, count=sample_count, name="view_names")
        return cls(
            raster_space=raster_space,
            source=source,
            method_id=method_id,
            width_px=width_px,
            height_px=height_px,
            samples=[
                CameraIntrinsicsSample(
                    index=index,
                    keyframe_index=keyframe_values[index],
                    timestamp_ns=timestamp_values[index],
                    view_name="" if view_name_values[index] is None else view_name_values[index],
                    intrinsics=CameraIntrinsics.from_matrix(matrix, width_px=width_px, height_px=height_px),
                )
                for index, matrix in enumerate(matrix_stack)
            ],
            metadata={} if metadata is None else metadata,
        )


def _optional_sequence(
    values: Sequence[Any] | None,
    *,
    count: int,
    name: str,
) -> list[Any | None]:
    if values is None:
        return [None] * count
    if len(values) != count:
        raise ValueError(f"Expected {count} {name} values, got {len(values)}.")
    return list(values)


def load_camera_intrinsics_yaml(path: Path) -> CameraIntrinsics:
    """Load the repository's canonical single-camera intrinsics YAML schema."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected camera intrinsics YAML mapping at '{path}'.")
    cameras = payload.get("cameras")
    if not isinstance(cameras, list) or not cameras:
        raise ValueError(f"Expected non-empty `cameras` list in '{path}'.")
    first_camera = cameras[0]
    if not isinstance(first_camera, dict) or not isinstance(first_camera.get("camera"), dict):
        raise ValueError(f"Expected `cameras[0].camera` mapping in '{path}'.")
    camera = first_camera["camera"]
    intrinsics_payload = camera.get("intrinsics")
    if not isinstance(intrinsics_payload, dict) or not isinstance(intrinsics_payload.get("data"), list):
        raise ValueError(f"Expected `cameras[0].camera.intrinsics.data` list in '{path}'.")
    values = intrinsics_payload["data"]
    if len(values) != 4:
        raise ValueError(f"Expected four pinhole intrinsics values in '{path}', got {len(values)}.")
    fx, fy, cx, cy = values
    distortion = camera.get("distortion", {})
    distortion_model = distortion.get("type") if isinstance(distortion, dict) else None
    distortion_parameters = distortion.get("parameters", {}) if isinstance(distortion, dict) else {}
    distortion_data = distortion_parameters.get("data", ()) if isinstance(distortion_parameters, dict) else ()
    return CameraIntrinsics(
        fx=float(fx),
        fy=float(fy),
        cx=float(cx),
        cy=float(cy),
        width_px=int(camera["image_width"]),
        height_px=int(camera["image_height"]),
        distortion_model=distortion_model,
        distortion_coefficients=tuple(float(value) for value in distortion_data),
    )


def scale_camera_intrinsics(
    intrinsics: CameraIntrinsics,
    *,
    scale_x: float,
    scale_y: float,
    width_px: int | None = None,
    height_px: int | None = None,
) -> CameraIntrinsics:
    """Scale one pinhole camera model into a resized raster."""
    resolved_width = (
        width_px
        if width_px is not None
        else (None if intrinsics.width_px is None else int(round(intrinsics.width_px * scale_x)))
    )
    resolved_height = (
        height_px
        if height_px is not None
        else (None if intrinsics.height_px is None else int(round(intrinsics.height_px * scale_y)))
    )
    return intrinsics.model_copy(
        update={
            "fx": intrinsics.fx * scale_x,
            "fy": intrinsics.fy * scale_y,
            "cx": intrinsics.cx * scale_x,
            "cy": intrinsics.cy * scale_y,
            "width_px": resolved_width,
            "height_px": resolved_height,
        }
    )


def crop_camera_intrinsics(
    intrinsics: CameraIntrinsics,
    *,
    left_px: float,
    top_px: float,
    width_px: int | None = None,
    height_px: int | None = None,
) -> CameraIntrinsics:
    """Translate one pinhole camera model into a cropped raster."""
    return intrinsics.model_copy(
        update={
            "cx": intrinsics.cx - left_px,
            "cy": intrinsics.cy - top_px,
            "width_px": width_px,
            "height_px": height_px,
        }
    )


def center_crop_resize_intrinsics(
    intrinsics: CameraIntrinsics,
    *,
    output_width_px: int,
    output_height_px: int,
    border_x_px: int = 0,
    border_y_px: int = 0,
) -> CameraIntrinsics:
    """Project intrinsics through the center-crop-and-resize path used by ViSTA image-only preprocessing."""
    if intrinsics.width_px is None or intrinsics.height_px is None:
        raise ValueError("Center-crop resize requires source intrinsics with explicit width_px and height_px.")
    source_width = intrinsics.width_px
    source_height = intrinsics.height_px
    center_x = int(source_width / 2)
    center_y = int(source_height / 2)
    min_margin_x = min(center_x, source_width - center_x)
    min_margin_y = min(center_y, source_height - center_y)
    left = max(center_x - min_margin_x, border_x_px)
    top = max(center_y - min_margin_y, border_y_px)
    right = min(center_x + min_margin_x, source_width - border_x_px)
    bottom = min(center_y + min_margin_y, source_height - border_y_px)
    cropped_width = right - left
    cropped_height = bottom - top
    if cropped_width <= 0 or cropped_height <= 0:
        raise ValueError("Center crop produced an empty raster.")

    cropped = crop_camera_intrinsics(
        intrinsics,
        left_px=left,
        top_px=top,
        width_px=cropped_width,
        height_px=cropped_height,
    )
    scale = max(output_width_px / cropped_width, output_height_px / cropped_height) + 1e-8
    resized_width = int(np.floor(cropped_width * scale))
    resized_height = int(np.floor(cropped_height * scale))
    resized = scale_camera_intrinsics(
        cropped,
        scale_x=scale,
        scale_y=scale,
        width_px=resized_width,
        height_px=resized_height,
    )
    final_left = int(np.round(resized_width / 2 - output_width_px / 2))
    final_top = int(np.round(resized_height / 2 - output_height_px / 2))
    return crop_camera_intrinsics(
        resized,
        left_px=final_left,
        top_px=final_top,
        width_px=output_width_px,
        height_px=output_height_px,
    )


__all__ = [
    "CameraIntrinsics",
    "CameraIntrinsicsSample",
    "CameraIntrinsicsSeries",
    "center_crop_resize_intrinsics",
    "crop_camera_intrinsics",
    "load_camera_intrinsics_yaml",
    "scale_camera_intrinsics",
]
