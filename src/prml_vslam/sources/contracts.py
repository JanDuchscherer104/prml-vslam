"""Source-stage reference contracts and runtime payloads.

The source stage owns prepared reference inputs because datasets and live
sources materialize them alongside the normalized source manifest. Downstream
stages choose from these typed references rather than inspecting source-owned
folders directly.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from prml_vslam.interfaces.ingest import SequenceManifest
from prml_vslam.interfaces.rgbd import RgbdObservationSequenceRef
from prml_vslam.utils import BaseData


class ReferenceSource(StrEnum):
    """Typed source identifier for one prepared reference trajectory.

    ``GROUND_TRUTH`` is the preferred benchmark reference when available.
    ``ARCORE`` and ``ARKIT`` are optional external baseline identifiers that
    ADVIO currently materializes for comparison.
    """

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
    """Typed source identifier for one prepared reference cloud."""

    TANGO_AREA_LEARNING = "tango_area_learning"


class ReferenceCloudCoordinateStatus(StrEnum):
    """Coordinate status for one prepared reference cloud or trajectory."""

    SOURCE_NATIVE = "source_native"
    ALIGNED = "aligned"


class ReferenceTrajectoryRef(BaseData):
    """Reference one prepared trajectory in a source-declared frame.

    The file is usually a TUM trajectory consumed by
    :mod:`prml_vslam.eval`. The frame and coordinate-status fields are explicit
    because TUM does not encode whether a provider trajectory is source-native
    or already aligned into a benchmark target frame.
    """

    source: ReferenceSource
    path: Path
    target_frame: str | None = None
    native_frame: str | None = None
    coordinate_status: ReferenceCloudCoordinateStatus | None = None
    metadata_path: Path | None = None


class ReferenceCloudRef(BaseData):
    """Reference one prepared static point cloud for comparison or reconstruction.

    The frame and coordinate-status fields are part of the contract because PLY
    alone cannot describe whether a cloud is native, aligned, or already in the
    benchmark target frame.
    """

    source: ReferenceCloudSource
    path: Path
    metadata_path: Path
    target_frame: str
    coordinate_status: ReferenceCloudCoordinateStatus


class ReferencePointCloudSequenceRef(BaseData):
    """Reference a time-ordered reference-cloud sequence for replay adapters.

    ADVIO Tango payloads use this boundary to expose point-cloud samples without
    forcing the runtime packet stream to become dataset-specific. Consumers must
    preserve :attr:`target_frame`, :attr:`native_frame`, and
    :attr:`coordinate_status` when comparing against SLAM geometry.
    """

    source: ReferenceCloudSource
    index_path: Path
    payload_root: Path
    trajectory_path: Path
    target_frame: str
    native_frame: str
    coordinate_status: ReferenceCloudCoordinateStatus


class PreparedBenchmarkInputs(BaseData):
    """Collect optional reference inputs prepared alongside a source sequence.

    This DTO keeps source-prepared benchmark data explicit and separate from the
    primary source manifest. Stages can request a reference by source id or use
    the default RGB-D observation sequence, but absence is valid and should
    produce disabled/unavailable evaluation stages rather than hidden fallback
    behavior.
    """

    reference_trajectories: list[ReferenceTrajectoryRef] = Field(default_factory=list)
    reference_clouds: list[ReferenceCloudRef] = Field(default_factory=list)
    reference_point_cloud_sequences: list[ReferencePointCloudSequenceRef] = Field(default_factory=list)
    rgbd_observation_sequences: list[RgbdObservationSequenceRef] = Field(default_factory=list)

    def trajectory_for_source(self, source: ReferenceSource) -> ReferenceTrajectoryRef | None:
        """Return the prepared reference trajectory for one requested source."""
        matching = [reference for reference in self.reference_trajectories if reference.source is source]
        return next(
            (
                reference
                for reference in matching
                if reference.coordinate_status is not ReferenceCloudCoordinateStatus.SOURCE_NATIVE
            ),
            next(iter(matching), None),
        )

    def point_cloud_sequence_for_source(self, source: ReferenceCloudSource) -> ReferencePointCloudSequenceRef | None:
        """Return the prepared point-cloud sequence for one requested source."""
        return next(
            (reference for reference in self.reference_point_cloud_sequences if reference.source is source),
            None,
        )

    def default_rgbd_observation_sequence(self) -> RgbdObservationSequenceRef | None:
        """Return the default prepared RGB-D observation sequence, when one exists."""
        return next(iter(self.rgbd_observation_sequences), None)


class SourceStageOutput(BaseData):
    """Bundle the normalized source result for downstream stages."""

    sequence_manifest: SequenceManifest
    benchmark_inputs: PreparedBenchmarkInputs | None = None


__all__ = [
    "PreparedBenchmarkInputs",
    "ReferenceCloudCoordinateStatus",
    "ReferenceCloudRef",
    "ReferenceCloudSource",
    "ReferencePointCloudSequenceRef",
    "ReferenceSource",
    "ReferenceTrajectoryRef",
    "SourceStageOutput",
]
