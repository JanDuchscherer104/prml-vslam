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
    """Planned dense-cloud metric identifiers."""

    CHAMFER_DISTANCE = "chamfer.distance"
    F_SCORE = "f_score"


class DenseCloudSelectionConfig(BaseConfig):
    """Metric policy for aligned cloud evaluation."""

    model_config = ConfigDict(extra="ignore")

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
        if not context.run_config.stages.align_cloud.enabled:
            return False, "Cloud evaluation requires `align.cloud`."
        alignment_available, alignment_reason = context.run_config.stages.align_cloud.availability(context)
        if not alignment_available:
            return False, f"Cloud evaluation requires available cloud alignment: {alignment_reason}"
        return True, None


__all__ = ["CloudEvaluationStageConfig", "CloudMetricId", "DenseCloudSelectionConfig"]
