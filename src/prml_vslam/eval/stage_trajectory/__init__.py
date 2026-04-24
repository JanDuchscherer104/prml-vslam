"""Trajectory-evaluation pipeline stage integration."""

from __future__ import annotations

from typing import Any

from prml_vslam.eval.stage_trajectory.config import TrajectoryEvaluationPolicy, TrajectoryEvaluationStageConfig
from prml_vslam.eval.stage_trajectory.contracts import TrajectoryEvaluationRuntimeInput

__all__ = [
    "TrajectoryEvaluationPolicy",
    "TrajectoryEvaluationRuntime",
    "TrajectoryEvaluationRuntimeInput",
    "TrajectoryEvaluationStageConfig",
]


def __getattr__(name: str) -> Any:
    if name == "TrajectoryEvaluationRuntime":
        from prml_vslam.eval.stage_trajectory.runtime import TrajectoryEvaluationRuntime

        return TrajectoryEvaluationRuntime
    raise AttributeError(name)
