from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from numpy.typing import NDArray

from prml_vslam.interfaces import FrameTransform
from prml_vslam.sources.datasets.contracts import (
    AdvioPoseFrameMode,
    AdvioPoseSource,
    AdvioServingConfig,
    selected_advio_pose_source,
)
from prml_vslam.utils.geometry import trajectory_relative_to_first_pose

from .advio_frames import transform_advio_trajectory_to_rdf
from .advio_geometry import interpolate_trajectory_poses
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
        AdvioPoseSource.NONE: None,
    }[pose_source]


def load_advio_served_trajectory(
    *,
    paths: AdvioSequencePaths,
    scene: AdvioSceneMetadata,
    dataset_serving: AdvioServingConfig | None,
) -> PoseTrajectory3D:
    """Load one ADVIO trajectory using the requested serving semantics."""
    pose_source = selected_advio_pose_source(dataset_serving)
    path = resolve_advio_pose_csv_path(paths=paths, pose_source=pose_source)
    if path is None:
        if pose_source is not AdvioPoseSource.NONE:
            raise FileNotFoundError(f"Sequence {scene.sequence_slug} does not include {pose_source.label} pose data.")
        raise ValueError("ADVIO serving config must resolve to a real pose provider.")
    trajectory = transform_advio_trajectory_to_rdf(load_advio_trajectory(path), source=pose_source)
    return serve_loaded_advio_trajectory(
        trajectory=trajectory,
        pose_frame_mode=(
            AdvioPoseFrameMode.PROVIDER_WORLD if dataset_serving is None else dataset_serving.pose_frame_mode
        ),
    )


def serve_loaded_advio_trajectory(
    *,
    trajectory: PoseTrajectory3D,
    pose_frame_mode: AdvioPoseFrameMode,
) -> PoseTrajectory3D:
    """Apply one ADVIO serving mode to an already loaded trajectory."""
    match pose_frame_mode:
        case AdvioPoseFrameMode.PROVIDER_WORLD:
            return trajectory
        case AdvioPoseFrameMode.LOCAL_FIRST_POSE:
            return trajectory_relative_to_first_pose(trajectory)


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
    return target_frame, _advio_camera_frame(pose_source)


def _advio_provider_world_frame(pose_source: AdvioPoseSource) -> str:
    return {
        AdvioPoseSource.GROUND_TRUTH: "advio_gt_world",
        AdvioPoseSource.ARCORE: "advio_arcore_world",
        AdvioPoseSource.ARKIT: "advio_arkit_world",
    }.get(pose_source, f"advio_{pose_source.value}_world")


def _advio_camera_frame(pose_source: AdvioPoseSource) -> str:
    return {
        AdvioPoseSource.GROUND_TRUTH: "advio_iphone_camera",
        AdvioPoseSource.ARCORE: "advio_pixel_camera",
        AdvioPoseSource.ARKIT: "advio_iphone_camera",
    }.get(pose_source, f"advio_{pose_source.value}_camera")
