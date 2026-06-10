"""Persisted config for the diagnostic ``evaluate.cloud`` stage."""

from __future__ import annotations

from pathlib import Path

from pydantic import ConfigDict, Field

from prml_vslam.eval.contracts import CloudMetricId
from prml_vslam.pipeline.contracts.context import PipelinePlanContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.utils import BaseConfig


class DenseCloudSelectionConfig(BaseConfig):
    """Reference and estimate artifact-key selection for cloud diagnostics."""

    model_config = ConfigDict(extra="ignore")

    reference_artifact_key: str = "reference_cloud"
    estimate_artifact_key: str = "dense_points_ply"


class CloudEvaluationStageConfig(StageConfig):
    """Dense-cloud evaluation stage policy."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.CLOUD_EVALUATION
    selection: DenseCloudSelectionConfig = Field(default_factory=DenseCloudSelectionConfig)
    f1_threshold_m: float = Field(default=0.05, gt=0.0)
    """Distance threshold used for precision, recall, and F1, in meters."""

    planned_metrics: list[CloudMetricId] = Field(
        default_factory=lambda: [
            CloudMetricId.ACCURACY,
            CloudMetricId.COMPLETENESS,
            CloudMetricId.CHAMFER,
            CloudMetricId.F1,
            CloudMetricId.ICP_RMSE,
            CloudMetricId.ICP_FITNESS,
        ]
    )

    def planned_outputs(self, context: PipelinePlanContext) -> list[Path]:
        return [context.run_paths.cloud_metrics_path]

    def availability(self, context: PipelinePlanContext) -> tuple[bool, str | None]:
        del context
        return True, None


__all__ = ["CloudEvaluationStageConfig", "CloudMetricId", "DenseCloudSelectionConfig"]
