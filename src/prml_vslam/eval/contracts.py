"""Shared evaluation contracts not owned by trajectory metric manifests.

Trajectory metric contracts live in :mod:`prml_vslam.eval.trajectory_contracts`
and trajectory alignment contracts live in
:mod:`prml_vslam.align.trajectory_sim3.contracts`. Dense-cloud and intrinsics DTOs
remain here temporarily until those evaluation surfaces get the same split.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import numpy as np
from pydantic import Field

from prml_vslam.interfaces.camera import CameraIntrinsics
from prml_vslam.utils import BaseData


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

    estimate_cloud_path: Path
    """Estimated dense geometry path."""

    metrics: dict[str, float] = Field(default_factory=dict)
    """Scalar dense-cloud metrics keyed by metric name."""


class ImageQualityMetricId(StrEnum):
    """Name the image-pair quality metrics computed between two raster-aligned frames."""

    L1 = "image.l1"
    L2 = "image.l2"
    MSE = "image.mse"
    PSNR = "image.psnr"
    SSIM = "image.ssim"
    LPIPS = "image.lpips"


class ImageQualityMetrics(BaseData):
    """Capture image-quality metrics for one ``(reference, generated)`` image pair.

    All pixel-error metrics are computed on a ``[0, 1]`` normalized scale so the
    numbers are comparable regardless of the source value range. ``psnr`` is in
    decibels and is ``+inf`` for identical images. ``coverage`` is the fraction
    of pixels actually scored, which is ``1.0`` unless a mask restricted the
    comparison (for example to the covered region of a sparse render).
    """

    l1: float
    """Mean absolute error (MAE) on the normalized scale."""

    l2: float
    """Root mean squared error (RMSE) on the normalized scale."""

    mse: float
    """Mean squared error on the normalized scale."""

    psnr: float
    """Peak signal-to-noise ratio in dB; ``+inf`` for identical images."""

    ssim: float
    """Structural similarity index in ``[-1, 1]`` (``1.0`` for identical images)."""

    lpips: float | None = None
    """Learned perceptual distance (LPIPS); lower is more similar. ``None`` when not computed.

    Computed on the full image pair (the coverage mask is ignored), so it is only comparable
    across pairs scored with the same backbone. Optional so older artifacts reload unchanged.
    """

    coverage: float = 1.0
    """Fraction of pixels scored after masking (``1.0`` when unmasked)."""

    data_range: float
    """Source value range used to normalize the inputs (for example ``255`` for uint8)."""


class ImageQualitySummary(BaseData):
    """Aggregate image-quality metrics across a set of compared image pairs."""

    pair_count: int
    """Number of ``(reference, generated)`` pairs aggregated."""

    mean_coverage: float
    """Mean per-pair scored-pixel fraction."""

    stats: dict[str, MetricStats] = Field(default_factory=dict)
    """Across-pair summary statistics keyed by :class:`ImageQualityMetricId` value."""

    frames: list[ImageQualityMetrics] = Field(default_factory=list)
    """Per-pair metrics in input order, retained for plotting and inspection."""

    @classmethod
    def from_frames(cls, frames: list[ImageQualityMetrics]) -> ImageQualitySummary:
        """Summarize per-pair image metrics into across-pair statistics."""
        if not frames:
            raise ValueError("Cannot summarize zero image pairs.")
        field_by_metric = {
            ImageQualityMetricId.L1: "l1",
            ImageQualityMetricId.L2: "l2",
            ImageQualityMetricId.MSE: "mse",
            ImageQualityMetricId.PSNR: "psnr",
            ImageQualityMetricId.SSIM: "ssim",
        }
        # LPIPS is optional: only summarize it when every frame carries it, so runs scored
        # without the perceptual backbone keep the original metric set (and stay reloadable).
        if all(frame.lpips is not None for frame in frames):
            field_by_metric[ImageQualityMetricId.LPIPS] = "lpips"
        stats = {
            metric_id.value: MetricStats.from_error_values(
                np.asarray([getattr(frame, attribute) for frame in frames], dtype=np.float64)
            )
            for metric_id, attribute in field_by_metric.items()
        }
        mean_coverage = float(np.mean([frame.coverage for frame in frames]))
        return cls(pair_count=len(frames), mean_coverage=mean_coverage, stats=stats, frames=list(frames))


__all__ = [
    "CloudAlignmentArtifact",
    "CloudAlignmentSelection",
    "DenseCloudEvaluationArtifact",
    "DenseCloudEvaluationSelection",
    "ImageQualityMetricId",
    "ImageQualityMetrics",
    "ImageQualitySummary",
    "IntrinsicsComparisonDiagnostics",
    "MetricStats",
]
