"""Dense-cloud evaluation pipeline stage integration."""

from prml_vslam.eval.stage_cloud.config import CloudEvaluationStageConfig
from prml_vslam.eval.stage_cloud.contracts import CloudEvaluationStageInput
from prml_vslam.eval.stage_cloud.runtime import CloudEvaluationRuntime

__all__ = ["CloudEvaluationRuntime", "CloudEvaluationStageConfig", "CloudEvaluationStageInput"]
