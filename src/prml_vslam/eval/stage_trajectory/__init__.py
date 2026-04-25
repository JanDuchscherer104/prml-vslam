"""Trajectory-evaluation pipeline stage integration."""

from __future__ import annotations

from prml_vslam.eval.stage_trajectory.config import TrajectoryEvaluationPolicy, TrajectoryEvaluationStageConfig
from prml_vslam.eval.stage_trajectory.contracts import TrajectoryEvaluationStageInput
from prml_vslam.eval.stage_trajectory.runtime import TrajectoryEvaluationRuntime

__all__ = [
    "TrajectoryEvaluationPolicy",
    "TrajectoryEvaluationRuntime",
    "TrajectoryEvaluationStageInput",
    "TrajectoryEvaluationStageConfig",
]
