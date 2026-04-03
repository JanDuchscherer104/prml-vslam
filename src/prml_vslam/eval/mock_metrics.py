from __future__ import annotations

from pathlib import Path

import numpy as np

from prml_vslam.eval.interfaces import TrajectorySeries


def load_trajectory_pair(*, reference_path: Path, estimate_path: Path) -> tuple[TrajectorySeries, TrajectorySeries]:
    """Load the reference and estimate trajectories for one evaluation slice."""
    return _load_trajectory_series(reference_path, "Reference"), _load_trajectory_series(estimate_path, "Estimate")


def _load_trajectory_series(path: Path, name: str) -> TrajectorySeries:
    timestamps_s, positions_xyz = _load_tum_trajectory(path)
    return TrajectorySeries(name=name, timestamps_s=timestamps_s, positions_xyz=positions_xyz)


def _load_tum_trajectory(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load timestamps and XYZ positions from a TUM trajectory file."""
    rows = [
        [float(value) for value in line.split()]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not rows:
        return np.empty(0, dtype=np.float64), np.empty((0, 3), dtype=np.float64)
    data = np.asarray(rows, dtype=np.float64)
    return data[:, 0], data[:, 1:4]


__all__ = ["load_trajectory_pair"]
