"""Trajectory-evaluation stage runtime package."""

from __future__ import annotations

from typing import Any

__all__ = [
    "TrajectoryEvaluationRuntime",
    "TrajectoryEvaluationRuntimeInput",
    "TrajectoryEvaluationStageBinding",
    "TrajectoryEvaluationStageConfig",
]


def __getattr__(name: str) -> Any:
    if name == "TrajectoryEvaluationStageBinding":
        from .binding import TrajectoryEvaluationStageBinding

        return TrajectoryEvaluationStageBinding
    if name == "TrajectoryEvaluationStageConfig":
        from .config import TrajectoryEvaluationStageConfig

        return TrajectoryEvaluationStageConfig
    if name == "TrajectoryEvaluationRuntimeInput":
        from .contracts import TrajectoryEvaluationRuntimeInput

        return TrajectoryEvaluationRuntimeInput
    if name == "TrajectoryEvaluationRuntime":
        from .runtime import TrajectoryEvaluationRuntime

        return TrajectoryEvaluationRuntime
    raise AttributeError(name)
