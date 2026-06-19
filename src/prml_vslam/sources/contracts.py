"""Source-owned contracts for durable manifests and prepared references.

This module owns the contracts emitted by source adapters. Durable source
preparation returns :class:`SequenceManifest` and optional
:class:`PreparedBenchmarkInputs`; live observations use the shared
:mod:`prml_vslam.interfaces.observation` surface.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from prml_vslam.interfaces.camera import CameraIntrinsics
from prml_vslam.interfaces.observation import ObservationSequenceRef
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.sources.datasets.contracts import AdvioServingConfig, DatasetId
from prml_vslam.utils import BaseData


class Record3DTransportId(StrEnum):
    """Name the supported Record3D ingress transports across app, CLI, and source config."""

    USB = "usb"
    WIFI = "wifi"

    @property
    def label(self) -> str:
        """Return the transport label shown by launch surfaces and logs."""
        return "Wi-Fi Preview" if self is Record3DTransportId.WIFI else self.value.upper()

    def stream_hint(self) -> str:
        """Return a compact explanation of how the selected transport behaves."""
        match self:
            case Record3DTransportId.USB:
                return (
                    "USB capture uses the native `record3d` Python bindings. It can expose RGB, depth, intrinsics, "
                    "pose, and confidence."
                )
            case Record3DTransportId.WIFI:
                return (
                    "Wi-Fi Preview uses a Python-side WebRTC receiver. Enter the device address shown in the iPhone "
                    "app."
                )


class AdvioRawPoseRefs(BaseData):
    """Preserve ADVIO-native pose artifacts discovered during normalization."""

    ground_truth_csv_path: Path
    arcore_csv_path: Path | None = None
    arkit_csv_path: Path | None = None
    selected_pose_csv_path: Path | None = None


class AdvioManifestAssets(BaseData):
    """Carry ADVIO-specific normalized assets without widening the base manifest."""

    calibration_path: Path
    intrinsics: CameraIntrinsics
    T_cam_imu: FrameTransform
    pose_refs: AdvioRawPoseRefs
    fixpoints_csv_path: Path | None = None


class SequenceManifest(BaseData):
    """Describe the normalized source sequence consumed by downstream stages."""

    sequence_id: str
    dataset_id: DatasetId | None = None
    dataset_serving: AdvioServingConfig | None = None
    video_path: Path | None = None
    rgb_dir: Path | None = None
    timestamps_path: Path | None = None
    source_frame_indices_path: Path | None = None
    observation_index_path: Path | None = None
    intrinsics_path: Path | None = None
    rotation_metadata_path: Path | None = None
    advio: AdvioManifestAssets | None = None


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

    RECORD3D_LIDAR = "record3d_lidar"
    TUM_RGBD = "tum_rgbd"


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
    native_frame: str | None = None
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
    """GT/reference trajectories that may anchor benchmark comparisons."""

    candidate_trajectories: list[ReferenceTrajectoryRef] = Field(default_factory=list)
    """External baseline trajectories that may be evaluated against a reference."""

    reference_clouds: list[ReferenceCloudRef] = Field(default_factory=list)
    observation_sequences: list[ObservationSequenceRef] = Field(default_factory=list)

    def trajectory_for_source(self, source: ReferenceSource) -> ReferenceTrajectoryRef | None:
        """Return the prepared reference trajectory for one requested source."""
        matching = [reference for reference in self.reference_trajectories if reference.source is source]
        return next(
            (
                reference
                for reference in matching
                if reference.coordinate_status is ReferenceCloudCoordinateStatus.SOURCE_NATIVE
            ),
            next(iter(matching), None),
        )

    def default_observation_sequence(self) -> ObservationSequenceRef | None:
        """Return the default prepared observation sequence, when one exists."""
        return next(iter(self.observation_sequences), None)


__all__ = [
    "AdvioManifestAssets",
    "AdvioRawPoseRefs",
    "PreparedBenchmarkInputs",
    "ReferenceCloudCoordinateStatus",
    "ReferenceCloudRef",
    "ReferenceCloudSource",
    "ReferenceSource",
    "ReferenceTrajectoryRef",
    "Record3DTransportId",
    "SequenceManifest",
]
