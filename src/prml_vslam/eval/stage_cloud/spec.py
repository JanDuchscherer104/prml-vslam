"""Runtime spec placeholder for the planned dense-cloud evaluation stage."""

from __future__ import annotations

from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.spec import StageRuntimeSpec

CLOUD_EVALUATION_STAGE_SPEC = StageRuntimeSpec(
    stage_key=StageKey.CLOUD_EVALUATION,
    runtime_factory=lambda _context: None,
)

__all__ = ["CLOUD_EVALUATION_STAGE_SPEC"]
