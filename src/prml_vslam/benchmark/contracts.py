"""Thin benchmark-policy contracts kept outside the pipeline core."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from prml_vslam.utils import BaseConfig


class ReferenceSource(StrEnum):
    """Typed source identifier for one available reference trajectory."""

    GROUND_TRUTH = "ground_truth"
    ARCORE = "arcore"
    ARKIT = "arkit"

    @property
    def label(self) -> str:
        """Return the human-readable source label."""
        return {
            ReferenceSource.GROUND_TRUTH: "ground truth",
            ReferenceSource.ARCORE: "ARCore",
            ReferenceSource.ARKIT: "ARKit",
        }[self]


class ReferenceCloudSource(StrEnum):
    """Typed source identifier for one available reference cloud."""

    TANGO_RAW = "tango_raw"
    TANGO_AREA_LEARNING = "tango_area_learning"


class ReferenceCloudCoordinateStatus(StrEnum):
    """Coordinate status for one prepared reference cloud."""

    SOURCE_NATIVE = "source_native"
    ALIGNED = "aligned"


# TODO(pipeline-refactor/WP-02): Replace with [stages.reconstruction] reference
# mode policy once ReconstructionStageConfig covers current reference behavior.
class ReferenceReconstructionConfig(BaseConfig):
    """Policy toggle for the optional reference-reconstruction stage."""

    enabled: bool = False
    """Whether the run should include the corresponding stage."""

    extract_mesh: bool = False
    """Whether the reference reconstruction stage should also persist a triangle mesh."""


class TrajectoryBenchmarkConfig(BaseConfig):
    """Policy for trajectory evaluation."""

    enabled: bool = False
    """Whether the run should include trajectory evaluation."""

    baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH
    """Explicit reference source used by the trajectory evaluation stage when available."""


class CloudBenchmarkConfig(BaseConfig):
    """Policy for dense-cloud comparison."""

    enabled: bool = False
    """Whether the run should include dense-cloud comparison."""


class EfficiencyBenchmarkConfig(BaseConfig):
    """Policy for efficiency evaluation."""

    enabled: bool = False
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
    "ReferenceCloudCoordinateStatus",
    "ReferenceCloudSource",
    "ReferenceSource",
    "ReferenceReconstructionConfig",
    "TrajectoryBenchmarkConfig",
]
