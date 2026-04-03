from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from prml_vslam.datasets.interfaces import TimedPoseTrajectory
from prml_vslam.io.cv2_producer import Cv2FrameProducer, Cv2ProducerConfig, Cv2ReplayMode
from prml_vslam.io.interfaces import CameraPose, VideoPacketStream

from .advio_loading import load_advio_calibration, load_advio_frame_timestamps_ns, load_advio_trajectory
from .advio_models import AdvioPoseSource
from .advio_replay import wrap_with_advio_video_rotation

if TYPE_CHECKING:
    from .advio_sequence import AdvioSequence


DEFAULT_REPLAY_MODE = Cv2ReplayMode.REALTIME
ReplayMode = Cv2ReplayMode
ReplayStream = VideoPacketStream


def open_advio_stream(
    sequence: AdvioSequence,
    *,
    pose_source: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH,
    stride: int = 1,
    loop: bool = True,
    replay_mode: Cv2ReplayMode = DEFAULT_REPLAY_MODE,
    respect_video_rotation: bool = False,
) -> VideoPacketStream:
    from .advio_sequence import AdvioSequencePaths

    scene = sequence.scene
    paths = AdvioSequencePaths.resolve(sequence.config, scene, require_arcore=False)
    frame_timestamps_ns = load_advio_frame_timestamps_ns(paths.frame_timestamps_path)
    calibration = load_advio_calibration(paths.calibration_path)
    stream = Cv2FrameProducer(
        Cv2ProducerConfig(
            video_path=paths.video_path,
            frame_timestamps_ns=frame_timestamps_ns.tolist(),
            stride=stride,
            loop=loop,
            replay_mode=replay_mode,
            intrinsics=calibration.intrinsics,
            poses_by_frame=_poses_for_frame_timestamps(
                frame_timestamps_ns, _load_pose_trajectory(paths, scene, pose_source)
            ),
            static_metadata={
                "dataset": "ADVIO",
                "sequence_id": scene.sequence_id,
                "sequence_name": scene.sequence_slug,
                "pose_source": pose_source.value,
            },
        )
    )
    return wrap_with_advio_video_rotation(stream, video_path=paths.video_path) if respect_video_rotation else stream


def _load_pose_trajectory(
    paths,
    scene,
    pose_source: AdvioPoseSource,
) -> TimedPoseTrajectory | None:
    match pose_source:
        case AdvioPoseSource.GROUND_TRUTH:
            return load_advio_trajectory(paths.ground_truth_csv_path)
        case AdvioPoseSource.ARCORE:
            if not paths.arcore_csv_path.exists():
                raise FileNotFoundError(f"Required ADVIO pose CSV is missing: {paths.arcore_csv_path}")
            return load_advio_trajectory(paths.arcore_csv_path)
        case AdvioPoseSource.ARKIT:
            if paths.arkit_csv_path is None:
                raise FileNotFoundError(f"Sequence {scene.sequence_slug} does not include an ARKit baseline CSV.")
            return load_advio_trajectory(paths.arkit_csv_path)
        case AdvioPoseSource.NONE:
            return None


def _poses_for_frame_timestamps(
    frame_timestamps_ns: NDArray[np.int64],
    trajectory: TimedPoseTrajectory | None,
) -> list[CameraPose | None]:
    if trajectory is None or frame_timestamps_ns.size == 0:
        return [None] * int(frame_timestamps_ns.size)
    target_timestamps_s = frame_timestamps_ns.astype(np.float64) / 1e9
    source_timestamps_s = trajectory.timestamps_s
    interpolated_positions = np.column_stack(
        [np.interp(target_timestamps_s, source_timestamps_s, trajectory.positions_xyz[:, axis]) for axis in range(3)]
    )
    nearest_indices = np.searchsorted(source_timestamps_s, target_timestamps_s, side="left")
    nearest_indices = np.clip(nearest_indices, 0, max(len(source_timestamps_s) - 1, 0))
    previous_indices = np.clip(nearest_indices - 1, 0, max(len(source_timestamps_s) - 1, 0))
    pick_previous = np.abs(target_timestamps_s - source_timestamps_s[previous_indices]) <= np.abs(
        source_timestamps_s[nearest_indices] - target_timestamps_s
    )
    nearest_indices = np.where(pick_previous, previous_indices, nearest_indices)
    poses: list[CameraPose] = []
    for position, nearest_index in zip(interpolated_positions, nearest_indices, strict=True):
        quaternion = trajectory.quaternions_xyzw[int(nearest_index)]
        poses.append(
            CameraPose(
                qx=float(quaternion[0]),
                qy=float(quaternion[1]),
                qz=float(quaternion[2]),
                qw=float(quaternion[3]),
                tx=float(position[0]),
                ty=float(position[1]),
                tz=float(position[2]),
            )
        )
    return poses
