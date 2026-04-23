"""Method-owned live SLAM semantic DTOs."""

from __future__ import annotations

from typing import Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

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


class PoseEstimated(BaseData):
    """Method semantic notice that a pose estimate is available."""

    kind: Literal["pose.estimated"] = "pose.estimated"
    seq: int
    timestamp_ns: int
    source_seq: int | None = None
    source_timestamp_ns: int | None = None
    pose: FrameTransform
    pose_updated: bool = True


class KeyframeAccepted(BaseData):
    """Method semantic notice that a backend accepted a keyframe."""

    kind: Literal["keyframe.accepted"] = "keyframe.accepted"
    seq: int
    timestamp_ns: int
    keyframe_index: int | None = None
    accepted_keyframe_count: int | None = None
    backend_fps: float | None = None


class MapStatsUpdated(BaseData):
    """Method semantic notice carrying live map-size telemetry."""

    kind: Literal["map.stats"] = "map.stats"
    seq: int
    timestamp_ns: int
    num_sparse_points: int = 0
    num_dense_points: int = 0


class BackendWarning(BaseData):
    """Non-fatal backend warning surfaced without failing the active run."""

    kind: Literal["backend.warning"] = "backend.warning"
    message: str
    seq: int | None = None
    timestamp_ns: int | None = None


class BackendError(BaseData):
    """Fatal or actionable backend error surfaced from method execution."""

    kind: Literal["backend.error"] = "backend.error"
    message: str
    seq: int | None = None
    timestamp_ns: int | None = None


class SessionClosed(BaseData):
    """Terminal backend-session notice listing newly available artifact keys."""

    kind: Literal["session.closed"] = "session.closed"
    artifact_keys: list[str] = Field(default_factory=list)


__all__ = [
    "BackendError",
    "BackendWarning",
    "KeyframeAccepted",
    "MapStatsUpdated",
    "PoseEstimated",
    "SessionClosed",
    "SlamUpdate",
]
