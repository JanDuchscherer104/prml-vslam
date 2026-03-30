"""Typed message envelope and payload models for the pipeline runtime.

Both offline replay and streaming sessions use identical message types at stage
boundaries, making the same stage implementations reusable in both modes.

SE(3) poses are stored as nested lists for JSON/TOML serialisability inside
:class:`Envelope` payloads, and converted to/from **numpy (4, 4)** arrays via
:func:`pose_to_matrix` / :func:`pose_from_matrix` which delegate to
:mod:`pytransform3d`.
"""

from __future__ import annotations

import time
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
from pydantic import Field
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

    seq: int
    """Monotonically increasing sequence number within the session."""

    ts_ns: int
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

    width: int = 0
    """Frame width in pixels."""

    height: int = 0
    """Frame height in pixels."""

    intrinsics_hint: dict[str, Any] | None = None
    """Optional intrinsics hint (fx, fy, cx, cy) when available."""

    frame_index: int = 0
    """Original frame index in the source video."""


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

    num_points: int = 0
    """Number of 3D points in this incremental update."""

    points_path: Path | None = None
    """Path to a PLY file containing the sparse point cloud update."""


class PreviewPayload(BaseConfig):
    """Payload carried inside a PREVIEW envelope."""

    trajectory_so_far: list[list[float]] = Field(default_factory=list)
    """List of [x, y, z] positions for BEV rendering."""

    num_map_points: int = 0
    """Total sparse map points accumulated so far."""

    latest_pose: list[list[float]] = Field(
        default_factory=lambda: [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    )
    """Latest 4×4 camera pose (JSON-serialisable)."""

    @property
    def latest_pose_matrix(self) -> npt.NDArray[np.float64]:
        """Return the latest pose as a validated (4, 4) numpy array."""
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
