"""Typed message envelope and payload models for the pipeline runtime.

Both offline replay and streaming sessions use identical message types at stage
boundaries, making the same stage implementations reusable in both modes.

SE(3) poses are stored as nested lists for JSON/TOML serialisability inside
:class:`Envelope` payloads, and converted to/from **numpy (4, 4)** arrays via
:func:`pose_to_matrix` / :func:`pose_from_matrix` which delegate to
:mod:`pytransform3d`.
"""

from __future__ import annotations

import math
import time
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
from pydantic import Field, field_validator, model_validator
from pytransform3d import transformations as pt

from prml_vslam.utils import BaseConfig

# ---------------------------------------------------------------------------
# Helpers — convert between serialisable nested-list and numpy SE(3)
# ---------------------------------------------------------------------------


def pose_to_matrix(nested: list[list[float]]) -> npt.NDArray[np.float64]:
    """Convert a JSON-serialisable 4×4 nested list to a validated SE(3) matrix."""
    return pt.check_transform(np.asarray(nested, dtype=np.float64))


def pose_from_matrix(mat: npt.NDArray[np.float64]) -> list[list[float]]:
    """Convert a numpy (4, 4) SE(3) matrix to a JSON-serialisable nested list."""
    return pt.check_transform(mat).tolist()


def _validate_xyz_trajectory(points: list[list[float]]) -> list[list[float]]:
    """Validate a serialisable list of 3D points."""
    array = np.asarray(points, dtype=np.float64)
    if array.size == 0:
        return []
    if array.ndim != 2 or array.shape[1] != 3:
        msg = "trajectory_so_far must be a list of [x, y, z] points"
        raise ValueError(msg)
    if not np.isfinite(array).all():
        msg = "trajectory_so_far must contain only finite coordinates"
        raise ValueError(msg)
    return array.tolist()


class MessageKind(str, Enum):
    """Discriminator for messages flowing between pipeline stages."""

    FRAME = "frame"
    POSE_UPDATE = "pose_update"
    MAP_UPDATE = "map_update"
    DENSE_UPDATE = "dense_update"
    PREVIEW = "preview"
    ARTIFACT = "artifact"
    END = "end"


class Envelope(BaseConfig):
    """Typed message envelope that makes offline and streaming look identical.

    Every message flowing through the pipeline is wrapped in an Envelope.
    Stages consume and produce envelopes, routing on ``kind``.
    """

    session_id: str
    """Session that owns this message."""

    seq: int = Field(ge=0)
    """Monotonically increasing sequence number within the session."""

    ts_ns: int = Field(ge=0)
    """Timestamp in nanoseconds (video PTS for offline, wall-clock for streaming)."""

    kind: MessageKind
    """Discriminator used by stages for routing."""

    payload: dict[str, Any] = Field(default_factory=dict)
    """Arbitrary typed payload keyed by downstream convention."""


class FramePayload(BaseConfig):
    """Payload carried inside a FRAME envelope."""

    image_path: Path | None = None
    """Path to the decoded frame on disk (offline mode)."""

    jpeg_bytes: bytes | None = None
    """Raw JPEG bytes (streaming mode)."""

    width: int = Field(default=0, ge=0)
    """Frame width in pixels."""

    height: int = Field(default=0, ge=0)
    """Frame height in pixels."""

    intrinsics_hint: dict[str, Any] | None = None
    """Optional intrinsics hint (fx, fy, cx, cy) when available."""

    frame_index: int = Field(default=0, ge=0)
    """Original frame index in the source video."""

    @model_validator(mode="after")
    def validate_payload_source(self) -> FramePayload:
        """Require enough information to materialise or replay the frame."""
        if (self.width > 0) != (self.height > 0):
            msg = "FramePayload width and height must both be positive when provided"
            raise ValueError(msg)
        has_raster_source = self.image_path is not None or self.jpeg_bytes is not None
        has_dimensions = self.width > 0 and self.height > 0
        if not has_raster_source and not has_dimensions:
            msg = "FramePayload requires image_path, jpeg_bytes, or positive width and height"
            raise ValueError(msg)
        return self


class PosePayload(BaseConfig):
    """Payload carried inside a POSE_UPDATE envelope."""

    t_world_camera: list[list[float]] = Field(
        default_factory=lambda: [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    )
    """4×4 world-from-camera SE(3) transform (row-major, JSON-serialisable)."""

    timestamp_s: float = 0.0
    """Timestamp in seconds."""

    is_keyframe: bool = False
    """Whether this pose corresponds to a selected keyframe."""

    @field_validator("t_world_camera")
    @classmethod
    def validate_t_world_camera(cls, value: list[list[float]]) -> list[list[float]]:
        """Enforce a proper SE(3) matrix at the contract boundary."""
        return pose_from_matrix(pose_to_matrix(value))

    @field_validator("timestamp_s")
    @classmethod
    def validate_timestamp_s(cls, value: float) -> float:
        """Reject NaN and infinite timestamps."""
        if not math.isfinite(value):
            msg = "timestamp_s must be finite"
            raise ValueError(msg)
        return value

    @property
    def matrix(self) -> npt.NDArray[np.float64]:
        """Return the SE(3) pose as a validated (4, 4) numpy array."""
        return pose_to_matrix(self.t_world_camera)

    @staticmethod
    def from_matrix(
        mat: npt.NDArray[np.float64],
        *,
        timestamp_s: float = 0.0,
        is_keyframe: bool = False,
    ) -> PosePayload:
        """Build a :class:`PosePayload` from a numpy SE(3) matrix."""
        return PosePayload(
            t_world_camera=pose_from_matrix(mat),
            timestamp_s=timestamp_s,
            is_keyframe=is_keyframe,
        )


class MapUpdatePayload(BaseConfig):
    """Payload carried inside a MAP_UPDATE envelope."""

    num_points: int = Field(default=0, ge=0)
    """Number of 3D points in this incremental update."""

    points_path: Path | None = None
    """Path to a PLY file containing the sparse point cloud update."""


class PreviewPayload(BaseConfig):
    """Payload carried inside a PREVIEW envelope."""

    trajectory_so_far: list[list[float]] = Field(default_factory=list)
    """List of [x, y, z] positions for BEV rendering."""

    num_map_points: int = Field(default=0, ge=0)
    """Total sparse map points accumulated so far."""

    latest_pose: list[list[float]] | None = Field(
        default_factory=lambda: [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    )
    """Latest 4×4 camera pose (JSON-serialisable), when available."""

    @field_validator("trajectory_so_far")
    @classmethod
    def validate_trajectory_so_far(cls, value: list[list[float]]) -> list[list[float]]:
        """Reject malformed preview trajectories."""
        return _validate_xyz_trajectory(value)

    @field_validator("latest_pose")
    @classmethod
    def validate_latest_pose(cls, value: list[list[float]] | None) -> list[list[float]] | None:
        """Reject malformed preview poses while allowing missing poses."""
        if value is None:
            return None
        return pose_from_matrix(pose_to_matrix(value))

    @property
    def latest_pose_matrix(self) -> npt.NDArray[np.float64] | None:
        """Return the latest pose as a validated (4, 4) numpy array."""
        if self.latest_pose is None:
            return None
        return pose_to_matrix(self.latest_pose)


def make_envelope(
    *,
    session_id: str,
    seq: int,
    kind: MessageKind,
    payload: dict[str, Any] | None = None,
    ts_ns: int | None = None,
) -> Envelope:
    """Convenience factory for building envelopes with sensible defaults."""
    return Envelope(
        session_id=session_id,
        seq=seq,
        ts_ns=ts_ns if ts_ns is not None else time.time_ns(),
        kind=kind,
        payload=payload or {},
    )
