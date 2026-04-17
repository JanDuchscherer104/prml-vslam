"""Thin benchmark-policy contracts kept outside the pipeline core."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from prml_vslam.utils import BaseConfig, BaseData


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


class ReferenceTrajectoryRef(BaseData):
    """One prepared reference trajectory available to a benchmark run."""

    source: ReferenceSource
    """Typed source that produced the trajectory."""

    path: Path
    """Filesystem path to the normalized TUM trajectory."""


class ReferenceCloudSource(StrEnum):
    """Typed source identifier for one available reference cloud."""

    TANGO_RAW = "tango_raw"
    TANGO_AREA_LEARNING = "tango_area_learning"


class ReferenceCloudCoordinateStatus(StrEnum):
    """Coordinate status for one prepared reference cloud."""

    SOURCE_NATIVE = "source_native"
    ALIGNED = "aligned"


class ReferenceCloudRef(BaseData):
    """One prepared reference cloud available to a benchmark run."""

    source: ReferenceCloudSource
    """Typed source that produced the cloud."""

    path: Path
    """Filesystem path to the normalized point cloud artifact."""

    metadata_path: Path
    """Filesystem path to the side metadata describing the cloud."""

    target_frame: str
    """Target frame represented by the point coordinates."""

    coordinate_status: ReferenceCloudCoordinateStatus
    """Whether the cloud remains source-native or was aligned into repo space."""


class PreparedBenchmarkInputs(BaseData):
    """Prepared benchmark-side inputs discovered for one normalized sequence."""

    reference_trajectories: list[ReferenceTrajectoryRef] = Field(default_factory=list)
    """Available normalized reference trajectories keyed by source."""

    reference_clouds: list[ReferenceCloudRef] = Field(default_factory=list)
    """Available normalized reference clouds keyed by source and coordinate status."""

    def trajectory_for_source(self, source: ReferenceSource) -> ReferenceTrajectoryRef | None:
        """Return the prepared reference trajectory for one requested source."""
        return next((reference for reference in self.reference_trajectories if reference.source is source), None)


class ReferenceReconstructionConfig(BaseConfig):
    """Policy toggle for the optional reference-reconstruction stage."""

    enabled: bool = False
    """Whether the run should include the corresponding stage."""


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
    "PreparedBenchmarkInputs",
    "ReferenceCloudCoordinateStatus",
    "ReferenceCloudRef",
    "ReferenceCloudSource",
    "ReferenceSource",
    "ReferenceReconstructionConfig",
    "ReferenceTrajectoryRef",
    "TrajectoryBenchmarkConfig",
]
