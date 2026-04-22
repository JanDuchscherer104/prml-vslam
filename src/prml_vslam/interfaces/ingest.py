"""Canonical source-normalization and prepared-reference DTOs.

The ingest interface is the handoff from dataset/video/live-source owners into
the artifact-first pipeline. A source runtime produces a
:class:`SequenceManifest` for the normalized RGB/video side and may also
produce :class:`PreparedBenchmarkInputs` for reference trajectories, reference
clouds, or RGB-D observations. Downstream stages should depend on these typed
objects instead of inspecting source-specific folders directly.
"""

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
    """Preserve ADVIO-native pose artifacts discovered during normalization.

    These paths are provenance for replay, baseline selection, and later
    diagnostics. They are not automatically aligned or relabelled; consumers
    must choose a :class:`prml_vslam.benchmark.contracts.ReferenceSource`
    explicitly before using one as a benchmark trajectory.
    """

    ground_truth_csv_path: Path
    arcore_csv_path: Path | None = None
    arkit_csv_path: Path | None = None
    tango_raw_csv_path: Path | None = None
    tango_area_learning_csv_path: Path | None = None
    selected_pose_csv_path: Path | None = None


class AdvioManifestAssets(BaseData):
    """Carry ADVIO-specific normalized assets without widening the base manifest.

    ADVIO contributes calibration, IMU-camera extrinsics, optional fixpoints,
    and Tango point-cloud references that are useful for replay and evaluation.
    Keeping them in this nested DTO lets :class:`SequenceManifest` stay stable
    for non-ADVIO sources while preserving typed access for ADVIO-aware stages.
    """

    calibration_path: Path
    intrinsics: CameraIntrinsics
    T_cam_imu: FrameTransform
    pose_refs: AdvioRawPoseRefs
    fixpoints_csv_path: Path | None = None
    tango_point_cloud_index_path: Path | None = None
    tango_payload_root: Path | None = None


class SequenceManifest(BaseData):
    """Describe the normalized source sequence consumed by downstream stages.

    This is the canonical offline boundary for SLAM, evaluation, alignment, and
    reconstruction. It names repository-owned materialized inputs such as
    extracted RGB frames, timestamps, intrinsics, and dataset-specific side
    metadata. It must remain method-agnostic: backend-specific resizing,
    preprocessing, or native workspace layout belongs in the method wrapper.
    """

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
    """Reference one prepared trajectory in a source-declared frame.

    The file is usually a TUM trajectory consumed by
    :mod:`prml_vslam.eval`. Alignment policy is selected later by benchmark and
    evaluation config; ingest does not silently align or normalize references
    beyond making the artifact available.
    """

    source: ReferenceSource
    path: Path


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

    This DTO keeps benchmark-side data explicit and separate from the primary
    source manifest. Stages can request a reference by source id or use the
    default RGB-D observation sequence, but absence is a valid state and should
    produce disabled/unavailable evaluation stages rather than hidden fallback
    behavior.
    """

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
    """Bundle the source-stage result stored in target runtime state.

    The target :class:`prml_vslam.pipeline.stages.base.contracts.StageResult`
    stores this DTO as the source payload so downstream stage input builders can
    retrieve the manifest and optional references through one typed result,
    replacing the older split fields in legacy completion payloads.
    """

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
