"""Dense-cloud evaluation pipeline stage integration."""

from prml_vslam.eval.stage_cloud.config import CloudEvaluationStageConfig
from prml_vslam.eval.stage_cloud.contracts import CloudEvaluationStageInput
from prml_vslam.eval.stage_cloud.runtime import CloudEvaluationRuntime
from prml_vslam.eval.stage_cloud.spec import CLOUD_EVALUATION_STAGE_SPEC

__all__ = [
    "CLOUD_EVALUATION_STAGE_SPEC",
    "CloudEvaluationRuntime",
    "CloudEvaluationStageConfig",
    "CloudEvaluationStageInput",
]
