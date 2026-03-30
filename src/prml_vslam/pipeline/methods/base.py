"""SLAM backend protocol and output model.

Defines the contract that any VSLAM method backend must satisfy. Backends are
plain Python objects (no framework base class) that get bound to Burr actions.

All SE(3) transforms are represented as **numpy (4, 4) arrays** and
converted via :mod:`pytransform3d` — no hand-rolled rotation/quaternion math.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np
import numpy.typing as npt
from pydantic import Field, field_validator
from pytransform3d import transformations as pt

from prml_vslam.utils import BaseConfig


def _validate_xyz_points(points: list[list[float]] | npt.NDArray[np.float64]) -> list[list[float]]:
    """Validate a serialisable list of 3D points."""
    array = np.asarray(points, dtype=np.float64)
    if array.size == 0:
        return []
    if array.ndim != 2 or array.shape[1] != 3:
        msg = "preview_trajectory must be a list of [x, y, z] points"
        raise ValueError(msg)
    if not np.isfinite(array).all():
        msg = "preview_trajectory must contain only finite coordinates"
        raise ValueError(msg)
    return array.tolist()


class SlamOutput(BaseConfig):
    """Result of a single SLAM processing step."""

    pose: npt.NDArray[np.float64] | None = None
    """(4, 4) T_world_camera, or *None* if tracking was lost."""

    timestamp_s: float = 0.0
    """Timestamp in seconds."""

    is_keyframe: bool = False
    """Whether this pose corresponds to a selected keyframe."""

    map_points: npt.NDArray[np.float64] | None = None
    """Optional (N, 3) incremental sparse point update."""

    num_map_points: int = Field(default=0, ge=0)
    """Number of sparse map points tracked so far."""

    preview_trajectory: list[list[float]] | None = None
    """Accumulated [x, y, z] camera positions for BEV preview."""

    @field_validator("pose", mode="before")
    @classmethod
    def validate_pose(cls, value: npt.NDArray[np.float64] | None) -> npt.NDArray[np.float64] | None:
        """Reject malformed SE(3) matrices."""
        if value is None:
            return None
        return pt.check_transform(np.asarray(value, dtype=np.float64))

    @field_validator("timestamp_s")
    @classmethod
    def validate_timestamp_s(cls, value: float) -> float:
        """Reject NaN and infinite timestamps."""
        if not math.isfinite(value):
            msg = "timestamp_s must be finite"
            raise ValueError(msg)
        return value

    @field_validator("map_points", mode="before")
    @classmethod
    def validate_map_points(cls, value: npt.NDArray[np.float64] | None) -> npt.NDArray[np.float64] | None:
        """Reject malformed sparse map point arrays."""
        if value is None:
            return None
        points = np.asarray(value, dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 3:
            msg = "map_points must have shape (N, 3)"
            raise ValueError(msg)
        if not np.isfinite(points).all():
            msg = "map_points must contain only finite coordinates"
            raise ValueError(msg)
        return points

    @field_validator("preview_trajectory")
    @classmethod
    def validate_preview_trajectory(cls, value: list[list[float]] | None) -> list[list[float]] | None:
        """Reject malformed preview trajectories."""
        if value is None:
            return None
        return _validate_xyz_points(value)


@runtime_checkable
class SlamBackend(Protocol):
    """Protocol every VSLAM method adapter must satisfy."""

    def step(self, frame_index: int, ts_ns: int = 0) -> SlamOutput:
        """Process one frame and return the result."""
        ...

    def export_artifacts(self, artifact_root: Path) -> None:
        """Write trajectory.tum and sparse_points.ply to *artifact_root/slam/*."""
        ...


# ---------------------------------------------------------------------------
# Shared artifact-export helpers
# ---------------------------------------------------------------------------


@dataclass
class ArtifactAccumulator:
    """Tracks poses/points across frames for TUM + PLY export.

    Uses :func:`pytransform3d.transformations.pq_from_transform` for the
    TUM quaternion conversion — no hand-rolled math.
    """

    poses: list[npt.NDArray[np.float64]] = field(default_factory=list)
    timestamps: list[float] = field(default_factory=list)
    trajectory: list[list[float]] = field(default_factory=list)

    def record(self, pose: npt.NDArray[np.float64], timestamp_s: float = 0.0) -> None:
        pose = pt.check_transform(np.asarray(pose, dtype=np.float64))
        self.poses.append(pose)
        self.timestamps.append(timestamp_s)
        self.trajectory.append(pose[:3, 3].tolist())

    def export(self, artifact_root: Path) -> None:
        slam_dir = artifact_root / "slam"
        slam_dir.mkdir(parents=True, exist_ok=True)
        self._write_tum(slam_dir / "trajectory.tum")
        self._write_ply(slam_dir / "sparse_points.ply")

    # -- private helpers ---------------------------------------------------

    def _write_tum(self, path: Path) -> None:
        lines: list[str] = ["# timestamp tx ty tz qx qy qz qw"]
        for pose, ts in zip(self.poses, self.timestamps, strict=True):
            pq = pt.pq_from_transform(pose)  # [px, py, pz, qw, qx, qy, qz]
            tx, ty, tz = pq[0], pq[1], pq[2]
            qw, qx, qy, qz = pq[3], pq[4], pq[5], pq[6]
            # TUM format: timestamp tx ty tz qx qy qz qw
            lines.append(f"{ts:.6f} {tx:.6f} {ty:.6f} {tz:.6f} {qx:.6f} {qy:.6f} {qz:.6f} {qw:.6f}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_ply(self, path: Path) -> None:
        n = len(self.trajectory)
        header = [
            "ply",
            "format ascii 1.0",
            f"element vertex {n}",
            "property float x",
            "property float y",
            "property float z",
            "end_header",
        ]
        body = [f"{p[0]:.6f} {p[1]:.6f} {p[2]:.6f}" for p in self.trajectory]
        path.write_text("\n".join(header + body) + "\n", encoding="utf-8")
