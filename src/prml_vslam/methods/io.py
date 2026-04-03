"""Small IO helpers kept for the shared method interface surface."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from prml_vslam.utils.geometry import SE3Pose
from prml_vslam.utils.geometry import write_tum_trajectory as write_shared_tum_trajectory


def ensure_directory(path: Path) -> Path:
    """Create a directory if needed and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_tum_trajectory(trajectory_path: Path, poses: Sequence[SE3Pose], timestamps: Sequence[float]) -> Path:
    """Write a TUM-format trajectory from canonical SE(3) poses and timestamps."""
    return write_shared_tum_trajectory(trajectory_path, poses, timestamps)


__all__ = ["ensure_directory", "write_tum_trajectory"]
