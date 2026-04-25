from __future__ import annotations

from pathlib import Path

import numpy as np
from evo.core.trajectory import PoseTrajectory3D

from prml_vslam.interfaces import CAMERA_RDF_FRAME, FrameTransform, ObservationIndexEntry, ObservationProvenance
from prml_vslam.sources.replay import (
    ImageSequenceObservationSource,
    ObservationStream,
    ReplayMode,
)

from .tum_rgbd_loading import (
    TumRgbdFrameAssociation,
    load_depth_image_m,
    load_tum_rgbd_associations,
    load_tum_rgbd_ground_truth,
    load_tum_rgbd_intrinsics,
    resolve_ground_truth_path,
)
from .tum_rgbd_models import TumRgbdPoseSource

TUM_RGBD_WORLD_FRAME = "tum_rgbd_mocap_world"
TUM_RGBD_CAMERA_FRAME = CAMERA_RDF_FRAME


def open_tum_rgbd_stream(
    sequence_id: str,
    sequence_dir: Path,
    *,
    pose_source: TumRgbdPoseSource = TumRgbdPoseSource.GROUND_TRUTH,
    stride: int = 1,
    loop: bool = True,
    replay_mode: ReplayMode = ReplayMode.REALTIME,
    include_depth: bool = True,
) -> ObservationStream:
    """Open one TUM RGB-D sequence through the shared image-sequence replay stack."""
    associations = load_tum_rgbd_associations(sequence_dir)
    trajectory = (
        None
        if pose_source is TumRgbdPoseSource.NONE
        else load_tum_rgbd_ground_truth(resolve_ground_truth_path(sequence_dir))
    )
    intrinsics = load_tum_rgbd_intrinsics(sequence_id, sequence_dir)
    poses_by_frame = _poses_for_associations(associations, trajectory)
    return ImageSequenceObservationSource(
        sequence_dir=sequence_dir,
        rows=[
            ObservationIndexEntry(
                seq=source_frame_index,
                timestamp_ns=int(round(association.rgb_timestamp_s * 1e9)),
                rgb_path=association.rgb_path,
                depth_path=association.depth_path,
                T_world_camera=poses_by_frame[source_frame_index],
                intrinsics=intrinsics,
                provenance=ObservationProvenance(
                    source_id="tum_rgbd",
                    dataset_id="tum_rgbd",
                    sequence_id=sequence_id,
                    sequence_name=sequence_id,
                    pose_source=pose_source.value,
                    source_frame_index=source_frame_index,
                ),
            )
            for source_frame_index, association in enumerate(associations)
        ],
        stride=stride,
        loop=loop,
        replay_mode=replay_mode,
        include_depth=include_depth,
        depth_loader=load_depth_image_m,
    )


def _poses_for_associations(
    associations: list[TumRgbdFrameAssociation],
    trajectory: PoseTrajectory3D | None,
) -> list[FrameTransform | None]:
    if trajectory is None:
        return [None] * len(associations)
    return [
        None
        if association.pose_index is None
        else FrameTransform.from_matrix(
            np.asarray(trajectory.poses_se3[association.pose_index], dtype=np.float64),
            target_frame=TUM_RGBD_WORLD_FRAME,
            source_frame=TUM_RGBD_CAMERA_FRAME,
        )
        for association in associations
    ]
