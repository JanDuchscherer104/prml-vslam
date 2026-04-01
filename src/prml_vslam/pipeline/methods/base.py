"""SLAM backend protocol and output model.

Defines the contract that any VSLAM method backend must satisfy. Backends are
plain Python objects (no framework base class) that get bound to Burr actions.

All SE(3) transforms are represented as **numpy (4, 4) arrays** and exported
via dedicated external trajectory/geometry libraries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np
import numpy.typing as npt
import open3d as o3d
from evo.core.trajectory import PoseTrajectory3D
from evo.tools import file_interface


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

    Delegates trajectory export to ``evo`` and point-cloud export to
    ``open3d``.
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
        if not self.poses:
            path.write_text("", encoding="utf-8")
            return

        file_interface.write_tum_trajectory_file(
            path,
            PoseTrajectory3D(
                poses_se3=self.poses,
                timestamps=np.asarray(self.timestamps, dtype=np.float64),
            ),
        )

    def _write_ply(self, path: Path) -> None:
        if not self.trajectory:
            msg = f"Cannot export sparse point cloud to {path}: point cloud is empty."
            raise RuntimeError(msg)

        point_cloud = o3d.geometry.PointCloud()
        point_cloud.points = o3d.utility.Vector3dVector(np.asarray(self.trajectory, dtype=np.float64))
        ok = o3d.io.write_point_cloud(str(path), point_cloud, write_ascii=True)
        if not ok:
            msg = f"Open3D failed to write sparse point cloud to {path}."
            raise RuntimeError(msg)
