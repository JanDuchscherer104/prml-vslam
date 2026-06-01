"""Typed evaluation contracts for persisted metrics and review surfaces.

This module owns the normalized result payloads produced by
:mod:`prml_vslam.eval.services` and consumed by app or plotting code. It sits
downstream of :mod:`prml_vslam.pipeline` and :mod:`prml_vslam.sources`: runs
provide artifact roots and source-prepared references, while this package
provides the typed metric outputs and selection models used to inspect them.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import numpy as np
from jaxtyping import Float
from pydantic import Field

from prml_vslam.interfaces.camera import CameraIntrinsics
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.utils import BaseData


class TrajectoryMetricId(StrEnum):
    """Name the trajectory metrics supported or planned through the `evo` seam."""

    APE_TRANSLATION = "ape.translation"
    RPE_TRANSLATION = "rpe.translation"


class TrajectoryAlignmentMode(StrEnum):
    """Describe how trajectories are aligned before metric computation."""

    TIMESTAMP_ASSOCIATED_ONLY = "timestamp_associated_only"
    SE3_UMeyama = "se3_umeyama"
    SIM3_UMEYAMA = "sim3_umeyama"


class TrajectoryAlignmentArtifact(BaseData):
    """Persist an explicit trajectory alignment used for diagnostics or metrics."""

    source_frame: str
    target_frame: str
    alignment_type: TrajectoryAlignmentMode = TrajectoryAlignmentMode.SIM3_UMEYAMA
    scale: float
    rotation: list[list[float]]
    translation: list[float]
    matched_pairs: int
    rms_error_m: float
    reference_source: str
    sync_max_diff_s: float


class MetricStats(BaseData):
    """Capture scalar summary statistics for one evaluated error series."""

    rmse: float
    mean: float
    median: float
    std: float
    min: float
    max: float
    sse: float

    @classmethod
    def from_error_values(cls, error_values: np.ndarray) -> MetricStats:
        """Build the shared scalar summary payload from one raw error series."""
        squared = np.square(error_values)
        return cls(
            rmse=float(np.sqrt(np.mean(squared))),
            mean=float(np.mean(error_values)),
            median=float(np.median(error_values)),
            std=float(np.std(error_values)),
            min=float(np.min(error_values)),
            max=float(np.max(error_values)),
            sse=float(np.sum(squared)),
        )


class TrajectorySeries(BaseData):
    """Carry one trajectory series for persisted review and plotting."""

    name: str
    positions_xyz: Float[np.ndarray, "num_points 3"]  # noqa: F722
    timestamps_s: Float[np.ndarray, "num_points"]  # noqa: F821, UP037


class ErrorSeries(BaseData):
    """Carry one scalar error profile aligned with the evaluated timestamps."""

    timestamps_s: Float[np.ndarray, "num_points"]  # noqa: F821, UP037
    values: Float[np.ndarray, "num_points"]  # noqa: F821, UP037


class TrajectoryEvaluationPreview(BaseData):
    """Hold one in-memory trajectory-evaluation preview before or after persistence."""

    reference: TrajectorySeries
    estimate: TrajectorySeries
    error_series: ErrorSeries
    stats: MetricStats
    alignment: TrajectoryAlignmentArtifact | None = None


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


class TrajectoryEvaluationSemantics(BaseData):
    """Persist the exact metric semantics needed to interpret one result.

    The same numeric error series can mean different things depending on pose
    relation, trajectory alignment, and timestamp association tolerance. This
    DTO makes those choices durable alongside the metrics produced through the
    thin `evo <https://github.com/MichaelGrupp/evo>`_ adapter.
    """

    metric_id: TrajectoryMetricId = TrajectoryMetricId.APE_TRANSLATION
    pose_relation: str = "translation_part"
    alignment_mode: TrajectoryAlignmentMode = TrajectoryAlignmentMode.TIMESTAMP_ASSOCIATED_ONLY
    sync_max_diff_s: float
    candidate_next_metrics: list[TrajectoryMetricId] = Field(
        default_factory=lambda: [TrajectoryMetricId.RPE_TRANSLATION]
    )


class EvaluationArtifact(BaseData):
    """Represent one loaded or freshly computed trajectory-evaluation artifact.

    This is currently trajectory-specific even though the class name is generic;
    future dense-cloud stages should specialize rather than overloading this
    payload. The artifact is app/plotting friendly but still
    preserves reference and estimate paths plus metric semantics for review.
    """

    path: Path
    title: str
    matched_pairs: int
    stats: MetricStats
    reference_path: Path
    estimate_path: Path
    alignment_path: Path | None = None
    aligned_estimate_path: Path | None = None
    aligned_point_cloud_path: Path | None = None
    semantics: TrajectoryEvaluationSemantics
    trajectories: list[TrajectorySeries] = Field(default_factory=list)
    error_series: ErrorSeries | None = None

    @classmethod
    def from_payload(
        cls,
        *,
        path: Path,
        payload: dict[str, object],
        reference_path: Path,
        estimate_path: Path,
        trajectories: tuple[TrajectorySeries, TrajectorySeries],
    ) -> EvaluationArtifact:
        """Build the canonical evaluation artifact from one persisted metrics payload."""
        reference_trajectory, estimate_trajectory = trajectories
        matched_pairs_payload = payload["matched_pairs"]
        if not isinstance(matched_pairs_payload, int):
            raise ValueError(f"Expected integer matched_pairs in evaluation payload, got {matched_pairs_payload!r}.")
        return cls(
            path=path,
            title=str(payload["title"]),
            matched_pairs=matched_pairs_payload,
            stats=MetricStats.model_validate(payload["stats"]),
            semantics=TrajectoryEvaluationSemantics.model_validate(payload["semantics"]),
            reference_path=reference_path,
            estimate_path=estimate_path,
            alignment_path=Path(str(payload["alignment_path"])) if payload.get("alignment_path") is not None else None,
            aligned_estimate_path=(
                Path(str(payload["aligned_estimate_path"]))
                if payload.get("aligned_estimate_path") is not None
                else None
            ),
            aligned_point_cloud_path=(
                Path(str(payload["aligned_point_cloud_path"]))
                if payload.get("aligned_point_cloud_path") is not None
                else None
            ),
            trajectories=[reference_trajectory, estimate_trajectory],
            error_series=ErrorSeries(
                timestamps_s=np.asarray(payload["error_timestamps_s"], dtype=np.float64),
                values=np.asarray(payload["error_values"], dtype=np.float64),
            ),
        )


class DenseCloudEvaluationSelection(BaseData):
    """Describe the resolved dense-cloud inputs for one evaluation action."""

    artifact_root: Path
    """Artifact root that owns the compared dense outputs."""

    reference_cloud_path: Path
    """Reference dense geometry path."""

    estimate_cloud_path: Path
    """Estimated dense geometry path."""

    f_score_threshold_m: float = Field(default=0.05, gt=0.0)
    """Nearest-neighbor threshold, in meters, used for precision/recall F-score."""


class CloudAlignmentSelection(BaseData):
    """Describe offline point-cloud alignment inputs for benchmark runs."""

    artifact_root: Path
    """Artifact root that owns the derived cloud-alignment outputs."""

    reference_cloud_path: Path
    """Reference cloud in the benchmark target frame."""

    sim3_cloud_path: Path
    """Trajectory-Sim(3)-aligned SLAM cloud used as the ICP initialization."""

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

    estimate_cloud_path: Path
    """Estimated dense geometry path."""

    reference_point_count: int = 0
    """Number of points loaded from the reference cloud."""

    estimate_point_count: int = 0
    """Number of points loaded from the estimated cloud."""

    f_score_threshold_m: float = Field(default=0.05, gt=0.0)
    """Nearest-neighbor threshold, in meters, used for precision/recall F-score."""

    metrics: dict[str, float] = Field(default_factory=dict)
    """Scalar dense-cloud metrics keyed by metric name."""


class BenchmarkReference(BaseData):
    """Describe one reference trajectory available for benchmark comparison."""

    label: str
    """Human-readable label shown in the UI, e.g. ``"Ground Truth"`` or ``"ARCore"``."""

    source_key: str
    """Machine key used to derive result-file names, e.g. ``"ground_truth"`` or ``"arcore"``."""

    path: Path
    """Absolute path to the aligned TUM reference trajectory."""


class DiscoveredRun(BaseData):
    """Describe one normalized run discovered under the configured artifacts root."""

    artifact_root: Path
    """Root directory for the selected run."""

    estimate_path: Path
    """Estimated trajectory path for the run."""

    point_cloud_path: Path | None = None
    """Estimated point-cloud path for optional aligned overlay materialization."""

    method: str | None = None
    """Known benchmark method id, when it can be inferred from the path."""

    label: str
    """Compact user-facing label for selection widgets."""


class SelectionSnapshot(BaseData):
    """Capture the resolved dataset-and-run choice for one metrics render."""

    sequence_slug: str
    """Selected sequence slug."""

    reference_path: Path | None = None
    """Reference TUM trajectory path when available."""

    target_frame: str | None = None
    """Target coordinate frame for alignment and metrics."""

    coordinate_status: str | None = None
    """Native coordinate status of the reference trajectory."""

    run: DiscoveredRun
    """Selected artifact run."""


class EvaluationSelection(BaseData):
    """Bundle dataset, run, and reference choices exposed to review surfaces."""

    dataset: DatasetId
    """Dataset currently selected in the UI."""

    dataset_root: Path
    """Resolved local root for the selected dataset."""

    artifacts_root: Path
    """Configured artifacts root used for run discovery."""

    sequence_slugs: list[str] = Field(default_factory=list)
    """Local sequence slugs currently available under `dataset_root`."""

    sequence_slug: str | None = None
    """Resolved sequence slug after applying user preferences."""

    runs: list[DiscoveredRun] = Field(default_factory=list)
    """Discovered runs matching the resolved sequence."""

    selection: SelectionSnapshot | None = None
    """Resolved selection snapshot when both a sequence and run are available."""


__all__ = [
    "BenchmarkReference",
    "CloudAlignmentArtifact",
    "CloudAlignmentSelection",
    "DenseCloudEvaluationArtifact",
    "DenseCloudEvaluationSelection",
    "DiscoveredRun",
    "ErrorSeries",
    "EvaluationArtifact",
    "EvaluationSelection",
    "IntrinsicsComparisonDiagnostics",
    "MetricStats",
    "SelectionSnapshot",
    "TrajectoryAlignmentMode",
    "TrajectoryAlignmentArtifact",
    "TrajectoryEvaluationPreview",
    "TrajectoryEvaluationSemantics",
    "TrajectoryMetricId",
    "TrajectorySeries",
]
