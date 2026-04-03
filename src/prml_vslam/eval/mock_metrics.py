from __future__ import annotations

from pathlib import Path

import numpy as np

from prml_vslam.eval.interfaces import (
    ErrorSeries,
    EvaluationArtifact,
    EvaluationControls,
    MetricStats,
    TrajectorySeries,
)


def build_evaluation_artifact(
    *,
    result_path: Path,
    controls: EvaluationControls,
    payload: dict[str, object],
    reference_path: Path,
    estimate_path: Path,
    trajectories: tuple[TrajectorySeries, TrajectorySeries] | None = None,
) -> EvaluationArtifact:
    """Build the in-memory evaluation artifact for one persisted mock result."""
    reference_trajectory, estimate_trajectory = trajectories or load_trajectory_pair(
        reference_path=reference_path,
        estimate_path=estimate_path,
    )
    return EvaluationArtifact(
        path=result_path,
        controls=controls,
        title=str(payload["title"]),
        matched_pairs=int(payload["matched_pairs"]),
        stats=MetricStats.model_validate(payload["stats"]),
        reference_path=reference_path,
        estimate_path=estimate_path,
        trajectories=[reference_trajectory, estimate_trajectory],
        error_series=ErrorSeries(
            timestamps_s=np.asarray(payload["error_timestamps_s"], dtype=np.float64),
            values=np.asarray(payload["error_values"], dtype=np.float64),
        ),
    )


def load_trajectory_pair(*, reference_path: Path, estimate_path: Path) -> tuple[TrajectorySeries, TrajectorySeries]:
    """Load the reference and estimate trajectories for one evaluation slice."""
    return _load_trajectory_series(reference_path, "Reference"), _load_trajectory_series(estimate_path, "Estimate")


def stats_payload(error_values: np.ndarray) -> dict[str, float]:
    """Return the persisted scalar summary for one mock trajectory comparison."""
    squared = np.square(error_values)
    return {
        "rmse": float(np.sqrt(np.mean(squared))),
        "mean": float(np.mean(error_values)),
        "median": float(np.median(error_values)),
        "std": float(np.std(error_values)),
        "min": float(np.min(error_values)),
        "max": float(np.max(error_values)),
        "sse": float(np.sum(squared)),
    }


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


__all__ = ["build_evaluation_artifact", "load_trajectory_pair", "stats_payload"]
