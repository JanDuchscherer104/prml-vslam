"""Dense point-cloud evaluation service using Open3D nearest-neighbor metrics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from prml_vslam.eval.contracts import (
    CloudAlignmentArtifact,
    CloudEstimateKind,
    CloudMetricId,
    DenseCloudEstimateEvaluation,
    DenseCloudEvaluationArtifact,
    DenseCloudEvaluationSelection,
)


class DenseCloudEvaluationService:
    """Compute and load Open3D dense-cloud benchmark metrics."""

    def load_dense_evaluation(
        self,
        *,
        selection: DenseCloudEvaluationSelection,
    ) -> DenseCloudEvaluationArtifact | None:
        """Load a persisted dense-cloud evaluation when it exists."""
        result_path = self.result_path(selection.artifact_root)
        if not result_path.exists():
            return None
        return DenseCloudEvaluationArtifact.model_validate_json(result_path.read_text(encoding="utf-8"))

    def compute_dense_evaluation(
        self,
        *,
        selection: DenseCloudEvaluationSelection,
    ) -> DenseCloudEvaluationArtifact:
        """Compute and persist metrics for one dense-cloud estimate."""
        return self.compute_dense_evaluations(
            artifact_root=selection.artifact_root,
            reference_cloud_path=selection.reference_cloud_path,
            estimates=[(selection.estimate_kind, selection.estimate_cloud_path)],
            f1_threshold_m=selection.f1_threshold_m,
        )

    def compute_dense_evaluations(
        self,
        *,
        artifact_root: Path,
        reference_cloud_path: Path,
        estimates: list[tuple[CloudEstimateKind, Path]],
        f1_threshold_m: float = 0.05,
        cloud_alignment_path: Path | None = None,
    ) -> DenseCloudEvaluationArtifact:
        """Compute and persist metrics for all resolved dense-cloud estimates."""
        if not estimates:
            raise ValueError("Dense-cloud evaluation requires at least one estimate cloud.")
        reference_pcd = _read_non_empty_point_cloud(reference_cloud_path, label="reference", operation="evaluation")
        reference_count = len(reference_pcd.points)
        cloud_alignment = _load_cloud_alignment(cloud_alignment_path)
        estimate_payloads = [
            self._evaluate_estimate(
                reference_pcd=reference_pcd,
                reference_count=reference_count,
                estimate_kind=estimate_kind,
                estimate_cloud_path=estimate_cloud_path,
                f1_threshold_m=f1_threshold_m,
                cloud_alignment=cloud_alignment,
            )
            for estimate_kind, estimate_cloud_path in estimates
        ]
        artifact = DenseCloudEvaluationArtifact(
            path=self.result_path(artifact_root),
            title="Dense Cloud Evaluation (Open3D)",
            reference_cloud_path=reference_cloud_path,
            f1_threshold_m=f1_threshold_m,
            estimates=estimate_payloads,
            cloud_alignment_path=cloud_alignment_path,
        )
        artifact.path.parent.mkdir(parents=True, exist_ok=True)
        artifact.path.write_text(
            json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return artifact

    def _evaluate_estimate(
        self,
        *,
        reference_pcd: Any,
        reference_count: int,
        estimate_kind: CloudEstimateKind,
        estimate_cloud_path: Path,
        f1_threshold_m: float,
        cloud_alignment: CloudAlignmentArtifact | None,
    ) -> DenseCloudEstimateEvaluation:
        estimate_pcd = _read_non_empty_point_cloud(estimate_cloud_path, label="estimate", operation="evaluation")
        estimate_count = len(estimate_pcd.points)
        estimate_to_reference = np.asarray(estimate_pcd.compute_point_cloud_distance(reference_pcd), dtype=np.float64)
        reference_to_estimate = np.asarray(reference_pcd.compute_point_cloud_distance(estimate_pcd), dtype=np.float64)
        if estimate_to_reference.size == 0 or reference_to_estimate.size == 0:
            raise ValueError("Open3D produced empty nearest-neighbor distance arrays for cloud evaluation.")
        accuracy = float(np.mean(estimate_to_reference))
        completeness = float(np.mean(reference_to_estimate))
        precision = float(np.mean(estimate_to_reference <= f1_threshold_m))
        recall = float(np.mean(reference_to_estimate <= f1_threshold_m))
        f1 = 0.0 if precision + recall == 0.0 else float(2.0 * precision * recall / (precision + recall))
        metric_values: dict[CloudMetricId, float] = {
            CloudMetricId.ACCURACY: accuracy,
            CloudMetricId.COMPLETENESS: completeness,
            CloudMetricId.CHAMFER: accuracy + completeness,
            CloudMetricId.F1: f1,
        }
        if estimate_kind is CloudEstimateKind.SIM3_ICP and cloud_alignment is not None:
            metric_values[CloudMetricId.ICP_RMSE] = cloud_alignment.inlier_rmse_m
            metric_values[CloudMetricId.ICP_FITNESS] = cloud_alignment.fitness
        return DenseCloudEstimateEvaluation(
            estimate_kind=estimate_kind,
            estimate_cloud_path=estimate_cloud_path,
            reference_point_count=reference_count,
            estimate_point_count=estimate_count,
            metrics=metric_values,
        )

    @staticmethod
    def result_path(run_root: Path) -> Path:
        """Return the deterministic dense-cloud metrics path."""
        return run_root / "evaluation" / "cloud_metrics.json"


def _read_non_empty_point_cloud(path: Path, *, label: str, operation: str = "evaluation") -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Point-cloud {operation} {label} cloud does not exist: {path}")
    o3d = _import_open3d()
    point_cloud = o3d.io.read_point_cloud(path.as_posix())
    points_xyz = np.asarray(point_cloud.points, dtype=np.float64)
    if points_xyz.shape[0] == 0:
        raise ValueError(f"Point-cloud {operation} {label} cloud is empty: {path}")
    if points_xyz.ndim != 2 or points_xyz.shape[1] != 3:
        raise ValueError(f"Expected {label} point cloud shape (N, 3), got {points_xyz.shape} for '{path}'.")
    if not np.isfinite(points_xyz).all():
        raise ValueError(f"Point-cloud {operation} {label} cloud contains non-finite points: {path}")
    return point_cloud


def _load_cloud_alignment(path: Path | None) -> CloudAlignmentArtifact | None:
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"Cloud alignment artifact does not exist: {path}")
    return CloudAlignmentArtifact.model_validate_json(path.read_text(encoding="utf-8"))


def _import_open3d() -> Any:
    try:
        import open3d as o3d
    except ImportError as exc:  # pragma: no cover - exercised only when optional runtime is missing
        raise RuntimeError("Open3D is required for point-cloud evaluation.") from exc
    return o3d


__all__ = ["DenseCloudEvaluationService"]
