"""SLAM backend protocol and output model.

Defines the contract that any VSLAM method backend must satisfy. Backends are
plain Python objects (no framework base class) that get bound to Burr actions.

All SE(3) transforms are represented as **numpy (4, 4) arrays** and
converted via :mod:`pytransform3d` — no hand-rolled rotation/quaternion math.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np
import numpy.typing as npt
from pytransform3d import transformations as pt


@dataclass
class SlamOutput:
    """Result of a single SLAM processing step."""

    pose: npt.NDArray[np.float64] | None = None
    """(4, 4) T_world_camera, or *None* if tracking was lost."""

    timestamp_s: float = 0.0

    is_keyframe: bool = False

    map_points: npt.NDArray[np.float64] | None = None
    """Optional (N, 3) incremental sparse point update."""

    num_map_points: int = 0

    preview_trajectory: list[list[float]] | None = None
    """Accumulated [x, y, z] camera positions for BEV preview."""


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
