from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from numpy.typing import NDArray

from prml_vslam.interfaces import FrameTransform
from prml_vslam.interfaces.transforms import project_rotation_to_so3
from prml_vslam.sources.datasets.contracts import (
    AdvioPoseFrameMode,
    AdvioPoseSource,
    AdvioServingConfig,
    selected_advio_pose_source,
)

from .advio_frames import transform_advio_trajectory_to_rdf
from .advio_geometry import Sim3Alignment, fit_planar_rigid_alignment, interpolate_trajectory_poses
from .advio_loading import load_advio_trajectory

if TYPE_CHECKING:
    from .advio_models import AdvioSceneMetadata
    from .advio_sequence import AdvioSequencePaths


def resolve_advio_pose_csv_path(
    *,
    paths: AdvioSequencePaths,
    pose_source: AdvioPoseSource,
) -> Path | None:
    """Return the CSV backing one ADVIO pose provider."""
    return {
        AdvioPoseSource.GROUND_TRUTH: paths.ground_truth_csv_path,
        AdvioPoseSource.ARCORE: paths.arcore_csv_path if paths.arcore_csv_path.exists() else None,
        AdvioPoseSource.ARKIT: paths.arkit_csv_path,
        AdvioPoseSource.TANGO_RAW: paths.tango_raw_csv_path,
        AdvioPoseSource.TANGO_AREA_LEARNING: paths.tango_area_learning_csv_path,
        AdvioPoseSource.NONE: None,
    }[pose_source]


def _load_pose_trajectory(
    paths: AdvioSequencePaths,
    scene: AdvioSceneMetadata,
    pose_source: AdvioPoseSource,
) -> PoseTrajectory3D | None:
    path = resolve_advio_pose_csv_path(paths=paths, pose_source=pose_source)
    if path is None:
        if pose_source is AdvioPoseSource.NONE:
            return None
        raise FileNotFoundError(f"Sequence {scene.sequence_slug} does not include {pose_source.label} pose data.")
    return transform_advio_trajectory_to_rdf(load_advio_trajectory(path), source=pose_source)


def load_advio_served_trajectory(
    *,
    paths: AdvioSequencePaths,
    scene: AdvioSceneMetadata,
    dataset_serving: AdvioServingConfig | None,
) -> PoseTrajectory3D:
    """Load one ADVIO trajectory using the requested serving semantics."""
    pose_source = selected_advio_pose_source(dataset_serving)
    trajectory = _load_pose_trajectory(paths, scene, pose_source)
    if trajectory is None:
        raise ValueError("ADVIO serving config must resolve to a real pose provider.")
    return serve_loaded_advio_trajectory(
        trajectory=trajectory,
        ground_truth_trajectory=transform_advio_trajectory_to_rdf(
            load_advio_trajectory(paths.ground_truth_csv_path),
            source=AdvioPoseSource.GROUND_TRUTH,
        ),
        pose_source=pose_source,
        pose_frame_mode=(
            AdvioPoseFrameMode.PROVIDER_WORLD if dataset_serving is None else dataset_serving.pose_frame_mode
        ),
    )


def serve_loaded_advio_trajectory(
    *,
    trajectory: PoseTrajectory3D,
    ground_truth_trajectory: PoseTrajectory3D,
    pose_source: AdvioPoseSource,
    pose_frame_mode: AdvioPoseFrameMode,
) -> PoseTrajectory3D:
    """Apply one ADVIO serving mode to an already loaded trajectory."""
    match pose_frame_mode:
        case AdvioPoseFrameMode.PROVIDER_WORLD:
            return trajectory
        case AdvioPoseFrameMode.LOCAL_FIRST_POSE:
            return _rebase_trajectory_to_first_pose(trajectory)
        case AdvioPoseFrameMode.REFERENCE_WORLD:
            if pose_source is AdvioPoseSource.GROUND_TRUTH:
                return trajectory
            alignment = fit_planar_rigid_alignment(
                source_trajectory=trajectory,
                target_trajectory=ground_truth_trajectory,
                source_frame=_advio_provider_world_frame(pose_source),
                target_frame="advio_gt_world",
            )
            return _transform_trajectory_with_alignment(trajectory, alignment)


def _poses_for_frame_timestamps(
    frame_timestamps_ns: NDArray[np.int64],
    trajectory: PoseTrajectory3D | None,
    *,
    target_frame: str = "world",
    source_frame: str = "camera",
) -> list[FrameTransform | None]:
    if trajectory is None or frame_timestamps_ns.size == 0:
        return [None] * int(frame_timestamps_ns.size)
    return interpolate_trajectory_poses(
        trajectory,
        frame_timestamps_ns.astype(np.float64) / 1e9,
        target_frame=target_frame,
        source_frame=source_frame,
    )


def advio_pose_frames(*, pose_source: AdvioPoseSource, pose_frame_mode: AdvioPoseFrameMode) -> tuple[str, str]:
    """Return explicit target/source frame labels for served ADVIO camera poses."""
    match pose_frame_mode:
        case AdvioPoseFrameMode.PROVIDER_WORLD:
            target_frame = _advio_provider_world_frame(pose_source)
        case AdvioPoseFrameMode.LOCAL_FIRST_POSE:
            target_frame = f"{_advio_provider_world_frame(pose_source)}_local_first_pose"
        case AdvioPoseFrameMode.REFERENCE_WORLD:
            target_frame = "advio_gt_world"
    return target_frame, _advio_camera_frame(pose_source)


def _advio_provider_world_frame(pose_source: AdvioPoseSource) -> str:
    return {
        AdvioPoseSource.GROUND_TRUTH: "advio_gt_world",
        AdvioPoseSource.ARCORE: "advio_arcore_world",
        AdvioPoseSource.ARKIT: "advio_arkit_world",
        AdvioPoseSource.TANGO_RAW: "advio_tango_raw_world",
        AdvioPoseSource.TANGO_AREA_LEARNING: "advio_tango_area_learning_world",
    }.get(pose_source, f"advio_{pose_source.value}_world")


def _advio_camera_frame(pose_source: AdvioPoseSource) -> str:
    return {
        AdvioPoseSource.GROUND_TRUTH: "advio_iphone_camera",
        AdvioPoseSource.ARCORE: "advio_pixel_camera",
        AdvioPoseSource.ARKIT: "advio_iphone_camera",
        AdvioPoseSource.TANGO_RAW: "advio_tango_raw_device",
        AdvioPoseSource.TANGO_AREA_LEARNING: "advio_tango_area_learning_device",
    }.get(pose_source, f"advio_{pose_source.value}_camera")


def _rebase_trajectory_to_first_pose(trajectory: PoseTrajectory3D) -> PoseTrajectory3D:
    if len(trajectory.poses_se3) == 0:
        return trajectory
    first_pose_inv = np.linalg.inv(np.asarray(trajectory.poses_se3[0], dtype=np.float64))
    rebased_poses = [first_pose_inv @ np.asarray(pose, dtype=np.float64) for pose in trajectory.poses_se3]
    return _trajectory_from_pose_matrices(rebased_poses, trajectory.timestamps)


def _transform_trajectory_with_alignment(trajectory: PoseTrajectory3D, alignment: Sim3Alignment) -> PoseTrajectory3D:
    rotation = np.asarray(alignment.rotation, dtype=np.float64)
    translation = np.asarray(alignment.translation, dtype=np.float64)
    scale = float(alignment.scale)
    transformed_poses: list[np.ndarray] = []
    for pose in trajectory.poses_se3:
        pose_matrix = np.asarray(pose, dtype=np.float64)
        transformed_pose = np.eye(4, dtype=np.float64)
        transformed_pose[:3, :3] = project_rotation_to_so3(rotation @ pose_matrix[:3, :3])
        transformed_pose[:3, 3] = scale * (rotation @ pose_matrix[:3, 3]) + translation
        transformed_poses.append(transformed_pose)
    return _trajectory_from_pose_matrices(transformed_poses, trajectory.timestamps)


def _trajectory_from_pose_matrices(
    poses_se3: list[np.ndarray],
    timestamps_s: NDArray[np.float64] | list[float],
) -> PoseTrajectory3D:
    positions_xyz = np.asarray([pose[:3, 3] for pose in poses_se3], dtype=np.float64)
    orientations_quat_wxyz = np.asarray(
        [
            FrameTransform.from_matrix(np.asarray(pose, dtype=np.float64)).quaternion_xyzw()[[3, 0, 1, 2]]
            for pose in poses_se3
        ],
        dtype=np.float64,
    )
    return PoseTrajectory3D(
        positions_xyz=positions_xyz,
        orientations_quat_wxyz=orientations_quat_wxyz,
        timestamps=np.asarray(timestamps_s, dtype=np.float64),
    )
