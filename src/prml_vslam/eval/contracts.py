"""Shared evaluation contracts not owned by trajectory metric manifests.

Trajectory metric contracts live in :mod:`prml_vslam.eval.trajectory_contracts`
and trajectory alignment contracts live in
:mod:`prml_vslam.align.trajectory_sim3.contracts`. Dense-cloud and intrinsics DTOs
remain here temporarily until those evaluation surfaces get the same split.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from prml_vslam.interfaces.camera import CameraIntrinsics
from prml_vslam.utils import BaseData


class CloudMetricId(StrEnum):
    """Name dense-cloud metrics persisted by the Open3D evaluation seam."""

    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    CHAMFER = "chamfer"
    F1 = "f1"
    ICP_RMSE = "icp_rmse"
    ICP_FITNESS = "icp_fitness"


class CloudEstimateKind(StrEnum):
    """Describe which benchmark cloud artifact one metric row evaluates."""

    SIM3 = "sim3"
    SIM3_ICP = "sim3_icp"
    RECONSTRUCTION = "reconstruction"


class MetricStats(BaseData):
    """Capture scalar summary statistics for one evaluated error series."""

    rmse: float
    """Root-mean-square error."""

    mean: float
    """Mean error."""

    median: float
    """Median error."""

    std: float
    """Standard deviation of the error series."""

    min: float
    """Minimum error."""

    max: float
    """Maximum error."""

    sse: float
    """Sum of squared errors."""

    @classmethod
    def from_evo_statistics(cls, statistics: dict[str, float]) -> MetricStats:
        """Build stats from ``evo``'s ``metric.get_all_statistics()`` payload."""
        return cls(
            rmse=float(statistics["rmse"]),
            mean=float(statistics["mean"]),
            median=float(statistics["median"]),
            std=float(statistics["std"]),
            min=float(statistics["min"]),
            max=float(statistics["max"]),
            sse=float(statistics["sse"]),
        )


class IntrinsicsComparisonDiagnostics(BaseData):
    """Estimated-vs-reference intrinsics residuals in one raster space."""

    raster_space: str
    """Raster space for both estimated and reference intrinsics."""

    reference: CameraIntrinsics
    """Reference camera model in the comparison raster."""

    mean_estimate: CameraIntrinsics
    """Mean estimated camera model across all samples."""

    fx_residual_px: list[float] = Field(default_factory=list)
    """Per-sample `fx_est - fx_ref` residuals in pixels."""

    fy_residual_px: list[float] = Field(default_factory=list)
    """Per-sample `fy_est - fy_ref` residuals in pixels."""

    cx_residual_px: list[float] = Field(default_factory=list)
    """Per-sample `cx_est - cx_ref` residuals in pixels."""

    cy_residual_px: list[float] = Field(default_factory=list)
    """Per-sample `cy_est - cy_ref` residuals in pixels."""


class DenseCloudEvaluationSelection(BaseData):
    """Describe the resolved dense-cloud inputs for one evaluation action."""

    artifact_root: Path
    """Artifact root that owns the compared dense outputs."""

    reference_cloud_path: Path
    """Reference dense geometry path."""

    estimate_cloud_path: Path
    """Estimated dense geometry path."""

    estimate_kind: CloudEstimateKind = CloudEstimateKind.SIM3_ICP
    """Semantic role of the estimated dense geometry artifact."""

    f1_threshold_m: float = Field(default=0.05, gt=0.0)
    """Distance threshold used for precision, recall, and F1, in meters."""


class DenseCloudEstimateEvaluation(BaseData):
    """Metrics for one evaluated dense-cloud estimate artifact."""

    estimate_kind: CloudEstimateKind
    """Semantic role of the evaluated estimate cloud."""

    estimate_cloud_path: Path
    """Estimated dense geometry path compared against the reference cloud."""

    reference_point_count: int
    """Number of points loaded from the reference cloud."""

    estimate_point_count: int
    """Number of points loaded from the estimate cloud."""

    metrics: dict[CloudMetricId, float] = Field(default_factory=dict)
    """Scalar dense-cloud metrics keyed by canonical metric id."""


class CloudAlignmentSelection(BaseData):
    """Describe offline point-cloud alignment inputs for benchmark runs."""

    artifact_root: Path
    """Artifact root that owns the derived cloud-alignment outputs."""

    reference_cloud_path: Path
    """Reference cloud in the benchmark target frame."""

    sim3_cloud_path: Path
    """Trajectory-Sim(3)-aligned SLAM cloud used as the ICP initialization."""

    target_frame: str = "world"
    """Benchmark target frame for the aligned and ICP-refined clouds."""

    max_correspondence_distance_m: float = Field(default=0.05, gt=0.0)
    """Maximum ICP correspondence distance in meters."""


class CloudAlignmentArtifact(BaseData):
    """Persist one offline cloud-alignment result."""

    path: Path
    """Path to the side metadata payload."""

    reference_cloud_path: Path
    """Reference cloud used by the refinement."""

    sim3_point_cloud_path: Path
    """Canonical trajectory-Sim(3)-aligned estimate cloud."""

    icp_point_cloud_path: Path
    """ICP-refined estimate cloud."""

    target_frame: str = "world"
    """Benchmark target frame for the aligned and ICP-refined clouds."""

    max_correspondence_distance_m: float
    """Maximum correspondence distance used by ICP."""

    fitness: float
    """Open3D ICP fitness score."""

    inlier_rmse_m: float
    """Open3D ICP inlier RMSE in meters."""

    transformation: list[list[float]]
    """Estimated point-to-point ICP transform applied after Sim(3)."""


class DenseCloudEvaluationArtifact(BaseData):
    """Persist one dense-cloud evaluation result for later review."""

    path: Path
    """Path to the persisted result payload."""

    title: str
    """Short title shown to downstream consumers."""

    reference_cloud_path: Path
    """Reference dense geometry path."""

    f1_threshold_m: float = 0.05
    """Distance threshold used for precision, recall, and F1, in meters."""

    estimates: list[DenseCloudEstimateEvaluation] = Field(default_factory=list)
    """Per-estimate metric payloads for Sim3, ICP-refined, or reconstruction clouds."""

    cloud_alignment_path: Path | None = None
    """Optional point-cloud alignment metadata used to attach ICP diagnostics."""

    @property
    def metrics(self) -> dict[str, float]:
        """Return flattened metric keys for legacy table-style consumers."""
        return {
            f"{estimate.estimate_kind.value}.{metric_id.value}": value
            for estimate in self.estimates
            for metric_id, value in estimate.metrics.items()
        }


__all__ = [
    "CloudEstimateKind",
    "CloudAlignmentArtifact",
    "CloudAlignmentSelection",
    "CloudMetricId",
    "DenseCloudEvaluationArtifact",
    "DenseCloudEstimateEvaluation",
    "DenseCloudEvaluationSelection",
    "IntrinsicsComparisonDiagnostics",
    "MetricStats",
]
