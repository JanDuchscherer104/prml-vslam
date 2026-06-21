"""In-memory APE and RPE preview helpers for trajectory evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from evo.core import metrics, sync

from prml_vslam.align.trajectory_sim3 import align_estimate_sim3, trajectory_supports_sim3
from prml_vslam.align.trajectory_sim3.contracts import TrajectoryAlignmentArtifact
from prml_vslam.eval.contracts import MetricStats
from prml_vslam.utils.geometry import load_tum_trajectory

_EVO_ASSOCIATION_MAX_DIFF_S = 0.01


class AlignmentUnsupportedError(ValueError):
    """Raised when a requested trajectory alignment cannot be computed."""


@dataclass(slots=True)
class _TrajectoryMetricPreview:
    """Internal single-metric preview for trajectory evaluation."""

    error_timestamps_s: np.ndarray
    error_values: np.ndarray
    stats: MetricStats
    alignment: TrajectoryAlignmentArtifact
    reference_positions_xyz: np.ndarray | None = None
    estimate_positions_xyz: np.ndarray | None = None


def compute_trajectory_ape_preview(
    *,
    reference_path: Path,
    estimate_path: Path,
    pose_relation: metrics.PoseRelation = metrics.PoseRelation.translation_part,
    max_diff_s: float = _EVO_ASSOCIATION_MAX_DIFF_S,
    target_frame: str = "world",
    source_frame: str = "slam_world",
    reference_source: str = "reference",
    method_id: str | None = None,
    method_label: str | None = None,
) -> _TrajectoryMetricPreview:
    """Compute in-memory APE for two normalized TUM trajectory artifacts.

    Uses evo's timestamp association and APE implementation over
    :class:`evo.core.trajectory.PoseTrajectory3D`. The helper returns an
    internal preview and leaves persistence to :class:`TrajectoryEvaluationService`.
    """
    reference_trajectory = load_tum_trajectory(reference_path)
    estimate_trajectory = load_tum_trajectory(estimate_path)
    try:
        associated_reference, associated_estimate = sync.associate_trajectories(
            reference_trajectory,
            estimate_trajectory,
            max_diff=max_diff_s,
        )
    except sync.SyncException as exc:
        raise ValueError(
            f"No matching trajectory timestamps were found for evo APE (max_diff={max_diff_s:.3f}s)."
        ) from exc

    if not trajectory_supports_sim3(associated_reference, associated_estimate):
        raise AlignmentUnsupportedError("Trajectory lacks sufficient geometric spread for Sim(3) alignment.")
    evaluation_estimate, alignment = align_estimate_sim3(
        reference=associated_reference,
        estimate=associated_estimate,
        max_diff_s=max_diff_s,
        target_frame=target_frame,
        source_frame=source_frame,
        reference_source=reference_source,
        method_id=method_id,
        method_label=method_label,
    )

    metric = metrics.APE(pose_relation)
    metric.process_data((associated_reference, evaluation_estimate))
    error_values = np.asarray(metric.error, dtype=np.float64)
    if error_values.size == 0:
        raise ValueError("evo APE produced zero matched trajectory pairs.")
    return _TrajectoryMetricPreview(
        error_timestamps_s=np.asarray(associated_reference.timestamps, dtype=np.float64),
        error_values=error_values,
        reference_positions_xyz=np.asarray(associated_reference.positions_xyz, dtype=np.float64),
        estimate_positions_xyz=np.asarray(evaluation_estimate.positions_xyz, dtype=np.float64),
        stats=MetricStats.from_evo_statistics(metric.get_all_statistics()),
        alignment=alignment,
    )


def compute_trajectory_rpe_preview(
    *,
    reference_path: Path,
    estimate_path: Path,
    pose_relation: metrics.PoseRelation = metrics.PoseRelation.translation_part,
    delta: float = 1.0,
    delta_unit: metrics.Unit = metrics.Unit.meters,
    max_diff_s: float = _EVO_ASSOCIATION_MAX_DIFF_S,
    target_frame: str = "world",
    source_frame: str = "slam_world",
    reference_source: str = "reference",
    method_id: str | None = None,
    method_label: str | None = None,
) -> _TrajectoryMetricPreview:
    """Compute in-memory RPE for two normalized TUM trajectory artifacts.

    Translation RPE for monocular outputs is scale-sensitive, so the helper
    applies the same Sim(3) alignment used for APE before metric computation.
    """
    reference_trajectory = load_tum_trajectory(reference_path)
    estimate_trajectory = load_tum_trajectory(estimate_path)
    try:
        associated_reference, associated_estimate = sync.associate_trajectories(
            reference_trajectory,
            estimate_trajectory,
            max_diff=max_diff_s,
        )
    except sync.SyncException as exc:
        raise ValueError(
            f"No matching trajectory timestamps were found for evo RPE (max_diff={max_diff_s:.3f}s)."
        ) from exc

    if not trajectory_supports_sim3(associated_reference, associated_estimate):
        raise AlignmentUnsupportedError("Trajectory lacks sufficient geometric spread for Sim(3) alignment.")
    evaluation_estimate, alignment = align_estimate_sim3(
        reference=associated_reference,
        estimate=associated_estimate,
        max_diff_s=max_diff_s,
        target_frame=target_frame,
        source_frame=source_frame,
        reference_source=reference_source,
        method_id=method_id,
        method_label=method_label,
    )

    metric = metrics.RPE(pose_relation, delta=delta, delta_unit=delta_unit, all_pairs=False)
    try:
        metric.process_data((associated_reference, evaluation_estimate))
    except Exception as exc:
        raise ValueError(f"evo RPE computation failed: {exc}") from exc

    error_values = np.asarray(metric.error, dtype=np.float64)
    if error_values.size == 0:
        raise ValueError("evo RPE produced zero matched trajectory pairs.")
    return _TrajectoryMetricPreview(
        error_timestamps_s=np.arange(error_values.size, dtype=np.float64),
        error_values=error_values,
        stats=MetricStats.from_evo_statistics(metric.get_all_statistics()),
        alignment=alignment,
    )


__all__ = [
    "AlignmentUnsupportedError",
    "compute_trajectory_ape_preview",
    "compute_trajectory_rpe_preview",
]
