from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from evo.core import sync
from evo.core.trajectory import PoseTrajectory3D
from evo.tools import file_interface
from numpy.typing import NDArray
from pydantic import Field

from prml_vslam.interfaces import CAMERA_RDF_FRAME, ObservationProvenance
from prml_vslam.interfaces.geometry import apply_similarity_to_trajectory, yaw_similarity_align
from prml_vslam.sources.contracts import (
    AdvioManifestAssets,
    AdvioRawPoseRefs,
    PreparedBenchmarkInputs,
    ReferenceCloudCoordinateStatus,
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
from prml_vslam.utils import BaseData, Console, JsonObject

from . import advio_layout, advio_loading
from .advio_frames import (
    advio_basis_metadata,
    transform_advio_trajectory_to_rdf,
    write_advio_rdf_tum,
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

_ADVIO_GT_WORLD_FRAME = "advio_gt_world"
_ADVIO_ALIGN_MAX_DIFF_S = 0.01
_ADVIO_ALIGN_MIN_PAIRS = 3
# RDF gravity (down) axis: ADVIO provider worlds are Apple Y-up -> RDF, so up == -Y.
_ADVIO_RDF_UP_AXIS = np.array([0.0, 1.0, 0.0], dtype=np.float64)


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
                    selected_pose_csv_path=resolve_advio_pose_csv_path(paths=paths, pose_source=selected_pose_source),
                ),
                fixpoints_csv_path=paths.fixpoints_csv_path,
            ),
        )

    def to_benchmark_inputs(
        self,
        *,
        output_dir: Path | None = None,
        frame_selection: FrameSelectionConfig | None = None,
    ) -> PreparedBenchmarkInputs:
        """Materialize benchmark-owned reference trajectories for one sequence."""
        del frame_selection
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
                coordinate_status=ReferenceCloudCoordinateStatus.SOURCE_NATIVE,
                metadata_path=(evaluation_dir / "ground_truth.metadata.json").resolve(),
            )
        ]
        ground_truth_rdf = transform_advio_trajectory_to_rdf(
            advio_loading.load_advio_trajectory(paths.ground_truth_csv_path),
            source=AdvioPoseSource.GROUND_TRUTH,
        )
        if paths.arcore_csv_path.exists():
            _append_optional_reference_trajectory(
                references,
                source=ReferenceSource.ARCORE,
                source_path=paths.arcore_csv_path,
                target_path=evaluation_dir / "arcore.tum",
                ground_truth_rdf=ground_truth_rdf,
            )
        if paths.arkit_csv_path is not None:
            _append_optional_reference_trajectory(
                references,
                source=ReferenceSource.ARKIT,
                source_path=paths.arkit_csv_path,
                target_path=evaluation_dir / "arkit.tum",
                ground_truth_rdf=ground_truth_rdf,
            )
        return PreparedBenchmarkInputs(reference_trajectories=references)

    def open_stream(
        self,
        *,
        dataset_serving: DatasetServingConfig | None = None,
        pose_source: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH,
        stride: int = 1,
        loop: bool = True,
        replay_mode: ReplayMode = ReplayMode.REALTIME,
        normalize_video_orientation: bool = True,
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
            normalize_video_orientation=normalize_video_orientation,
        )


def _ensure_advio_tum(
    source_path: Path,
    target_path: Path,
    *,
    source: AdvioPoseSource,
    target_frame: str,
    native_frame: str,
    trajectory: PoseTrajectory3D | None = None,
    sanitization: JsonObject | None = None,
) -> Path:
    write_advio_rdf_tum(
        trajectory=advio_loading.load_advio_trajectory(source_path) if trajectory is None else trajectory,
        source=source,
        target_path=target_path,
    )
    _write_advio_trajectory_metadata(
        target_path.with_suffix(".metadata.json"),
        source=source,
        target_frame=target_frame,
        native_frame=native_frame,
        coordinate_status=ReferenceCloudCoordinateStatus.SOURCE_NATIVE,
        sanitization=sanitization,
    )
    return target_path.resolve()


def _append_optional_reference_trajectory(
    references: list[ReferenceTrajectoryRef],
    *,
    source: ReferenceSource,
    source_path: Path,
    target_path: Path,
    ground_truth_rdf: PoseTrajectory3D,
) -> None:
    pose_source = _advio_pose_source_from_reference(source)
    native_frame = f"advio_{source.value}_world"
    try:
        source_trajectory, sanitization = _load_sanitized_optional_advio_trajectory(source_path)
        native_path = _ensure_advio_tum(
            source_path,
            target_path,
            source=pose_source,
            target_frame=native_frame,
            native_frame=native_frame,
            trajectory=source_trajectory,
            sanitization=sanitization,
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
    except ValueError as exc:
        _CONSOLE.warning(
            "Skipping invalid optional ADVIO %s trajectory '%s': %s",
            source.value,
            source_path,
            exc,
        )
        return
    _append_aligned_reference_trajectory(
        references,
        source=source,
        pose_source=pose_source,
        native_frame=native_frame,
        source_trajectory=source_trajectory,
        ground_truth_rdf=ground_truth_rdf,
        target_path=target_path,
    )


def _append_aligned_reference_trajectory(
    references: list[ReferenceTrajectoryRef],
    *,
    source: ReferenceSource,
    pose_source: AdvioPoseSource,
    native_frame: str,
    source_trajectory: PoseTrajectory3D,
    ground_truth_rdf: PoseTrajectory3D,
    target_path: Path,
) -> None:
    """Emit a GT-aligned variant of one optional reference so it overlays GT.

    Uses a gravity-locked (yaw + scale + translation) similarity, which cannot
    flip the near-planar ADVIO trajectories upside down the way full Umeyama can.
    Best-effort: failures keep the source-native reference intact.
    """
    reference_rdf = transform_advio_trajectory_to_rdf(source_trajectory, source=pose_source)
    try:
        ground_truth_assoc, reference_assoc = sync.associate_trajectories(
            ground_truth_rdf, reference_rdf, max_diff=_ADVIO_ALIGN_MAX_DIFF_S
        )
    except (ValueError, sync.SyncException) as exc:
        _CONSOLE.warning("Skipping aligned ADVIO %s trajectory: %s", source.value, exc)
        return
    matched_pairs = int(len(ground_truth_assoc.positions_xyz))
    if matched_pairs < _ADVIO_ALIGN_MIN_PAIRS:
        _CONSOLE.warning("Skipping aligned ADVIO %s trajectory: only %d matched GT pairs.", source.value, matched_pairs)
        return
    estimate_xyz = np.asarray(reference_assoc.positions_xyz, dtype=np.float64)
    reference_xyz = np.asarray(ground_truth_assoc.positions_xyz, dtype=np.float64)
    scale, rotation, translation = yaw_similarity_align(
        estimate_xyz, reference_xyz, up_axis=_ADVIO_RDF_UP_AXIS, correct_scale=True
    )
    aligned = apply_similarity_to_trajectory(reference_rdf, scale=scale, rotation=rotation, translation=translation)
    residual = reference_xyz - (scale * (estimate_xyz @ rotation.T) + translation)
    rms_error_m = float(np.sqrt(np.mean(np.sum(residual**2, axis=1))))
    yaw_deg = math.degrees(math.atan2(float(rotation[0, 2]), float(rotation[0, 0])))

    aligned_path = target_path.with_name(f"{target_path.stem}_aligned_to_gt.tum")
    aligned_path.parent.mkdir(parents=True, exist_ok=True)
    file_interface.write_tum_trajectory_file(aligned_path, aligned)
    _write_advio_trajectory_metadata(
        aligned_path.with_suffix(".metadata.json"),
        source=pose_source,
        target_frame=_ADVIO_GT_WORLD_FRAME,
        native_frame=native_frame,
        coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
        alignment={
            "method": "yaw_similarity_umeyama",
            "scale": scale,
            "yaw_deg": yaw_deg,
            "translation": translation.tolist(),
            "matched_pairs": matched_pairs,
            "rms_error_m": rms_error_m,
            "sync_max_diff_s": _ADVIO_ALIGN_MAX_DIFF_S,
        },
    )
    references.append(
        ReferenceTrajectoryRef(
            source=source,
            path=aligned_path.resolve(),
            target_frame=_ADVIO_GT_WORLD_FRAME,
            native_frame=native_frame,
            coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
            metadata_path=aligned_path.with_suffix(".metadata.json").resolve(),
        )
    )


def _write_advio_trajectory_metadata(
    path: Path,
    *,
    source: AdvioPoseSource,
    target_frame: str,
    native_frame: str,
    coordinate_status: ReferenceCloudCoordinateStatus,
    alignment: JsonObject | None = None,
    sanitization: JsonObject | None = None,
) -> None:
    basis_metadata = advio_basis_metadata(source=source, target_frame=target_frame, native_frame=native_frame)
    payload = basis_metadata.model_dump(mode="json") | {
        "dataset": "ADVIO",
        "source": source.value,
        "coordinate_status": coordinate_status.value,
        "alignment": alignment,
        "sanitization": sanitization,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _load_sanitized_optional_advio_trajectory(source_path: Path) -> tuple[PoseTrajectory3D, JsonObject]:
    rows = advio_loading.load_advio_trajectory_rows(source_path)
    input_rows = int(len(rows))
    finite_mask = np.all(np.isfinite(rows), axis=1)
    rows = rows[finite_mask]
    dropped_nonfinite_rows = input_rows - int(len(rows))
    if len(rows) == 0:
        raise ValueError(f"Optional ADVIO trajectory '{source_path}' has no finite pose rows.")

    order = np.argsort(rows[:, 0], kind="stable")
    reordered_timestamps = bool(np.any(order != np.arange(len(rows))))
    rows = rows[order]
    keep_first_timestamp = np.ones(len(rows), dtype=bool)
    keep_first_timestamp[1:] = rows[1:, 0] != rows[:-1, 0]
    dropped_duplicate_timestamps = int(len(rows) - int(np.count_nonzero(keep_first_timestamp)))
    rows = rows[keep_first_timestamp]

    quaternion_norms = np.linalg.norm(rows[:, 4:8], axis=1)
    valid_quaternion_mask = np.isfinite(quaternion_norms) & (quaternion_norms > 0.0)
    dropped_invalid_quaternion_rows = int(len(rows) - int(np.count_nonzero(valid_quaternion_mask)))
    rows = rows[valid_quaternion_mask]
    quaternion_norms = quaternion_norms[valid_quaternion_mask]
    if len(rows) == 0:
        raise ValueError(f"Optional ADVIO trajectory '{source_path}' has no valid orientation rows.")
    max_quaternion_norm_error = float(np.max(np.abs(quaternion_norms - 1.0)))
    normalized_quaternion_rows = int(np.count_nonzero(np.abs(quaternion_norms - 1.0) > 1e-9))
    rows = rows.copy()
    rows[:, 4:8] /= quaternion_norms[:, None]

    trajectory = PoseTrajectory3D(
        positions_xyz=rows[:, 1:4].astype(np.float64, copy=True),
        orientations_quat_wxyz=rows[:, 4:8].astype(np.float64, copy=True),
        timestamps=rows[:, 0].astype(np.float64, copy=True),
    )
    valid, details = trajectory.check()
    if not valid:
        raise ValueError(f"Invalid sanitized optional ADVIO trajectory '{source_path}': {details}")
    return trajectory, {
        "input_rows": input_rows,
        "output_rows": int(len(rows)),
        "dropped_nonfinite_rows": dropped_nonfinite_rows,
        "dropped_duplicate_timestamps": dropped_duplicate_timestamps,
        "dropped_invalid_quaternion_rows": dropped_invalid_quaternion_rows,
        "reordered_timestamps": reordered_timestamps,
        "normalized_quaternion_rows": normalized_quaternion_rows,
        "max_quaternion_norm_error": max_quaternion_norm_error,
    }


def _advio_pose_source_from_reference(source: ReferenceSource) -> AdvioPoseSource:
    return {
        ReferenceSource.GROUND_TRUTH: AdvioPoseSource.GROUND_TRUTH,
        ReferenceSource.ARCORE: AdvioPoseSource.ARCORE,
        ReferenceSource.ARKIT: AdvioPoseSource.ARKIT,
    }[source]
