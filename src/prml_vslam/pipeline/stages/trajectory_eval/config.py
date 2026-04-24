"""Persisted config for the ``evaluate.trajectory`` stage."""

from __future__ import annotations

from pydantic import ConfigDict, Field

from prml_vslam.benchmark.contracts import ReferenceSource
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.utils import BaseConfig


class TrajectoryEvaluationPolicy(BaseConfig):
    """Stage-owned trajectory-evaluation selection policy."""

    model_config = ConfigDict(extra="ignore")

    baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH
    """Explicit reference source used by the trajectory-evaluation stage."""


class TrajectoryEvaluationStageConfig(StageConfig):
    """Stage-owned trajectory-evaluation policy."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.TRAJECTORY_EVALUATION
    evaluation: TrajectoryEvaluationPolicy = Field(default_factory=TrajectoryEvaluationPolicy)
    """Evaluation-owned baseline and metric policy consumed by the runtime."""

    @property
    def baseline_source(self) -> ReferenceSource:
        """Return the selected reference trajectory source."""
        return self.evaluation.baseline_source


__all__ = ["TrajectoryEvaluationPolicy", "TrajectoryEvaluationStageConfig"]
