"""Persisted config for the diagnostic ``evaluate.cloud`` stage."""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field

from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.utils import BaseConfig


class CloudMetricId(StrEnum):
    """Planned dense-cloud metric identifiers."""

    CHAMFER_DISTANCE = "chamfer.distance"
    F_SCORE = "f_score"


class DenseCloudSelectionConfig(BaseConfig):
    """Reference and estimate artifact-key selection for cloud diagnostics."""

    model_config = ConfigDict(extra="ignore")

    reference_artifact_key: str = "reference_cloud"
    estimate_artifact_key: str = "dense_points_ply"


class CloudEvaluationStageConfig(StageConfig):
    """Diagnostic cloud-evaluation stage skeleton.

    The binding declares planned metrics and inputs, but no runtime is
    registered until dense-cloud evaluation is implemented.
    """

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.CLOUD_EVALUATION
    selection: DenseCloudSelectionConfig = Field(default_factory=DenseCloudSelectionConfig)
    planned_metrics: list[CloudMetricId] = Field(
        default_factory=lambda: [CloudMetricId.CHAMFER_DISTANCE, CloudMetricId.F_SCORE]
    )


__all__ = ["CloudEvaluationStageConfig", "CloudMetricId", "DenseCloudSelectionConfig"]
