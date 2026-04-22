"""Canonical ingest- and benchmark-facing stage DTOs."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from prml_vslam.benchmark.contracts import (
    ReferenceCloudCoordinateStatus,
    ReferenceCloudSource,
    ReferenceSource,
)
from prml_vslam.datasets.contracts import DatasetId, DatasetServingConfig
from prml_vslam.interfaces.camera import CameraIntrinsics
from prml_vslam.interfaces.rgbd import RgbdObservationSequenceRef
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.utils import BaseData


class AdvioRawPoseRefs(BaseData):
    """Relevant ADVIO raw pose artifacts preserved in the normalized manifest."""

    ground_truth_csv_path: Path
    arcore_csv_path: Path | None = None
    arkit_csv_path: Path | None = None
    tango_raw_csv_path: Path | None = None
    tango_area_learning_csv_path: Path | None = None
    selected_pose_csv_path: Path | None = None


class AdvioManifestAssets(BaseData):
    """ADVIO-specific ingest payload preserved for downstream consumers."""

    calibration_path: Path
    intrinsics: CameraIntrinsics
    T_cam_imu: FrameTransform
    pose_refs: AdvioRawPoseRefs
    fixpoints_csv_path: Path | None = None
    tango_point_cloud_index_path: Path | None = None
    tango_payload_root: Path | None = None


class SequenceManifest(BaseData):
    """Normalized artifact boundary between input ingestion and benchmark execution."""

    sequence_id: str
    dataset_id: DatasetId | None = None
    dataset_serving: DatasetServingConfig | None = None
    video_path: Path | None = None
    rgb_dir: Path | None = None
    timestamps_path: Path | None = None
    intrinsics_path: Path | None = None
    rotation_metadata_path: Path | None = None
    advio: AdvioManifestAssets | None = None


class ReferenceTrajectoryRef(BaseData):
    """One prepared reference trajectory available to a benchmark run."""

    source: ReferenceSource
    path: Path


class ReferenceCloudRef(BaseData):
    """One prepared reference cloud available to a benchmark run."""

    source: ReferenceCloudSource
    path: Path
    metadata_path: Path
    target_frame: str
    coordinate_status: ReferenceCloudCoordinateStatus


class ReferencePointCloudSequenceRef(BaseData):
    """One prepared step-wise reference point-cloud stream for replay-like use."""

    source: ReferenceCloudSource
    index_path: Path
    payload_root: Path
    trajectory_path: Path
    target_frame: str
    native_frame: str
    coordinate_status: ReferenceCloudCoordinateStatus


class PreparedBenchmarkInputs(BaseData):
    """Prepared benchmark-side inputs discovered for one normalized sequence."""

    reference_trajectories: list[ReferenceTrajectoryRef] = Field(default_factory=list)
    reference_clouds: list[ReferenceCloudRef] = Field(default_factory=list)
    reference_point_cloud_sequences: list[ReferencePointCloudSequenceRef] = Field(default_factory=list)
    rgbd_observation_sequences: list[RgbdObservationSequenceRef] = Field(default_factory=list)

    def trajectory_for_source(self, source: ReferenceSource) -> ReferenceTrajectoryRef | None:
        """Return the prepared reference trajectory for one requested source."""
        return next((reference for reference in self.reference_trajectories if reference.source is source), None)

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
    """Normalized source-stage payload retained for downstream runtime stages."""

    sequence_manifest: SequenceManifest
    """Canonical normalized sequence manifest for the run-owned input layout."""

    benchmark_inputs: PreparedBenchmarkInputs | None = None
    """Optional prepared reference and replay inputs for benchmark stages."""


__all__ = [
    "AdvioManifestAssets",
    "AdvioRawPoseRefs",
    "PreparedBenchmarkInputs",
    "ReferenceCloudCoordinateStatus",
    "ReferenceCloudRef",
    "ReferenceCloudSource",
    "ReferencePointCloudSequenceRef",
    "ReferenceSource",
    "ReferenceTrajectoryRef",
    "RgbdObservationSequenceRef",
    "SequenceManifest",
    "SourceStageOutput",
]
