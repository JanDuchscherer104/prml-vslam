from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from evo.tools import file_interface
from numpy.typing import NDArray
from pydantic import Field

from prml_vslam.interfaces import CAMERA_RDF_FRAME, ObservationProvenance
from prml_vslam.sources.contracts import (
    AdvioManifestAssets,
    AdvioRawPoseRefs,
    PreparedBenchmarkInputs,
    ReferenceCloudCoordinateStatus,
    ReferenceCloudSource,
    ReferencePointCloudSequenceRef,
    ReferenceSource,
    ReferenceTrajectoryRef,
    SequenceManifest,
)
from prml_vslam.sources.datasets.contracts import (
    AdvioPoseSource,
    DatasetId,
    DatasetServingConfig,
    FrameSelectionConfig,
    selected_advio_pose_source,
)
from prml_vslam.sources.replay import ObservationStream, PyAvVideoObservationSource, ReplayMode
from prml_vslam.utils import BaseData, Console

from . import advio_layout, advio_loading
from .advio_frames import (
    advio_basis_metadata,
    transform_advio_trajectory_to_rdf,
    write_advio_rdf_tum,
)
from .advio_geometry import (
    build_advio_tango_reference_clouds,
    fit_planar_rigid_alignment,
    transform_trajectory_with_alignment,
)
from .advio_models import (
    ADVIO_SEQUENCE_COUNT,
    AdvioCatalog,
    AdvioSceneMetadata,
    AdvioSequenceConfig,
)
from .advio_replay_adapter import (
    _poses_for_frame_timestamps,
    advio_pose_frames,
    load_advio_served_trajectory,
    resolve_advio_pose_csv_path,
)

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

    def to_benchmark_inputs(
        self,
        *,
        output_dir: Path | None = None,
        tango_reference_point_stride: int = 1,
    ) -> PreparedBenchmarkInputs:
        """Materialize benchmark-owned reference trajectories for one sequence."""
        paths = self._resolve_paths(require_arcore=False)
        evaluation_dir = paths.sequence_dir / "evaluation" if output_dir is None else output_dir
        evaluation_dir.mkdir(parents=True, exist_ok=True)
        references = [
            ReferenceTrajectoryRef(
                source=ReferenceSource.GROUND_TRUTH,
                path=_ensure_advio_tum(
                    paths.ground_truth_csv_path,
                    evaluation_dir / "ground_truth.tum",
                    source=AdvioPoseSource.GROUND_TRUTH,
                    target_frame="advio_gt_world",
                    native_frame="advio_gt_world",
                ),
                target_frame="advio_gt_world",
                native_frame="advio_gt_world",
                coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
                metadata_path=(evaluation_dir / "ground_truth.metadata.json").resolve(),
            )
        ]
        if paths.arcore_csv_path.exists():
            _append_optional_reference_trajectory(
                references,
                source=ReferenceSource.ARCORE,
                source_path=paths.arcore_csv_path,
                target_path=evaluation_dir / "arcore.tum",
                aligned_target_path=evaluation_dir / "arcore_aligned_to_gt.tum",
                ground_truth_path=paths.ground_truth_csv_path,
            )
        if paths.arkit_csv_path is not None:
            _append_optional_reference_trajectory(
                references,
                source=ReferenceSource.ARKIT,
                source_path=paths.arkit_csv_path,
                target_path=evaluation_dir / "arkit.tum",
                aligned_target_path=evaluation_dir / "arkit_aligned_to_gt.tum",
                ground_truth_path=paths.ground_truth_csv_path,
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
                point_stride=tango_reference_point_stride,
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
        replay_mode: ReplayMode = ReplayMode.REALTIME,
        respect_video_rotation: bool = False,
    ) -> ObservationStream:
        scene = self.scene
        paths = self._resolve_paths(require_arcore=False)
        frame_timestamps_ns = advio_loading.load_advio_frame_timestamps_ns(paths.frame_timestamps_path)
        calibration = advio_loading.load_advio_calibration(paths.calibration_path)
        effective_serving = (
            dataset_serving
            if dataset_serving is not None
            else DatasetServingConfig(dataset_id="advio", pose_source=pose_source)
        )
        pose_target_frame, _native_pose_source_frame = advio_pose_frames(
            pose_source=effective_serving.pose_source,
            pose_frame_mode=effective_serving.pose_frame_mode,
        )
        return PyAvVideoObservationSource(
            video_path=paths.video_path,
            frame_timestamps_ns=frame_timestamps_ns.tolist(),
            stride=stride,
            loop=loop,
            replay_mode=replay_mode,
            intrinsics=calibration.intrinsics,
            poses_by_frame=_poses_for_frame_timestamps(
                frame_timestamps_ns,
                load_advio_served_trajectory(
                    paths=paths,
                    scene=scene,
                    dataset_serving=effective_serving,
                ),
                target_frame=pose_target_frame,
                source_frame=CAMERA_RDF_FRAME,
            ),
            base_provenance=ObservationProvenance(
                source_id="advio",
                dataset_id="advio",
                sequence_id=str(scene.sequence_id),
                sequence_name=scene.sequence_slug,
                pose_source=effective_serving.pose_source.value,
            ),
            apply_video_rotation=respect_video_rotation,
        )


def _ensure_advio_tum(
    source_path: Path,
    target_path: Path,
    *,
    source: AdvioPoseSource,
    target_frame: str,
    native_frame: str,
) -> Path:
    write_advio_rdf_tum(
        trajectory=advio_loading.load_advio_trajectory(source_path),
        source=source,
        target_path=target_path,
    )
    _write_advio_trajectory_metadata(
        target_path.with_suffix(".metadata.json"),
        source=source,
        target_frame=target_frame,
        native_frame=native_frame,
        coordinate_status=(
            ReferenceCloudCoordinateStatus.ALIGNED
            if target_frame == "advio_gt_world"
            else ReferenceCloudCoordinateStatus.SOURCE_NATIVE
        ),
    )
    return target_path.resolve()


def _append_optional_reference_trajectory(
    references: list[ReferenceTrajectoryRef],
    *,
    source: ReferenceSource,
    source_path: Path,
    target_path: Path,
    aligned_target_path: Path,
    ground_truth_path: Path,
) -> None:
    pose_source = _advio_pose_source_from_reference(source)
    native_frame = f"advio_{source.value}_world"
    try:
        native_path = _ensure_advio_tum(
            source_path,
            target_path,
            source=pose_source,
            target_frame=native_frame,
            native_frame=native_frame,
        )
        references.append(
            ReferenceTrajectoryRef(
                source=source,
                path=native_path,
                target_frame=native_frame,
                native_frame=native_frame,
                coordinate_status=ReferenceCloudCoordinateStatus.SOURCE_NATIVE,
                metadata_path=native_path.with_suffix(".metadata.json").resolve(),
            )
        )
        aligned_path = _ensure_aligned_advio_tum(
            source_path=source_path,
            ground_truth_path=ground_truth_path,
            target_path=aligned_target_path,
            source=pose_source,
            native_frame=native_frame,
        )
        references.append(
            ReferenceTrajectoryRef(
                source=source,
                path=aligned_path,
                target_frame="advio_gt_world",
                native_frame=native_frame,
                coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
                metadata_path=aligned_path.with_suffix(".metadata.json").resolve(),
            )
        )
    except ValueError as exc:
        _CONSOLE.warning(
            "Skipping invalid optional ADVIO %s trajectory '%s': %s",
            source.value,
            source_path,
            exc,
        )


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
    ):
        if trajectory_csv_path is None or not trajectory_csv_path.exists():
            continue
        try:
            pose_source = AdvioPoseSource(source.value)
            native_frame = f"advio_{source.value}_world"
            trajectory_path = _ensure_advio_tum(
                trajectory_csv_path,
                evaluation_dir / tum_name,
                source=pose_source,
                target_frame=native_frame,
                native_frame=native_frame,
            )
        except ValueError as exc:
            _CONSOLE.warning(
                "Skipping invalid optional ADVIO %s point-cloud trajectory '%s': %s",
                source.value,
                trajectory_csv_path,
                exc,
            )
            continue
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
        try:
            aligned_trajectory_path = _ensure_aligned_advio_tum(
                source_path=trajectory_csv_path,
                ground_truth_path=paths.ground_truth_csv_path,
                target_path=evaluation_dir / f"{source.value}_aligned_to_gt.tum",
                source=pose_source,
                native_frame=native_frame,
            )
        except ValueError:
            continue
        sequences.append(
            ReferencePointCloudSequenceRef(
                source=source,
                index_path=paths.tango_point_cloud_index_path.resolve(),
                payload_root=paths.tango_dir.resolve(),
                trajectory_path=aligned_trajectory_path,
                target_frame="advio_gt_world",
                native_frame=native_frame,
                coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
            )
        )
    return sequences


def _ensure_aligned_advio_tum(
    *,
    source_path: Path,
    ground_truth_path: Path,
    target_path: Path,
    source: AdvioPoseSource,
    native_frame: str,
) -> Path:
    source_rdf_trajectory = transform_advio_trajectory_to_rdf(
        advio_loading.load_advio_trajectory(source_path),
        source=source,
    )
    ground_truth_rdf_trajectory = transform_advio_trajectory_to_rdf(
        advio_loading.load_advio_trajectory(ground_truth_path),
        source=AdvioPoseSource.GROUND_TRUTH,
    )
    alignment = fit_planar_rigid_alignment(
        source_trajectory=source_rdf_trajectory,
        target_trajectory=ground_truth_rdf_trajectory,
        source_frame=native_frame,
        target_frame="advio_gt_world",
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    file_interface.write_tum_trajectory_file(
        target_path,
        transform_trajectory_with_alignment(source_rdf_trajectory, alignment),
    )
    _write_advio_trajectory_metadata(
        target_path.with_suffix(".metadata.json"),
        source=source,
        target_frame="advio_gt_world",
        native_frame=native_frame,
        coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
        alignment=alignment.model_dump(mode="json"),
    )
    return target_path.resolve()


def _write_advio_trajectory_metadata(
    path: Path,
    *,
    source: AdvioPoseSource,
    target_frame: str,
    native_frame: str,
    coordinate_status: ReferenceCloudCoordinateStatus,
    alignment: dict[str, str | int | float | bool | None | list[float] | list[list[float]]] | None = None,
) -> None:
    basis_metadata = advio_basis_metadata(source=source, target_frame=target_frame, native_frame=native_frame)
    payload = basis_metadata.model_dump(mode="json") | {
        "dataset": "ADVIO",
        "source": source.value,
        "coordinate_status": coordinate_status.value,
        "alignment": alignment,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _advio_pose_source_from_reference(source: ReferenceSource) -> AdvioPoseSource:
    return {
        ReferenceSource.GROUND_TRUTH: AdvioPoseSource.GROUND_TRUTH,
        ReferenceSource.ARCORE: AdvioPoseSource.ARCORE,
        ReferenceSource.ARKIT: AdvioPoseSource.ARKIT,
    }[source]
