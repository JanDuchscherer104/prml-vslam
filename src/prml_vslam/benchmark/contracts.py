"""Benchmark-policy and prepared-reference contracts kept outside the pipeline core.

This module owns the typed benchmark-side inputs and policy toggles that
surround a run without becoming part of the orchestration core. The pipeline
attaches :class:`BenchmarkConfig` to :class:`prml_vslam.pipeline.RunRequest`,
while dataset adapters materialize :class:`PreparedBenchmarkInputs` for methods,
alignment, and evaluation consumers.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from prml_vslam.utils import BaseConfig, BaseData


class ReferenceSource(StrEnum):
    """Identify one trajectory baseline available to benchmark-oriented consumers."""

    GROUND_TRUTH = "ground_truth"
    ARCORE = "arcore"
    ARKIT = "arkit"

    @property
    def label(self) -> str:
        """Return the human-readable benchmark reference-source label."""
        return {
            ReferenceSource.GROUND_TRUTH: "ground truth",
            ReferenceSource.ARCORE: "ARCore",
            ReferenceSource.ARKIT: "ARKit",
        }[self]


class ReferenceTrajectoryRef(BaseData):
    """Point to one normalized benchmark trajectory prepared for a run."""

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
    """Point to one prepared dense reference cloud available to benchmark consumers."""

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


class ReferencePointCloudSequenceRef(BaseData):
    """Describe one prepared step-wise point-cloud sequence for replay-like consumers."""

    source: ReferenceCloudSource
    """Typed source that produced the point-cloud payloads."""

    index_path: Path
    """Filesystem path to the `timestamp,index` table for the point-cloud payloads."""

    payload_root: Path
    """Directory containing the referenced point-cloud payload CSV files."""

    trajectory_path: Path
    """Filesystem path to the normalized TUM trajectory used to place payloads in world coordinates."""

    target_frame: str
    """Target frame represented by the point coordinates after pose application."""

    native_frame: str
    """Original source-native world frame for the step-wise geometry stream."""

    coordinate_status: ReferenceCloudCoordinateStatus
    """Whether the point-cloud stream remains source-native or was already aligned."""


class PreparedBenchmarkInputs(BaseData):
    """Bundle prepared reference artifacts that complement one normalized sequence.

    This DTO sits beside :class:`prml_vslam.pipeline.contracts.sequence.SequenceManifest`
    at the offline boundary: the manifest describes what the method should
    process, while these prepared inputs describe what optional benchmark
    references the rest of the package may compare against or forward through a
    wrapper.
    """

    reference_trajectories: list[ReferenceTrajectoryRef] = Field(default_factory=list)
    """Available normalized reference trajectories keyed by source."""

    reference_clouds: list[ReferenceCloudRef] = Field(default_factory=list)
    """Available normalized reference clouds keyed by source and coordinate status."""

    reference_point_cloud_sequences: list[ReferencePointCloudSequenceRef] = Field(default_factory=list)
    """Available step-wise point-cloud sequences keyed by source."""

    def trajectory_for_source(self, source: ReferenceSource) -> ReferenceTrajectoryRef | None:
        """Return the prepared trajectory baseline for one requested source."""
        return next((reference for reference in self.reference_trajectories if reference.source is source), None)

    def point_cloud_sequence_for_source(self, source: ReferenceCloudSource) -> ReferencePointCloudSequenceRef | None:
        """Return the prepared step-wise point-cloud baseline for one requested source."""
        return next(
            (reference for reference in self.reference_point_cloud_sequences if reference.source is source),
            None,
        )


class ReferenceReconstructionConfig(BaseConfig):
    """Toggle the optional reference-reconstruction stage in :mod:`prml_vslam.pipeline`."""

    enabled: bool = False
    """Whether the run should include the corresponding stage."""


class TrajectoryBenchmarkConfig(BaseConfig):
    """Configure trajectory evaluation around normalized run outputs."""

    enabled: bool = False
    """Whether the run should include trajectory evaluation."""

    baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH
    """Explicit reference source used by the trajectory evaluation stage when available."""


class CloudBenchmarkConfig(BaseConfig):
    """Toggle dense-cloud comparison stages around normalized run outputs."""

    enabled: bool = False
    """Whether the run should include dense-cloud comparison."""


class EfficiencyBenchmarkConfig(BaseConfig):
    """Toggle runtime-efficiency evaluation for one run."""

    enabled: bool = False
    """Whether the run should include efficiency metrics."""


class BenchmarkConfig(BaseConfig):
    """Collect benchmark-side stage toggles attached to one :class:`RunRequest`.

    This bundle shapes which optional benchmark stages the pipeline plans, but
    it does not perform evaluation itself. Execution lives in
    :mod:`prml_vslam.eval` and adjacent runtime owners.
    """

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
    "ReferencePointCloudSequenceRef",
    "ReferenceSource",
    "ReferenceReconstructionConfig",
    "ReferenceTrajectoryRef",
    "TrajectoryBenchmarkConfig",
]
