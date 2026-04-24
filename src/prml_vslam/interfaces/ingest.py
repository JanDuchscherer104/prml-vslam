"""Canonical source-normalization DTOs.

The ingest interface is the handoff from dataset/video/live-source owners into
the artifact-first pipeline. A source runtime produces a
:class:`SequenceManifest` for the normalized RGB/video side. Prepared reference
inputs live in :mod:`prml_vslam.sources.contracts`.
"""

from __future__ import annotations

from pathlib import Path

from prml_vslam.datasets.contracts import DatasetId, DatasetServingConfig
from prml_vslam.interfaces.camera import CameraIntrinsics
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.utils import BaseData

# TODO: ingest is legacy naming.


class AdvioRawPoseRefs(BaseData):
    """Preserve ADVIO-native pose artifacts discovered during normalization.

    These paths are provenance for replay, baseline selection, and later
    diagnostics. They are not automatically aligned or relabelled; consumers
    must choose a :class:`prml_vslam.sources.contracts.ReferenceSource`
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


__all__ = [
    "AdvioManifestAssets",
    "AdvioRawPoseRefs",
    "SequenceManifest",
]
