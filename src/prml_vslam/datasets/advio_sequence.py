from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from prml_vslam.datasets.interfaces import TimedPoseTrajectory
from prml_vslam.io.cv2_producer import Cv2FrameProducer, Cv2ProducerConfig, Cv2ReplayMode
from prml_vslam.io.interfaces import CameraPose, VideoPacketStream
from prml_vslam.pipeline.contracts import SequenceManifest
from prml_vslam.utils import BaseData

from .advio_layout import (
    list_local_sequence_ids,
    load_advio_catalog,
    resolve_calibration_path,
    resolve_ground_truth_csv,
    resolve_optional_arkit_csv,
    resolve_optional_gyroscope_csv,
    resolve_sequence_dir,
    scene_for_sequence_id,
)
from .advio_loading import (
    AdvioCalibration,
    load_advio_calibration,
    load_advio_frame_timestamps_ns,
    load_advio_trajectory,
    write_advio_pose_tum,
)
from .advio_models import ADVIO_SEQUENCE_COUNT, AdvioCatalog, AdvioPoseSource, AdvioSceneMetadata, AdvioSequenceConfig
from .advio_replay import wrap_with_advio_video_rotation


class AdvioSequencePaths(BaseData):
    config: AdvioSequenceConfig
    sequence_dir: Path
    video_path: Path
    frame_timestamps_path: Path
    ground_truth_csv_path: Path
    arcore_csv_path: Path
    arkit_csv_path: Path | None = None
    calibration_path: Path
    accelerometer_csv_path: Path | None = None
    gyroscope_csv_path: Path | None = None

    @classmethod
    def resolve(cls, config: AdvioSequenceConfig, scene: AdvioSceneMetadata) -> AdvioSequencePaths:
        sequence_dir = resolve_sequence_dir(config.dataset_root, scene)
        paths = cls(
            config=config,
            sequence_dir=sequence_dir,
            video_path=sequence_dir / "iphone" / "frames.mov",
            frame_timestamps_path=sequence_dir / "iphone" / "frames.csv",
            ground_truth_csv_path=resolve_ground_truth_csv(sequence_dir, scene),
            arcore_csv_path=sequence_dir / "pixel" / "arcore.csv",
            arkit_csv_path=resolve_optional_arkit_csv(sequence_dir, scene),
            calibration_path=resolve_calibration_path(config.dataset_root, scene),
            accelerometer_csv_path=(path if (path := sequence_dir / "iphone" / "accelerometer.csv").exists() else None),
            gyroscope_csv_path=resolve_optional_gyroscope_csv(sequence_dir, scene),
        )
        for path in (
            paths.video_path,
            paths.frame_timestamps_path,
            paths.ground_truth_csv_path,
            paths.arcore_csv_path,
            paths.calibration_path,
        ):
            if not path.exists():
                raise FileNotFoundError(f"Required ADVIO path is missing: {path}")
        return paths


class AdvioOfflineSample(BaseData):
    model_config = {"arbitrary_types_allowed": True}

    sequence_id: int = Field(ge=1, le=ADVIO_SEQUENCE_COUNT)
    sequence_name: str
    paths: AdvioSequencePaths
    frame_timestamps_ns: NDArray[np.int64]
    calibration: AdvioCalibration
    ground_truth: TimedPoseTrajectory
    arcore: TimedPoseTrajectory
    arkit: TimedPoseTrajectory | None = None

    @property
    def duration_s(self) -> float:
        return (
            0.0
            if self.frame_timestamps_ns.size < 2
            else float((self.frame_timestamps_ns[-1] - self.frame_timestamps_ns[0]) / 1e9)
        )


class AdvioSequence(BaseData):
    config: AdvioSequenceConfig
    catalog: AdvioCatalog | None = None

    @property
    def scene(self) -> AdvioSceneMetadata:
        return scene_for_sequence_id(self.catalog or load_advio_catalog(), self.config.sequence_id)

    @property
    def paths(self) -> AdvioSequencePaths:
        return AdvioSequencePaths.resolve(self.config, self.scene)

    def load_offline_sample(self) -> AdvioOfflineSample:
        scene = self.scene
        paths = AdvioSequencePaths.resolve(self.config, scene)
        return AdvioOfflineSample(
            sequence_id=self.config.sequence_id,
            sequence_name=scene.sequence_slug,
            paths=paths,
            frame_timestamps_ns=load_advio_frame_timestamps_ns(paths.frame_timestamps_path),
            calibration=load_advio_calibration(paths.calibration_path),
            ground_truth=load_advio_trajectory(paths.ground_truth_csv_path),
            arcore=load_advio_trajectory(paths.arcore_csv_path),
            arkit=(load_advio_trajectory(paths.arkit_csv_path) if paths.arkit_csv_path is not None else None),
        )

    def to_sequence_manifest(self, *, output_dir: Path | None = None) -> SequenceManifest:
        sample = self.load_offline_sample()
        evaluation_dir = sample.paths.sequence_dir / "evaluation" if output_dir is None else output_dir
        evaluation_dir.mkdir(parents=True, exist_ok=True)

        reference_tum_path = evaluation_dir / "ground_truth.tum"
        if not reference_tum_path.exists():
            self.write_ground_truth_tum(reference_tum_path)

        arcore_tum_path = evaluation_dir / "arcore.tum"
        if not arcore_tum_path.exists():
            self.write_arcore_tum(arcore_tum_path)

        return SequenceManifest(
            sequence_id=sample.sequence_name,
            video_path=sample.paths.video_path,
            timestamps_path=sample.paths.frame_timestamps_path,
            intrinsics_path=sample.paths.calibration_path,
            reference_tum_path=reference_tum_path,
            arcore_tum_path=arcore_tum_path,
        )

    def open_stream(
        self,
        *,
        pose_source: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH,
        stride: int = 1,
        loop: bool = True,
        replay_mode: Cv2ReplayMode = Cv2ReplayMode.REALTIME,
        respect_video_rotation: bool = False,
    ) -> VideoPacketStream:
        scene = self.scene
        sequence_dir = resolve_sequence_dir(self.config.dataset_root, scene)
        video_path = sequence_dir / "iphone" / "frames.mov"
        frame_timestamps_path = sequence_dir / "iphone" / "frames.csv"
        calibration_path = resolve_calibration_path(self.config.dataset_root, scene)
        for path in (video_path, frame_timestamps_path, calibration_path):
            if not path.exists():
                raise FileNotFoundError(f"Required ADVIO path is missing: {path}")
        frame_timestamps_ns = load_advio_frame_timestamps_ns(frame_timestamps_path)
        calibration = load_advio_calibration(calibration_path)
        poses_by_frame = _poses_for_frame_timestamps(
            frame_timestamps_ns,
            _load_stream_trajectory(
                sequence_dir=sequence_dir,
                scene=scene,
                pose_source=pose_source,
            ),
        )
        stream = Cv2FrameProducer(
            Cv2ProducerConfig(
                video_path=video_path,
                frame_timestamps_ns=frame_timestamps_ns.tolist(),
                stride=stride,
                loop=loop,
                replay_mode=replay_mode,
                intrinsics=calibration.intrinsics,
                poses_by_frame=poses_by_frame,
                static_metadata={
                    "dataset": "ADVIO",
                    "sequence_id": scene.sequence_id,
                    "sequence_name": scene.sequence_slug,
                    "pose_source": pose_source.value,
                },
            )
        )
        return wrap_with_advio_video_rotation(stream, video_path=video_path) if respect_video_rotation else stream

    def write_ground_truth_tum(self, target_path: Path) -> Path:
        return write_advio_pose_tum(self.paths.ground_truth_csv_path, target_path)

    def write_arcore_tum(self, target_path: Path) -> Path:
        return write_advio_pose_tum(self.paths.arcore_csv_path, target_path)

    def write_arkit_tum(self, target_path: Path) -> Path:
        if (arkit_path := self.paths.arkit_csv_path) is None:
            raise FileNotFoundError(f"Sequence {self.scene.sequence_slug} does not include an ARKit baseline CSV.")
        return write_advio_pose_tum(arkit_path, target_path)


def load_advio_sequence(config: AdvioSequenceConfig) -> AdvioOfflineSample:
    return AdvioSequence(config=config).load_offline_sample()


def list_advio_sequence_ids(dataset_root: Path) -> list[int]:
    return list_local_sequence_ids(dataset_root)


def _trajectory_for_pose_source(
    sample: AdvioOfflineSample,
    pose_source: AdvioPoseSource,
) -> TimedPoseTrajectory | None:
    return {
        AdvioPoseSource.GROUND_TRUTH: sample.ground_truth,
        AdvioPoseSource.ARCORE: sample.arcore,
        AdvioPoseSource.ARKIT: sample.arkit,
        AdvioPoseSource.NONE: None,
    }[pose_source]


def _load_stream_trajectory(
    *,
    sequence_dir: Path,
    scene: AdvioSceneMetadata,
    pose_source: AdvioPoseSource,
) -> TimedPoseTrajectory | None:
    match pose_source:
        case AdvioPoseSource.GROUND_TRUTH:
            return load_advio_trajectory(resolve_ground_truth_csv(sequence_dir, scene))
        case AdvioPoseSource.ARCORE:
            arcore_path = sequence_dir / "pixel" / "arcore.csv"
            if not arcore_path.exists():
                raise FileNotFoundError(f"Required ADVIO pose CSV is missing: {arcore_path}")
            return load_advio_trajectory(arcore_path)
        case AdvioPoseSource.ARKIT:
            arkit_path = resolve_optional_arkit_csv(sequence_dir, scene)
            if arkit_path is None:
                raise FileNotFoundError(f"Sequence {scene.sequence_slug} does not include an ARKit baseline CSV.")
            return load_advio_trajectory(arkit_path)
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
