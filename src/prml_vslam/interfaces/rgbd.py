"""Shared posed RGB-D observation contracts.

This module owns the strict RGB-D observation boundary used by reference
reconstruction and future SLAM-derived reconstruction stages. Unlike
``FramePacket``, these DTOs require complete geometry inputs: a metric depth
raster, matching camera intrinsics, and an explicit ``T_world_camera`` pose.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Self

import numpy as np
from numpy.typing import NDArray
from pydantic import AliasChoices, Field, model_validator

from prml_vslam.utils import BaseData

from .camera import CameraIntrinsics
from .transforms import FrameTransform

RGBD_OBSERVATION_SEQUENCE_FORMAT = "rgbd_observation_sequence.v1"


class RgbdObservationProvenance(BaseData):
    """Describe where one normalized posed RGB-D observation came from."""

    source_id: str = ""
    """Stable source family such as ``tum_rgbd`` or ``vista``."""

    dataset_id: str = ""
    """Dataset family when the observation came from a repository dataset."""

    method_id: str = ""
    """Method/backend id when the observation came from a SLAM backend."""

    sequence_id: str = ""
    """Dataset-, source-, or run-specific sequence identifier."""

    sequence_name: str = ""
    """Human-readable source sequence name."""

    pose_source: str = ""
    """Pose provider used to build ``T_world_camera``."""

    world_frame: str = "world"
    """World frame represented by ``T_world_camera.target_frame``."""

    raster_space: str = "source"
    """Raster space for RGB, depth, and intrinsics, such as ``source`` or ``vista_model``."""

    source_frame_index: int | None = None
    """Index in the source frame stream before any repository sampling."""

    keyframe_index: int | None = None
    """Accepted SLAM keyframe index when the observation came from a backend update."""


class RgbdObservation(BaseData):
    """Represent one complete posed RGB-D observation for reconstruction.

    ``T_world_camera`` follows the repository camera-pose convention:
    world <- camera. ``image_rgb``, ``depth_map_m``, and
    ``camera_intrinsics`` must describe the same raster.
    """

    seq: int = Field(ge=0)
    """Monotonic observation index within the selected sequence."""

    timestamp_ns: int = Field(ge=0)
    """Source-aligned observation timestamp in nanoseconds."""

    T_world_camera: FrameTransform = Field(
        validation_alias=AliasChoices("T_world_camera", "pose_world_camera"),
    )
    """Canonical camera pose using world <- camera semantics."""

    camera_intrinsics: CameraIntrinsics
    """Pinhole intrinsics for the RGB-D raster."""

    depth_map_m: NDArray[np.float32]
    """HxW metric depth raster in meters."""

    image_rgb: NDArray[np.uint8] | None = None
    """Optional HxWx3 RGB image aligned with ``depth_map_m``."""

    provenance: RgbdObservationProvenance = Field(default_factory=RgbdObservationProvenance)
    """Typed source and frame-semantics provenance."""

    @property
    def pose_world_camera(self) -> FrameTransform:
        """Return the legacy pose field name during the reconstruction DTO migration."""
        return self.T_world_camera

    @model_validator(mode="after")
    def validate_raster_contract(self) -> Self:
        """Validate the geometry and raster invariants required by TSDF fusion."""
        depth = np.asarray(self.depth_map_m, dtype=np.float32)
        if depth.ndim != 2:
            raise ValueError(f"Expected a 2D depth map, got shape {depth.shape}.")
        if not np.all(np.isfinite(depth)):
            raise ValueError("Depth map must contain only finite values.")
        if np.any(depth < 0.0):
            raise ValueError("Depth map must not contain negative values.")

        height_px, width_px = depth.shape
        if self.camera_intrinsics.width_px is not None and self.camera_intrinsics.width_px != width_px:
            raise ValueError(
                f"Intrinsics width_px={self.camera_intrinsics.width_px} does not match depth width {width_px}."
            )
        if self.camera_intrinsics.height_px is not None and self.camera_intrinsics.height_px != height_px:
            raise ValueError(
                f"Intrinsics height_px={self.camera_intrinsics.height_px} does not match depth height {height_px}."
            )

        if self.image_rgb is not None:
            image = np.asarray(self.image_rgb, dtype=np.uint8)
            expected_shape = (height_px, width_px, 3)
            if image.shape != expected_shape:
                raise ValueError(f"Expected RGB image shape {expected_shape}, got {image.shape}.")

        if self.T_world_camera.target_frame != self.provenance.world_frame:
            self.provenance = self.provenance.model_copy(update={"world_frame": self.T_world_camera.target_frame})
        return self


class RgbdObservationIndexEntry(BaseData):
    """One row in a durable RGB-D observation sequence index."""

    seq: int = Field(ge=0)
    """Monotonic observation index."""

    timestamp_ns: int = Field(ge=0)
    """Observation timestamp in nanoseconds."""

    rgb_path: Path | None = None
    """Path to an optional RGB payload, relative to the sequence payload root."""

    depth_path: Path
    """Path to the depth payload, relative to the sequence payload root."""

    depth_scale_to_m: float = Field(default=1.0, gt=0.0)
    """Multiplier that converts the stored depth payload values into meters."""

    T_world_camera: FrameTransform = Field(
        validation_alias=AliasChoices("T_world_camera", "pose_world_camera"),
    )
    """Canonical camera pose using world <- camera semantics."""

    camera_intrinsics: CameraIntrinsics
    """Pinhole intrinsics for this row's RGB-D raster."""

    provenance: RgbdObservationProvenance = Field(default_factory=RgbdObservationProvenance)
    """Row-level source provenance."""


class RgbdObservationSequenceIndex(BaseData):
    """Durable ``rgbd_observation_sequence.v1`` index payload."""

    format_version: Literal["rgbd_observation_sequence.v1"] = RGBD_OBSERVATION_SEQUENCE_FORMAT
    """Stable schema discriminator for durable RGB-D observation indexes."""

    source_id: str
    """Stable source family for this sequence."""

    sequence_id: str
    """Dataset-, source-, or run-specific sequence identifier."""

    world_frame: str = "world"
    """World frame shared by the sequence observations."""

    raster_space: str = "source"
    """Raster space shared by the sequence observations."""

    observation_count: int = Field(ge=0)
    """Expected number of rows in the index."""

    rows: list[RgbdObservationIndexEntry] = Field(default_factory=list)
    """Observation rows with payload refs and per-frame geometry."""

    @model_validator(mode="after")
    def validate_observation_count(self) -> Self:
        """Ensure the declared observation count matches the row payload."""
        if self.observation_count != len(self.rows):
            raise ValueError(
                f"RgbdObservationSequenceIndex observation_count={self.observation_count} "
                f"does not match {len(self.rows)} rows."
            )
        return self


class RgbdObservationSequenceRef(BaseData):
    """Durable descriptor for a prepared RGB-D observation sequence."""

    format_version: Literal["rgbd_observation_sequence.v1"] = RGBD_OBSERVATION_SEQUENCE_FORMAT
    """Stable schema discriminator for the referenced index."""

    source_id: str
    """Stable source family for this sequence."""

    sequence_id: str
    """Dataset-, source-, or run-specific sequence identifier."""

    index_path: Path
    """Path to the durable ``RgbdObservationSequenceIndex`` JSON payload."""

    payload_root: Path
    """Root directory used to resolve relative RGB/depth payload paths."""

    observation_count: int = Field(ge=0)
    """Expected number of observations available through the index."""

    world_frame: str = "world"
    """World frame shared by observations."""

    raster_space: str = "source"
    """Raster space shared by observations."""


__all__ = [
    "RGBD_OBSERVATION_SEQUENCE_FORMAT",
    "RgbdObservation",
    "RgbdObservationIndexEntry",
    "RgbdObservationProvenance",
    "RgbdObservationSequenceIndex",
    "RgbdObservationSequenceRef",
]
