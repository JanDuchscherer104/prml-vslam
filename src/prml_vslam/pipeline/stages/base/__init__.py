"""Generic stage runtime contract package."""

from prml_vslam.pipeline.contracts.context import PipelineExecutionContext, PipelinePlanContext
from prml_vslam.pipeline.stages.base.config import FailureFingerprint
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus, StageRuntimeUpdate
from prml_vslam.pipeline.stages.base.runtime import LifecycleStageRuntimeMixin
from prml_vslam.pipeline.stages.base.spec import StageRuntimeSpec

__all__ = [
    "FailureFingerprint",
    "LifecycleStageRuntimeMixin",
    "PipelineExecutionContext",
    "PipelinePlanContext",
    "StageResult",
    "StageRuntimeStatus",
    "StageRuntimeUpdate",
    "StageRuntimeSpec",
]
