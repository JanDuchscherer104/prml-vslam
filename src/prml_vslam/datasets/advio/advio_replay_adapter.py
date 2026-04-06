from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from numpy.typing import NDArray

from prml_vslam.interfaces import CameraIntrinsics, FramePacket, SE3Pose
from prml_vslam.io.cv2_producer import Cv2ProducerConfig, Cv2ReplayMode, open_cv2_replay_stream
from prml_vslam.protocols import FramePacketStream

from .advio_loading import load_advio_calibration, load_advio_frame_timestamps_ns, load_advio_trajectory
from .advio_models import AdvioPoseSource

if TYPE_CHECKING:
    from .advio_models import AdvioSceneMetadata
    from .advio_sequence import AdvioSequence, AdvioSequencePaths


def open_advio_stream(
    sequence: AdvioSequence,
    *,
    pose_source: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH,
    stride: int = 1,
    loop: bool = True,
    replay_mode: Cv2ReplayMode = Cv2ReplayMode.REALTIME,
    respect_video_rotation: bool = False,
) -> FramePacketStream:
    from .advio_sequence import AdvioSequencePaths

    scene = sequence.scene
    paths = AdvioSequencePaths.resolve(sequence.config, scene, require_arcore=False)
    frame_timestamps_ns = load_advio_frame_timestamps_ns(paths.frame_timestamps_path)
    calibration = load_advio_calibration(paths.calibration_path)
    stream = open_cv2_replay_stream(
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
    return _wrap_with_advio_video_rotation(stream, video_path=paths.video_path) if respect_video_rotation else stream


def _load_pose_trajectory(
    paths: AdvioSequencePaths,
    scene: AdvioSceneMetadata,
    pose_source: AdvioPoseSource,
) -> PoseTrajectory3D | None:
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
    trajectory: PoseTrajectory3D | None,
) -> list[SE3Pose | None]:
    if trajectory is None or frame_timestamps_ns.size == 0:
        return [None] * int(frame_timestamps_ns.size)
    target_timestamps_s = frame_timestamps_ns.astype(np.float64) / 1e9
    source_timestamps_s = np.asarray(trajectory.timestamps, dtype=np.float64)
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
    poses: list[SE3Pose] = []
    for position, nearest_index in zip(interpolated_positions, nearest_indices, strict=True):
        nearest_pose = SE3Pose.from_matrix(np.asarray(trajectory.poses_se3[int(nearest_index)], dtype=np.float64))
        poses.append(
            SE3Pose(
                qx=nearest_pose.qx,
                qy=nearest_pose.qy,
                qz=nearest_pose.qz,
                qw=nearest_pose.qw,
                tx=float(position[0]),
                ty=float(position[1]),
                tz=float(position[2]),
            )
        )
    return poses


def _wrap_with_advio_video_rotation(stream: FramePacketStream, *, video_path: Path) -> FramePacketStream:
    rotation_degrees = read_advio_video_rotation_degrees(video_path)
    return stream if rotation_degrees == 0 else _RotatedVideoStream(stream, rotation_degrees)


class _RotatedVideoStream:
    def __init__(self, stream: FramePacketStream, rotation_degrees: int) -> None:
        self._stream = stream
        self._rotation_degrees = rotation_degrees

    def connect(self) -> Path:
        return self._stream.connect()

    def disconnect(self) -> None:
        self._stream.disconnect()

    def wait_for_packet(self, timeout_seconds: float | None = None) -> FramePacket:
        packet = self._stream.wait_for_packet(timeout_seconds)
        return packet.model_copy(
            update={
                "rgb": _rotate_rgb(packet.rgb, self._rotation_degrees),
                "intrinsics": _rotate_intrinsics(packet.intrinsics, self._rotation_degrees),
                "metadata": {**packet.metadata, "video_rotation_degrees": self._rotation_degrees},
            }
        )


def _load_pyav() -> object:
    try:
        import av
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Rotation-aware ADVIO replay requires the optional `av` dependency. Install it with `uv sync --extra replay`."
        ) from exc
    return av


def read_advio_video_rotation_degrees(video_path: Path) -> int:
    av = _load_pyav()
    try:
        with av.open(str(video_path)) as container:
            stream = next(iter(container.streams.video), None)
            if stream is None:
                raise ValueError("No video stream found.")
            if (rotation := _rotation_from_metadata(getattr(stream, "metadata", {}))) is not None:
                return rotation
            for frame in container.decode(video=0):
                return _rotation_from_frame(frame)
    except Exception as exc:
        raise ValueError(f"Failed to read ADVIO video rotation metadata from {video_path}: {exc}") from exc
    return 0


def _rotation_from_metadata(metadata: dict[str, str] | None) -> int | None:
    for key in ("rotate", "rotation"):
        try:
            return None if metadata is None or metadata.get(key) is None else _normalize_rotation(float(metadata[key]))
        except (KeyError, TypeError, ValueError):
            continue
    return None


def _rotation_from_frame(frame: object) -> int:
    return next(
        (
            rotation
            for side_data in getattr(frame, "side_data", ())
            if "display" in str(getattr(side_data, "type", "")).lower()
            and (rotation := _rotation_from_side_data(side_data)) is not None
        ),
        0,
    )


def _rotation_from_side_data(side_data: object) -> int | None:
    for attr in ("rotation", "angle"):
        value = getattr(side_data, attr, None)
        if isinstance(value, str | int | float):
            try:
                return _normalize_rotation(float(value))
            except ValueError:
                return None
    to_ndarray = getattr(side_data, "to_ndarray", None)
    if not callable(to_ndarray):
        return None
    matrix = np.asarray(to_ndarray(), dtype=np.float64)
    if matrix.size < 4:
        return None
    matrix = matrix.reshape(3, 3) if matrix.size >= 9 else matrix.reshape(2, 2)
    return _normalize_rotation(np.degrees(np.arctan2(matrix[1, 0], matrix[0, 0])))


def _normalize_rotation(rotation_degrees: float) -> int:
    return int(np.rint(rotation_degrees / 90.0) * 90) % 360


def _rotate_rgb(rgb: NDArray[np.uint8], rotation_degrees: int) -> NDArray[np.uint8]:
    quarter_turns = {90: 3, 180: 2, 270: 1}.get(rotation_degrees)
    return rgb if quarter_turns is None else np.ascontiguousarray(np.rot90(rgb, k=quarter_turns))


def _rotate_intrinsics(
    intrinsics: CameraIntrinsics | None,
    rotation_degrees: int,
) -> CameraIntrinsics | None:
    if intrinsics is None or rotation_degrees == 0:
        return intrinsics
    match rotation_degrees:
        case 90:
            update = {
                "width_px": intrinsics.height_px,
                "height_px": intrinsics.width_px,
                "fx": intrinsics.fy,
                "fy": intrinsics.fx,
                "cx": intrinsics.height_px - intrinsics.cy,
                "cy": intrinsics.cx,
            }
        case 180:
            update = {"cx": intrinsics.width_px - intrinsics.cx, "cy": intrinsics.height_px - intrinsics.cy}
        case 270:
            update = {
                "width_px": intrinsics.height_px,
                "height_px": intrinsics.width_px,
                "fx": intrinsics.fy,
                "fy": intrinsics.fx,
                "cx": intrinsics.cy,
                "cy": intrinsics.width_px - intrinsics.cx,
            }
        case _:
            return intrinsics
    return intrinsics.model_copy(update=update)
