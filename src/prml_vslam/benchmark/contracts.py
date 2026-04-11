"""Thin benchmark-policy contracts kept outside the pipeline core."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from prml_vslam.utils import BaseConfig


class TrajectoryBaselineId(StrEnum):
    """Explicit baseline selection for trajectory evaluation."""

    REFERENCE = "reference"
    ARCORE = "arcore"


class ReferenceReconstructionConfig(BaseConfig):
    """Policy toggle for the optional reference-reconstruction stage."""

    enabled: bool = False
    """Whether the run should include the corresponding stage."""


class TrajectoryBenchmarkConfig(BaseConfig):
    """Policy for trajectory evaluation."""

    enabled: bool = True
    """Whether the run should include trajectory evaluation."""

    baseline_id: TrajectoryBaselineId = TrajectoryBaselineId.REFERENCE
    """Explicit baseline used by the trajectory evaluation stage when available."""


class CloudBenchmarkConfig(BaseConfig):
    """Policy for dense-cloud comparison."""

    enabled: bool = False
    """Whether the run should include dense-cloud comparison."""


class EfficiencyBenchmarkConfig(BaseConfig):
    """Policy for efficiency evaluation."""

    enabled: bool = True
    """Whether the run should include efficiency metrics."""


class BenchmarkConfig(BaseConfig):
    """Thin benchmark-policy bundle attached to one run request."""

    reference: ReferenceReconstructionConfig = Field(default_factory=ReferenceReconstructionConfig)
    """Reference-reconstruction policy."""

    trajectory: TrajectoryBenchmarkConfig = Field(default_factory=TrajectoryBenchmarkConfig)
    """Trajectory-evaluation policy."""

    cloud: CloudBenchmarkConfig = Field(default_factory=CloudBenchmarkConfig)
    """Dense-cloud evaluation policy."""

    efficiency: EfficiencyBenchmarkConfig = Field(default_factory=EfficiencyBenchmarkConfig)
    """Efficiency-evaluation policy."""


__all__ = [
    "BenchmarkConfig",
    "CloudBenchmarkConfig",
    "EfficiencyBenchmarkConfig",
    "ReferenceReconstructionConfig",
    "TrajectoryBaselineId",
    "TrajectoryBenchmarkConfig",
]
