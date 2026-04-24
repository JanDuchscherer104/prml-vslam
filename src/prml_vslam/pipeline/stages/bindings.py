"""Static ordered stage bindings for pipeline composition."""

from __future__ import annotations

from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.binding import StageBinding
from prml_vslam.pipeline.stages.cloud_eval.binding import CloudEvaluationStageBinding
from prml_vslam.pipeline.stages.ground_alignment.binding import GroundAlignmentStageBinding
from prml_vslam.pipeline.stages.reconstruction.binding import ReconstructionStageBinding
from prml_vslam.pipeline.stages.slam.binding import SlamStageBinding
from prml_vslam.pipeline.stages.source.binding import SourceStageBinding
from prml_vslam.pipeline.stages.summary.binding import SummaryStageBinding
from prml_vslam.pipeline.stages.trajectory_eval.binding import TrajectoryEvaluationStageBinding

STAGE_BINDINGS: tuple[StageBinding, ...] = (
    SourceStageBinding(),
    SlamStageBinding(),
    GroundAlignmentStageBinding(),
    TrajectoryEvaluationStageBinding(),
    ReconstructionStageBinding(),
    CloudEvaluationStageBinding(),
    SummaryStageBinding(),
)
"""Canonical stage order used by planning and runtime orchestration."""

STAGE_BINDINGS_BY_KEY: dict[StageKey, StageBinding] = {binding.key: binding for binding in STAGE_BINDINGS}
"""Stage bindings keyed by canonical stage key."""


def stage_binding_for(stage_key: StageKey) -> StageBinding:
    """Return the static binding for one canonical stage key."""
    try:
        return STAGE_BINDINGS_BY_KEY[stage_key]
    except KeyError as exc:
        raise RuntimeError(f"No stage binding registered for '{stage_key.value}'.") from exc


__all__ = ["STAGE_BINDINGS", "STAGE_BINDINGS_BY_KEY", "stage_binding_for"]
