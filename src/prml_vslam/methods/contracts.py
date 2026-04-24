"""Method-owned SLAM semantic DTOs."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.interfaces.camera import CameraIntrinsics
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.utils import BaseData


class SlamUpdate(BaseData):
    """Represent one method-owned incremental SLAM update."""

    seq: int
    timestamp_ns: int
    source_seq: int | None = None
    source_timestamp_ns: int | None = None
    is_keyframe: bool = False
    keyframe_index: int | None = None
    pose: FrameTransform | None = None
    num_sparse_points: int = 0
    num_dense_points: int = 0
    pointmap: NDArray[np.float32] | None = None
    camera_intrinsics: CameraIntrinsics | None = None
    image_rgb: NDArray[np.uint8] | None = None
    depth_map: NDArray[np.float32] | None = None
    preview_rgb: NDArray[np.uint8] | None = None
    pose_updated: bool = False
    backend_warnings: list[str] = Field(default_factory=list)


class SlamArtifacts(BaseData):
    """Normalize durable outputs produced by a SLAM backend.

    The bundle is the scientific handoff from method execution into evaluation,
    alignment, reconstruction, artifact inspection, and reporting.
    """

    trajectory_tum: ArtifactRef
    sparse_points_ply: ArtifactRef | None = None
    dense_points_ply: ArtifactRef | None = None
    extras: dict[str, ArtifactRef] = Field(default_factory=dict)


__all__ = ["SlamArtifacts", "SlamUpdate"]
