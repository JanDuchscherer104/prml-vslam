from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from prml_vslam.interfaces import FramePacketStream, TimedPoseTrajectory
from prml_vslam.io import Cv2ReplayMode
from prml_vslam.pipeline.contracts import SequenceManifest
from prml_vslam.utils import BaseData

from . import advio_layout, advio_loading
from .advio_models import ADVIO_SEQUENCE_COUNT, AdvioCatalog, AdvioPoseSource, AdvioSceneMetadata, AdvioSequenceConfig
from .advio_replay_adapter import open_advio_stream


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
    def resolve(
        cls,
        config: AdvioSequenceConfig,
        scene: AdvioSceneMetadata,
        *,
        require_arcore: bool = True,
    ) -> AdvioSequencePaths:
        sequence_dir = advio_layout.resolve_sequence_dir(config.dataset_root, scene)
        paths = cls(
            config=config,
            sequence_dir=sequence_dir,
            video_path=sequence_dir / "iphone" / "frames.mov",
            frame_timestamps_path=sequence_dir / "iphone" / "frames.csv",
            ground_truth_csv_path=advio_layout.resolve_ground_truth_csv(sequence_dir, scene),
            arcore_csv_path=sequence_dir / "pixel" / "arcore.csv",
            arkit_csv_path=advio_layout.resolve_optional_arkit_csv(sequence_dir, scene),
            calibration_path=advio_layout.resolve_calibration_path(config.dataset_root, scene),
            accelerometer_csv_path=(path if (path := sequence_dir / "iphone" / "accelerometer.csv").exists() else None),
            gyroscope_csv_path=advio_layout.resolve_optional_gyroscope_csv(sequence_dir, scene),
        )
        required_paths = (
            paths.video_path,
            paths.frame_timestamps_path,
            paths.ground_truth_csv_path,
            paths.calibration_path,
        ) + ((paths.arcore_csv_path,) if require_arcore else ())
        for path in required_paths:
            if not path.exists():
                raise FileNotFoundError(f"Required ADVIO path is missing: {path}")
        return paths


class AdvioOfflineSample(BaseData):
    model_config = {"arbitrary_types_allowed": True}

    sequence_id: int = Field(ge=1, le=ADVIO_SEQUENCE_COUNT)
    sequence_name: str
    paths: AdvioSequencePaths
    frame_timestamps_ns: NDArray[np.int64]
    calibration: advio_loading.AdvioCalibration
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

    def _resolve_paths(self, *, require_arcore: bool = True) -> AdvioSequencePaths:
        return AdvioSequencePaths.resolve(self.config, self.scene, require_arcore=require_arcore)

    @property
    def scene(self) -> AdvioSceneMetadata:
        return advio_layout.scene_for_sequence_id(
            self.catalog or advio_layout.load_advio_catalog(), self.config.sequence_id
        )

    @property
    def paths(self) -> AdvioSequencePaths:
        return self._resolve_paths()

    def load_offline_sample(self) -> AdvioOfflineSample:
        paths = self.paths
        return AdvioOfflineSample(
            sequence_id=self.config.sequence_id,
            sequence_name=self.scene.sequence_slug,
            paths=paths,
            frame_timestamps_ns=advio_loading.load_advio_frame_timestamps_ns(paths.frame_timestamps_path),
            calibration=advio_loading.load_advio_calibration(paths.calibration_path),
            ground_truth=advio_loading.load_advio_trajectory(paths.ground_truth_csv_path),
            arcore=advio_loading.load_advio_trajectory(paths.arcore_csv_path),
            arkit=(
                advio_loading.load_advio_trajectory(paths.arkit_csv_path) if paths.arkit_csv_path is not None else None
            ),
        )

    def to_sequence_manifest(self, *, output_dir: Path | None = None) -> SequenceManifest:
        paths = self._resolve_paths(require_arcore=False)
        evaluation_dir = paths.sequence_dir / "evaluation" if output_dir is None else output_dir
        evaluation_dir.mkdir(parents=True, exist_ok=True)
        reference_tum_path = _ensure_tum(self.write_ground_truth_tum, evaluation_dir / "ground_truth.tum")
        arcore_tum_path = (
            _ensure_tum(self.write_arcore_tum, evaluation_dir / "arcore.tum")
            if paths.arcore_csv_path.exists()
            else None
        )
        return SequenceManifest(
            sequence_id=self.scene.sequence_slug,
            video_path=paths.video_path,
            timestamps_path=paths.frame_timestamps_path,
            intrinsics_path=paths.calibration_path,
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
    ) -> FramePacketStream:
        return open_advio_stream(
            self,
            pose_source=pose_source,
            stride=stride,
            loop=loop,
            replay_mode=replay_mode,
            respect_video_rotation=respect_video_rotation,
        )

    def write_ground_truth_tum(self, target_path: Path) -> Path:
        return advio_loading.write_advio_pose_tum(
            self._resolve_paths(require_arcore=False).ground_truth_csv_path, target_path
        )

    def write_arcore_tum(self, target_path: Path) -> Path:
        return advio_loading.write_advio_pose_tum(
            self._resolve_paths(require_arcore=False).arcore_csv_path, target_path
        )

    def write_arkit_tum(self, target_path: Path) -> Path:
        if (arkit_path := self._resolve_paths(require_arcore=False).arkit_csv_path) is None:
            raise FileNotFoundError(f"Sequence {self.scene.sequence_slug} does not include an ARKit baseline CSV.")
        return advio_loading.write_advio_pose_tum(arkit_path, target_path)


def load_advio_sequence(config: AdvioSequenceConfig) -> AdvioOfflineSample:
    return AdvioSequence(config=config).load_offline_sample()


def list_advio_sequence_ids(dataset_root: Path) -> list[int]:
    return advio_layout.list_local_sequence_ids(dataset_root)


def _ensure_tum(write_tum: Callable[[Path], Path], target_path: Path) -> Path:
    if not target_path.exists():
        write_tum(target_path)
    return target_path
