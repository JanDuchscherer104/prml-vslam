"""Shared RDF observation contracts.

This module owns the single observation boundary used by live sources, SLAM
streaming, durable RGB-D sequences, and reconstruction. All metric geometry in
an :class:`Observation` is expressed in the fixed RDF camera frame
``camera_rdf``. World placement is represented only by
``T_world_camera: world <- camera_rdf``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Self

import numpy as np
from numpy.typing import NDArray
from pydantic import ConfigDict, Field, model_validator

from prml_vslam.utils import BaseData

from .camera import CameraIntrinsics
from .transforms import FrameTransform

OBSERVATION_SEQUENCE_FORMAT = "observation_sequence.v1"
CAMERA_RDF_FRAME = "camera_rdf"


class ObservationProvenance(BaseData):
    """Describe where one normalized observation came from."""

    source_id: str = ""
    dataset_id: str = ""
    method_id: str = ""
    sequence_id: str = ""
    sequence_name: str = ""
    pose_source: str = ""
    world_frame: str = "world"
    raster_space: str = "source"
    source_frame_index: int | None = None
    keyframe_index: int | None = None
    transport: str = ""
    device_type: str = ""
    device_address: str = ""
    video_rotation_degrees: int = 0
    original_width: int | None = None
    original_height: int | None = None

    def compact_payload(self) -> dict[str, object]:
        """Return a compact JSON-ready subset for UI details and telemetry sinks."""
        payload = self.model_dump(mode="json", exclude_none=True)
        return {
            key: value
            for key, value in payload.items()
            if value not in ("", [], {}, 0)
            and (key, value) not in {("world_frame", "world"), ("raster_space", "source")}
        }


class Observation(BaseData):
    """Represent one live, replayed, or file-backed RDF camera observation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    seq: int = Field(ge=0)
    timestamp_ns: int = Field(ge=0)
    provenance: ObservationProvenance

    source_frame_index: int | None = None
    loop_index: int = Field(default=0, ge=0)
    arrival_timestamp_s: float | None = None
    camera_frame: Literal["camera_rdf"] = CAMERA_RDF_FRAME

    rgb: NDArray[np.uint8] | None = None
    depth_m: NDArray[np.float32] | None = None
    confidence: NDArray[np.float32] | None = None
    pointmap_xyz: NDArray[np.float32] | None = None
    point_cloud_xyz: NDArray[np.float32] | None = None
    point_cloud_rgb: NDArray[np.uint8] | None = None
    intrinsics: CameraIntrinsics | None = None
    T_world_camera: FrameTransform | None = None

    @model_validator(mode="after")
    def validate_observation_contract(self) -> Self:
        """Validate RDF geometry, raster alignment, and pose requirements."""
        if self.T_world_camera is not None:
            if self.T_world_camera.source_frame != CAMERA_RDF_FRAME:
                raise ValueError("Observation.T_world_camera.source_frame must be 'camera_rdf'.")
            if self.T_world_camera.target_frame != self.provenance.world_frame:
                self.provenance = self.provenance.model_copy(update={"world_frame": self.T_world_camera.target_frame})

        rgb_shape = self._normalize_rgb()
        depth_shape = self._normalize_depth()
        confidence_shape = self._normalize_confidence()
        pointmap_shape = self._normalize_pointmap()
        self._normalize_point_cloud()

        geometry_present = self.depth_m is not None or self.pointmap_xyz is not None or self.point_cloud_xyz is not None
        if geometry_present and self.T_world_camera is None:
            raise ValueError("Metric observation geometry requires T_world_camera.")
        if (self.depth_m is not None or self.pointmap_xyz is not None) and self.intrinsics is None:
            raise ValueError("Raster metric observation geometry requires intrinsics.")

        raster_shape = depth_shape or pointmap_shape
        if confidence_shape is not None:
            if depth_shape is None:
                raise ValueError("Observation.confidence requires depth_m.")
            if confidence_shape != depth_shape:
                raise ValueError(f"Confidence shape {confidence_shape} does not match depth shape {depth_shape}.")
        if depth_shape is not None and pointmap_shape is not None and depth_shape != pointmap_shape:
            raise ValueError(f"Pointmap shape {pointmap_shape} does not match depth shape {depth_shape}.")
        if raster_shape is not None and rgb_shape is not None and rgb_shape != raster_shape:
            raise ValueError(f"RGB raster shape {rgb_shape} does not match metric raster shape {raster_shape}.")
        if raster_shape is not None and self.intrinsics is not None:
            height_px, width_px = raster_shape
            if self.intrinsics.width_px is not None and self.intrinsics.width_px != width_px:
                raise ValueError(
                    f"Intrinsics width_px={self.intrinsics.width_px} does not match raster width {width_px}."
                )
            if self.intrinsics.height_px is not None and self.intrinsics.height_px != height_px:
                raise ValueError(
                    f"Intrinsics height_px={self.intrinsics.height_px} does not match raster height {height_px}."
                )
        return self

    def _normalize_rgb(self) -> tuple[int, int] | None:
        if self.rgb is None:
            return None
        rgb = np.asarray(self.rgb, dtype=np.uint8)
        if rgb.ndim != 3 or rgb.shape[2] != 3:
            raise ValueError(f"Expected RGB image shape (H, W, 3), got {rgb.shape}.")
        object.__setattr__(self, "rgb", rgb)
        return rgb.shape[:2]

    def _normalize_depth(self) -> tuple[int, int] | None:
        if self.depth_m is None:
            return None
        depth = np.asarray(self.depth_m, dtype=np.float32)
        if depth.ndim != 2:
            raise ValueError(f"Expected depth map shape (H, W), got {depth.shape}.")
        if not np.all(np.isfinite(depth)):
            raise ValueError("Depth map must contain only finite values.")
        if np.any(depth < 0.0):
            raise ValueError("Depth map must not contain negative values.")
        object.__setattr__(self, "depth_m", depth)
        return depth.shape

    def _normalize_confidence(self) -> tuple[int, int] | None:
        if self.confidence is None:
            return None
        confidence = np.asarray(self.confidence, dtype=np.float32)
        if confidence.ndim != 2:
            raise ValueError(f"Expected confidence shape (H, W), got {confidence.shape}.")
        if not np.all(np.isfinite(confidence)):
            raise ValueError("Confidence map must contain only finite values.")
        object.__setattr__(self, "confidence", confidence)
        return confidence.shape

    def _normalize_pointmap(self) -> tuple[int, int] | None:
        if self.pointmap_xyz is None:
            return None
        pointmap = np.asarray(self.pointmap_xyz, dtype=np.float32)
        if pointmap.ndim != 3 or pointmap.shape[2] != 3:
            raise ValueError(f"Expected pointmap shape (H, W, 3), got {pointmap.shape}.")
        if not np.all(np.isfinite(pointmap)):
            raise ValueError("Pointmap samples must contain only finite values.")
        object.__setattr__(self, "pointmap_xyz", pointmap)
        return pointmap.shape[:2]

    def _normalize_point_cloud(self) -> None:
        if self.point_cloud_xyz is None:
            if self.point_cloud_rgb is not None:
                raise ValueError("Observation.point_cloud_rgb requires point_cloud_xyz.")
            return
        points = np.asarray(self.point_cloud_xyz, dtype=np.float32)
        if points.ndim != 2 or points.shape[1] != 3:
            raise ValueError(f"Expected point cloud shape (N, 3), got {points.shape}.")
        if not np.all(np.isfinite(points)):
            raise ValueError("Point cloud samples must contain only finite values.")
        object.__setattr__(self, "point_cloud_xyz", points)
        if self.point_cloud_rgb is not None:
            colors = np.asarray(self.point_cloud_rgb, dtype=np.uint8)
            if colors.shape != points.shape:
                raise ValueError(f"Expected point cloud colors shape {points.shape}, got {colors.shape}.")
            object.__setattr__(self, "point_cloud_rgb", colors)


class ObservationIndexEntry(BaseData):
    """One row in a durable observation sequence index."""

    seq: int = Field(ge=0)
    timestamp_ns: int = Field(ge=0)
    rgb_path: Path | None = None
    depth_path: Path | None = None
    depth_scale_to_m: float = Field(default=1.0, gt=0.0)
    T_world_camera: FrameTransform | None = None
    intrinsics: CameraIntrinsics | None = None
    camera_frame: Literal["camera_rdf"] = CAMERA_RDF_FRAME
    provenance: ObservationProvenance


class ObservationSequenceIndex(BaseData):
    """Durable ``observation_sequence.v1`` index payload."""

    format_version: Literal["observation_sequence.v1"] = OBSERVATION_SEQUENCE_FORMAT
    source_id: str
    sequence_id: str
    world_frame: str = "world"
    raster_space: str = "source"
    observation_count: int = Field(ge=0)
    rows: list[ObservationIndexEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_observation_count(self) -> Self:
        """Ensure the declared observation count matches the row payload."""
        if self.observation_count != len(self.rows):
            raise ValueError(
                f"ObservationSequenceIndex observation_count={self.observation_count} "
                f"does not match {len(self.rows)} rows."
            )
        return self


class ObservationSequenceRef(BaseData):
    """Durable descriptor for a prepared observation sequence."""

    format_version: Literal["observation_sequence.v1"] = OBSERVATION_SEQUENCE_FORMAT
    source_id: str
    sequence_id: str
    index_path: Path
    payload_root: Path
    observation_count: int = Field(ge=0)
    world_frame: str = "world"
    raster_space: str = "source"


__all__ = [
    "CAMERA_RDF_FRAME",
    "OBSERVATION_SEQUENCE_FORMAT",
    "Observation",
    "ObservationIndexEntry",
    "ObservationProvenance",
    "ObservationSequenceIndex",
    "ObservationSequenceRef",
]
