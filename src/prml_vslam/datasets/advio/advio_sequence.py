from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from numpy.typing import NDArray
from pydantic import Field

from prml_vslam.benchmark import (
    ReferenceCloudCoordinateStatus,
    ReferenceCloudSource,
    ReferenceSource,
)
from prml_vslam.datasets.contracts import (
    AdvioPoseSource,
    DatasetId,
    DatasetServingConfig,
    FrameSelectionConfig,
    selected_advio_pose_source,
)
from prml_vslam.interfaces import FramePacketProvenance
from prml_vslam.interfaces.ingest import (
    AdvioManifestAssets,
    AdvioRawPoseRefs,
    PreparedBenchmarkInputs,
    ReferencePointCloudSequenceRef,
    ReferenceTrajectoryRef,
)
from prml_vslam.io import Cv2ReplayMode
from prml_vslam.io.cv2_producer import Cv2FramePayload, Cv2FrameProducer, Cv2ProducerConfig
from prml_vslam.protocols import FramePacketStream
from prml_vslam.utils import BaseData, Console

from . import advio_layout, advio_loading
from .advio_geometry import (
    build_advio_tango_reference_clouds,
    load_tango_point_cloud_index,
    load_tango_point_cloud_payload,
)
from .advio_models import (
    ADVIO_SEQUENCE_COUNT,
    AdvioCatalog,
    AdvioSceneMetadata,
    AdvioSequenceConfig,
)
from .advio_replay_adapter import (
    _poses_for_frame_timestamps,
    _RotatedVideoStream,
    load_advio_served_trajectory,
    read_advio_video_rotation_degrees,
    resolve_advio_pose_csv_path,
)

if TYPE_CHECKING:
    from prml_vslam.interfaces.ingest import SequenceManifest

_CONSOLE = Console(__name__).child("AdvioSequence")


class AdvioSequencePaths(BaseData):
    config: AdvioSequenceConfig
    sequence_dir: Path
    video_path: Path
    frame_timestamps_path: Path
    ground_truth_csv_path: Path
    fixpoints_csv_path: Path | None = None
    arcore_csv_path: Path
    arkit_csv_path: Path | None = None
    calibration_path: Path
    tango_raw_csv_path: Path | None = None
    tango_area_learning_csv_path: Path | None = None
    tango_point_cloud_index_path: Path | None = None
    tango_dir: Path | None = None
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
            fixpoints_csv_path=advio_layout.resolve_optional_fixpoints_csv(sequence_dir, scene),
            arcore_csv_path=sequence_dir / "pixel" / "arcore.csv",
            arkit_csv_path=advio_layout.resolve_optional_arkit_csv(sequence_dir, scene),
            calibration_path=advio_layout.resolve_calibration_path(config.dataset_root, scene),
            tango_raw_csv_path=(path if (path := sequence_dir / "tango" / "raw.csv").exists() else None),
            tango_area_learning_csv_path=(
                path if (path := sequence_dir / "tango" / "area-learning.csv").exists() else None
            ),
            tango_point_cloud_index_path=(
                path if (path := sequence_dir / "tango" / "point-cloud.csv").exists() else None
            ),
            tango_dir=(path if (path := sequence_dir / "tango").exists() else None),
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
    ground_truth: PoseTrajectory3D
    arcore: PoseTrajectory3D
    arkit: PoseTrajectory3D | None = None

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

    @classmethod
    def setup_target(cls, config: AdvioSequenceConfig, **kwargs: object) -> AdvioSequence:
        """Build one sequence runtime from its validated config."""
        return cls(config=config, **kwargs)

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

    def to_sequence_manifest(
        self,
        *,
        output_dir: Path | None = None,
        frame_selection: FrameSelectionConfig | None = None,
        dataset_serving: DatasetServingConfig | None = None,
    ) -> SequenceManifest:
        from prml_vslam.interfaces.ingest import SequenceManifest

        del frame_selection
        paths = self._resolve_paths(require_arcore=False)
        calibration = advio_loading.load_advio_calibration(paths.calibration_path)
        selected_pose_source = selected_advio_pose_source(dataset_serving)
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
        return SequenceManifest(
            sequence_id=self.scene.sequence_slug,
            dataset_id=DatasetId.ADVIO,
            dataset_serving=dataset_serving,
            video_path=paths.video_path,
            timestamps_path=paths.frame_timestamps_path,
            intrinsics_path=paths.calibration_path,
            advio=AdvioManifestAssets(
                calibration_path=paths.calibration_path,
                intrinsics=calibration.intrinsics,
                T_cam_imu=calibration.t_cam_imu,
                pose_refs=AdvioRawPoseRefs(
                    ground_truth_csv_path=paths.ground_truth_csv_path,
                    arcore_csv_path=paths.arcore_csv_path if paths.arcore_csv_path.exists() else None,
                    arkit_csv_path=paths.arkit_csv_path,
                    tango_raw_csv_path=paths.tango_raw_csv_path,
                    tango_area_learning_csv_path=paths.tango_area_learning_csv_path,
                    selected_pose_csv_path=resolve_advio_pose_csv_path(paths=paths, pose_source=selected_pose_source),
                ),
                fixpoints_csv_path=paths.fixpoints_csv_path,
                tango_point_cloud_index_path=paths.tango_point_cloud_index_path,
                tango_payload_root=paths.tango_dir,
            ),
        )

    def to_benchmark_inputs(self, *, output_dir: Path | None = None) -> PreparedBenchmarkInputs:
        """Materialize benchmark-owned reference trajectories for one sequence."""
        paths = self._resolve_paths(require_arcore=False)
        evaluation_dir = paths.sequence_dir / "evaluation" if output_dir is None else output_dir
        evaluation_dir.mkdir(parents=True, exist_ok=True)
        references = [
            ReferenceTrajectoryRef(
                source=ReferenceSource.GROUND_TRUTH,
                path=_ensure_advio_tum(paths.ground_truth_csv_path, evaluation_dir / "ground_truth.tum"),
            )
        ]
        if paths.arcore_csv_path.exists():
            _append_optional_reference_trajectory(
                references,
                source=ReferenceSource.ARCORE,
                source_path=paths.arcore_csv_path,
                target_path=evaluation_dir / "arcore.tum",
            )
        if paths.arkit_csv_path is not None:
            _append_optional_reference_trajectory(
                references,
                source=ReferenceSource.ARKIT,
                source_path=paths.arkit_csv_path,
                target_path=evaluation_dir / "arkit.tum",
            )
        return PreparedBenchmarkInputs(
            reference_trajectories=references,
            reference_clouds=build_advio_tango_reference_clouds(
                sequence_slug=self.scene.sequence_slug,
                ground_truth_csv_path=paths.ground_truth_csv_path,
                tango_raw_csv_path=paths.tango_raw_csv_path,
                tango_area_learning_csv_path=paths.tango_area_learning_csv_path,
                tango_point_cloud_index_path=paths.tango_point_cloud_index_path,
                output_dir=evaluation_dir,
            ),
            reference_point_cloud_sequences=_build_reference_point_cloud_sequences(
                paths=paths,
                sequence_slug=self.scene.sequence_slug,
                evaluation_dir=evaluation_dir,
            ),
        )

    def open_stream(
        self,
        *,
        dataset_serving: DatasetServingConfig | None = None,
        pose_source: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH,
        stride: int = 1,
        loop: bool = True,
        replay_mode: Cv2ReplayMode = Cv2ReplayMode.REALTIME,
        respect_video_rotation: bool = False,
    ) -> FramePacketStream:
        scene = self.scene
        paths = self._resolve_paths(require_arcore=False)
        frame_timestamps_ns = advio_loading.load_advio_frame_timestamps_ns(paths.frame_timestamps_path)
        calibration = advio_loading.load_advio_calibration(paths.calibration_path)
        effective_serving = (
            dataset_serving
            if dataset_serving is not None
            else DatasetServingConfig(dataset_id="advio", pose_source=pose_source)
        )
        stream: FramePacketStream = Cv2FrameProducer(
            Cv2ProducerConfig(
                video_path=paths.video_path,
                frame_timestamps_ns=frame_timestamps_ns.tolist(),
                stride=stride,
                loop=loop,
                replay_mode=replay_mode,
                intrinsics=calibration.intrinsics,
                payload_provider=_build_advio_payload_provider(
                    paths=paths,
                    pose_source=effective_serving.pose_source,
                ),
                poses_by_frame=_poses_for_frame_timestamps(
                    frame_timestamps_ns,
                    load_advio_served_trajectory(
                        paths=paths,
                        scene=scene,
                        dataset_serving=effective_serving,
                    ),
                ),
                base_provenance=FramePacketProvenance(
                    source_id="advio",
                    dataset_id="advio",
                    sequence_id=str(scene.sequence_id),
                    sequence_name=scene.sequence_slug,
                    pose_source=effective_serving.pose_source.value,
                ),
            )
        )
        if not respect_video_rotation:
            return stream
        rotation_degrees = read_advio_video_rotation_degrees(paths.video_path)
        return stream if rotation_degrees == 0 else _RotatedVideoStream(stream, rotation_degrees)


def _ensure_advio_tum(source_path: Path, target_path: Path) -> Path:
    if not target_path.exists():
        advio_loading.write_advio_pose_tum(source_path, target_path)
    return target_path


def _append_optional_reference_trajectory(
    references: list[ReferenceTrajectoryRef],
    *,
    source: ReferenceSource,
    source_path: Path,
    target_path: Path,
) -> None:
    try:
        references.append(
            ReferenceTrajectoryRef(
                source=source,
                path=_ensure_advio_tum(source_path, target_path),
            )
        )
    except ValueError as exc:
        _CONSOLE.warning(
            "Skipping invalid optional ADVIO %s trajectory '%s': %s",
            source.value,
            source_path,
            exc,
        )


def _build_advio_payload_provider(
    *,
    paths: AdvioSequencePaths,
    pose_source: AdvioPoseSource,
):
    if pose_source not in {AdvioPoseSource.TANGO_RAW, AdvioPoseSource.TANGO_AREA_LEARNING}:
        return None
    if paths.tango_point_cloud_index_path is None:
        return None
    index_rows = load_tango_point_cloud_index(paths.tango_point_cloud_index_path)
    if index_rows.size == 0:
        return None

    def provider(_frame_index: int, timestamp_ns: int) -> Cv2FramePayload | None:
        target_timestamp_s = timestamp_ns / 1e9
        nearest_index = int(np.argmin(np.abs(index_rows[:, 0] - target_timestamp_s)))
        if abs(float(index_rows[nearest_index, 0]) - target_timestamp_s) > 0.05:
            return None
        payload_path = _resolve_tango_payload_path(paths, int(index_rows[nearest_index, 1]))
        if payload_path is None:
            return None
        payload = load_tango_point_cloud_payload(payload_path).astype(np.float32, copy=False)
        return Cv2FramePayload(pointmap=payload.reshape(-1, 1, 3))

    return provider


def _resolve_tango_payload_path(paths: AdvioSequencePaths, cloud_index: int) -> Path | None:
    if paths.tango_dir is None:
        return None
    for candidate in (
        paths.tango_dir / f"point-cloud-{cloud_index:05d}.csv",
        paths.tango_dir / f"point-cloud-{cloud_index:03d}.csv",
        paths.tango_dir / f"point-cloud-{cloud_index}.csv",
    ):
        if candidate.exists():
            return candidate
    return None


def _build_reference_point_cloud_sequences(
    *,
    paths: AdvioSequencePaths,
    sequence_slug: str,
    evaluation_dir: Path,
) -> list[ReferencePointCloudSequenceRef]:
    if paths.tango_point_cloud_index_path is None or paths.tango_dir is None:
        return []

    sequences: list[ReferencePointCloudSequenceRef] = []
    for source, trajectory_csv_path, tum_name in (
        (ReferenceCloudSource.TANGO_AREA_LEARNING, paths.tango_area_learning_csv_path, "tango_area_learning.tum"),
        (ReferenceCloudSource.TANGO_RAW, paths.tango_raw_csv_path, "tango_raw.tum"),
    ):
        if trajectory_csv_path is None or not trajectory_csv_path.exists():
            continue
        try:
            trajectory_path = _ensure_advio_tum(trajectory_csv_path, evaluation_dir / tum_name)
        except ValueError as exc:
            _CONSOLE.warning(
                "Skipping invalid optional ADVIO %s point-cloud trajectory '%s': %s",
                source.value,
                trajectory_csv_path,
                exc,
            )
            continue
        native_frame = f"advio_{source.value}_world"
        sequences.append(
            ReferencePointCloudSequenceRef(
                source=source,
                index_path=paths.tango_point_cloud_index_path.resolve(),
                payload_root=paths.tango_dir.resolve(),
                trajectory_path=trajectory_path,
                target_frame=native_frame,
                native_frame=native_frame,
                coordinate_status=ReferenceCloudCoordinateStatus.SOURCE_NATIVE,
            )
        )
    return sequences
