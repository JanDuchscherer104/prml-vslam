"""Persisted config for the ``evaluate.cloud`` stage."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import ConfigDict, Field

from prml_vslam.pipeline.contracts.context import PipelinePlanContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.utils import BaseConfig


class CloudMetricId(StrEnum):
    """Dense-cloud metric identifiers exposed by the stage config."""

    CHAMFER_DISTANCE = "chamfer.distance"
    F_SCORE = "f_score"


class DenseCloudSelectionConfig(BaseConfig):
    """Reference and estimate artifact-key selection for cloud evaluation."""

    model_config = ConfigDict(extra="ignore")

    reference_artifact_key: str = "reference_cloud"
    estimate_artifact_key: str = "aligned_point_cloud_ply"
    f_score_threshold_m: float = Field(default=0.05, gt=0.0)
    """Nearest-neighbor threshold, in meters, used for precision/recall F-score."""


class CloudEvaluationStageConfig(StageConfig):
    """Stage-owned dense-cloud evaluation policy."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.CLOUD_EVALUATION
    selection: DenseCloudSelectionConfig = Field(default_factory=DenseCloudSelectionConfig)
    planned_metrics: list[CloudMetricId] = Field(
        default_factory=lambda: [CloudMetricId.CHAMFER_DISTANCE, CloudMetricId.F_SCORE]
    )

    def planned_outputs(self, context: PipelinePlanContext) -> list[Path]:
        return [context.run_paths.cloud_metrics_path]

    def availability(self, context: PipelinePlanContext) -> tuple[bool, str | None]:
        slam_backend = context.run_config.stages.slam.backend
        if slam_backend is None:
            return False, "Cloud evaluation requires `[stages.slam.backend]`."
        backend = context.slam_backend if context.slam_backend is not None else slam_backend
        if not backend.supports_dense_points:
            return False, f"{backend.display_name} does not support dense point-cloud outputs."
        if not context.run_config.stages.slam.outputs.emit_dense_points:
            return False, "Cloud evaluation requires dense SLAM point-cloud outputs."
        if not context.run_config.stages.evaluate_trajectory.enabled:
            return False, "Cloud evaluation requires trajectory evaluation to align SLAM geometry."
        if not context.run_config.stages.reconstruction.enabled:
            return False, "Cloud evaluation requires reference reconstruction."
        trajectory_available, trajectory_reason = context.run_config.stages.evaluate_trajectory.availability(context)
        if not trajectory_available:
            return False, f"Cloud evaluation requires available trajectory evaluation: {trajectory_reason}"
        reconstruction_available, reconstruction_reason = context.run_config.stages.reconstruction.availability(context)
        if not reconstruction_available:
            return False, f"Cloud evaluation requires available reference reconstruction: {reconstruction_reason}"
        return True, None


__all__ = ["CloudEvaluationStageConfig", "CloudMetricId", "DenseCloudSelectionConfig"]
