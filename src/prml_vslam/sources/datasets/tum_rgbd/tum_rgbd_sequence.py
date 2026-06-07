from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
from pydantic import ConfigDict

from prml_vslam.interfaces import (
    FrameTransform,
    ObservationIndexEntry,
    ObservationProvenance,
    ObservationSequenceIndex,
    ObservationSequenceRef,
)
from prml_vslam.sources.contracts import (
    PreparedBenchmarkInputs,
    ReferenceCloudCoordinateStatus,
    ReferenceCloudRef,
    ReferenceCloudSource,
    ReferenceSource,
    ReferenceTrajectoryRef,
)
from prml_vslam.sources.datasets.contracts import DatasetId, FrameSelectionConfig
from prml_vslam.sources.observation_sequence import load_observation_sequence_index
from prml_vslam.sources.replay import ObservationStream, ReplayMode
from prml_vslam.utils import BaseData
from prml_vslam.utils.geometry import (
    depth_map_to_world_points,
    sample_point_cloud_random,
    write_point_cloud_ply,
)

from . import tum_rgbd_layout, tum_rgbd_loading
from .tum_rgbd_loading import TUM_RGBD_CAMERA_FRAME, TUM_RGBD_NATIVE_WORLD_FRAME, TUM_RGBD_WORLD_FRAME
from .tum_rgbd_models import TumRgbdCatalog, TumRgbdPoseSource, TumRgbdSequenceConfig
from .tum_rgbd_replay_adapter import open_tum_rgbd_stream

TUM_RGBD_DEPTH_SCALE_TO_M = 1.0 / 5000.0

if TYPE_CHECKING:
    from prml_vslam.sources.contracts import SequenceManifest


class TumRgbdSequencePaths(BaseData):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    config: TumRgbdSequenceConfig
    sequence_dir: Path
    rgb_list_path: Path
    depth_list_path: Path | None = None
    ground_truth_path: Path

    @classmethod
    def resolve(cls, config: TumRgbdSequenceConfig, *, catalog: TumRgbdCatalog | None = None) -> TumRgbdSequencePaths:
        scene = tum_rgbd_layout.scene_for_sequence_id(
            catalog or tum_rgbd_layout.load_tum_rgbd_catalog(), config.sequence_id
        )
        sequence_dir = tum_rgbd_layout.resolve_sequence_dir(config.dataset_root, scene)
        paths = cls(
            config=config,
            sequence_dir=sequence_dir,
            rgb_list_path=sequence_dir / "rgb.txt",
            depth_list_path=(path if (path := sequence_dir / "depth.txt").exists() else None),
            ground_truth_path=tum_rgbd_loading.resolve_ground_truth_path(sequence_dir),
        )
        for required_path in (paths.rgb_list_path, paths.ground_truth_path):
            if not required_path.exists():
                raise FileNotFoundError(f"Required TUM RGB-D path is missing: {required_path}")
        if not (sequence_dir / "rgb").is_dir():
            raise FileNotFoundError(f"Required TUM RGB-D RGB directory is missing: {sequence_dir / 'rgb'}")
        return paths


class TumRgbdSequence(BaseData):
    config: TumRgbdSequenceConfig
    catalog: TumRgbdCatalog | None = None

    @property
    def scene(self):
        return tum_rgbd_layout.scene_for_sequence_id(
            self.catalog or tum_rgbd_layout.load_tum_rgbd_catalog(),
            self.config.sequence_id,
        )

    @property
    def paths(self) -> TumRgbdSequencePaths:
        return TumRgbdSequencePaths.resolve(self.config, catalog=self.catalog)

    def load_offline_sample(self) -> tum_rgbd_loading.TumRgbdOfflineSample:
        paths = self.paths
        return tum_rgbd_loading.TumRgbdOfflineSample(
            sequence_id=self.scene.sequence_id,
            sequence_name=self.scene.display_name,
            paths=paths,
            associations=tum_rgbd_loading.load_tum_rgbd_associations(paths.sequence_dir),
            intrinsics=tum_rgbd_loading.load_tum_rgbd_intrinsics(self.scene.sequence_id, paths.sequence_dir),
            ground_truth=tum_rgbd_loading.load_tum_rgbd_ground_truth(paths.ground_truth_path),
        )

    def to_sequence_manifest(
        self,
        *,
        output_dir: Path | None = None,
        frame_selection: FrameSelectionConfig | None = None,
    ) -> SequenceManifest:
        from prml_vslam.sources.contracts import SequenceManifest

        paths = self.paths
        if frame_selection is not None and output_dir is not None:
            selected_frames = _select_frame_associations(paths, frame_selection)
            paths = _materialize_sampled_paths(paths, selected_frames, output_dir)
        intrinsics_path = tum_rgbd_loading.ensure_tum_rgbd_intrinsics_yaml(
            self.scene.sequence_id,
            paths.sequence_dir,
            None if output_dir is None else output_dir / "intrinsics.yaml",
        )
        return SequenceManifest(
            sequence_id=self.scene.sequence_id,
            dataset_id=DatasetId.TUM_RGBD,
            rgb_dir=paths.sequence_dir / "rgb",
            timestamps_path=paths.rgb_list_path,
            intrinsics_path=intrinsics_path,
        )

    def to_benchmark_inputs(
        self,
        *,
        output_dir: Path | None = None,
        frame_selection: FrameSelectionConfig | None = None,
    ) -> PreparedBenchmarkInputs:
        paths = self.paths
        evaluation_dir = paths.sequence_dir / "evaluation" if output_dir is None else output_dir
        reference_path = tum_rgbd_loading.ensure_ground_truth_tum(
            paths.sequence_dir, evaluation_dir / "ground_truth.tum"
        )
        selected_frames = _select_frame_associations(paths, frame_selection or FrameSelectionConfig())
        observation_sequence = self._prepare_observation_sequence(
            paths=paths,
            selected_frames=selected_frames,
            output_dir=evaluation_dir,
        )
        reference_cloud = self._prepare_reference_cloud(
            observation_sequence=observation_sequence,
            output_dir=evaluation_dir,
        )
        return PreparedBenchmarkInputs(
            reference_trajectories=[
                ReferenceTrajectoryRef(
                    source=ReferenceSource.GROUND_TRUTH,
                    path=reference_path,
                    target_frame=TUM_RGBD_WORLD_FRAME,
                    native_frame=TUM_RGBD_NATIVE_WORLD_FRAME,
                    coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
                )
            ],
            reference_clouds=[] if reference_cloud is None else [reference_cloud],
            observation_sequences=[] if observation_sequence is None else [observation_sequence],
        )

    def open_stream(
        self,
        *,
        pose_source: TumRgbdPoseSource = TumRgbdPoseSource.GROUND_TRUTH,
        stride: int = 1,
        loop: bool = True,
        replay_mode: ReplayMode = ReplayMode.REALTIME,
        include_depth: bool = True,
    ) -> ObservationStream:
        paths = self.paths
        return open_tum_rgbd_stream(
            self.scene.sequence_id,
            paths.sequence_dir,
            pose_source=pose_source,
            stride=stride,
            loop=loop,
            replay_mode=replay_mode,
            include_depth=include_depth,
        )

    def _prepare_observation_sequence(
        self,
        *,
        paths: TumRgbdSequencePaths,
        selected_frames: list[tuple[int, tum_rgbd_loading.TumRgbdFrameAssociation]],
        output_dir: Path,
    ) -> ObservationSequenceRef | None:
        """Write a durable observation index for reconstruction, if depth exists."""
        trajectory = tum_rgbd_loading.load_tum_rgbd_ground_truth_rdf(paths.ground_truth_path)
        intrinsics = tum_rgbd_loading.load_tum_rgbd_intrinsics(self.scene.sequence_id, paths.sequence_dir)
        rows: list[ObservationIndexEntry] = []
        for source_frame_index, association in selected_frames:
            if association.depth_path is None or association.pose_index is None:
                continue
            rows.append(
                ObservationIndexEntry(
                    seq=len(rows),
                    timestamp_ns=int(round(association.rgb_timestamp_s * 1e9)),
                    rgb_path=_relative_to_sequence_root(association.rgb_path, paths.sequence_dir),
                    depth_path=_relative_to_sequence_root(association.depth_path, paths.sequence_dir),
                    depth_scale_to_m=1.0 / 5000.0,
                    T_world_camera=FrameTransform.from_matrix(
                        np.asarray(trajectory.poses_se3[association.pose_index], dtype=np.float64),
                        target_frame=TUM_RGBD_WORLD_FRAME,
                        source_frame=TUM_RGBD_CAMERA_FRAME,
                    ),
                    intrinsics=intrinsics,
                    provenance=ObservationProvenance(
                        source_id="tum_rgbd",
                        dataset_id="tum_rgbd",
                        sequence_id=self.scene.sequence_id,
                        sequence_name=self.scene.display_name,
                        pose_source=ReferenceSource.GROUND_TRUTH.value,
                        world_frame=TUM_RGBD_WORLD_FRAME,
                        raster_space="source",
                        source_frame_index=source_frame_index,
                    ),
                )
            )
        if not rows:
            return None
        index = ObservationSequenceIndex(
            source_id="tum_rgbd",
            sequence_id=self.scene.sequence_id,
            world_frame=TUM_RGBD_WORLD_FRAME,
            raster_space="source",
            observation_count=len(rows),
            rows=rows,
        )
        index_path = (output_dir / "observations.json").resolve()
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(json.dumps(index.model_dump(mode="json"), indent=2), encoding="utf-8")
        return ObservationSequenceRef(
            source_id="tum_rgbd",
            sequence_id=self.scene.sequence_id,
            index_path=index_path,
            payload_root=paths.sequence_dir.resolve(),
            observation_count=len(rows),
            world_frame=TUM_RGBD_WORLD_FRAME,
            raster_space="source",
        )

    def _prepare_reference_cloud(
        self,
        *,
        observation_sequence: ObservationSequenceRef | None,
        output_dir: Path,
    ) -> ReferenceCloudRef | None:
        """Fuse method-input RGB-D observations into the aligned TUM RGB-D reference cloud."""
        if observation_sequence is None:
            return None
        chunks: list[np.ndarray] = []
        color_chunks: list[np.ndarray] = []
        skipped_method_frame_reasons: dict[str, int] = {}
        contributed_source_frame_indices: list[int] = []
        contributed_timestamps_ns: list[int] = []
        observation_index = load_observation_sequence_index(observation_sequence.index_path)
        reference_cloud_config = self.config.reference_cloud
        for row in observation_index.rows:
            if row.depth_path is None or row.intrinsics is None or row.T_world_camera is None:
                skipped_method_frame_reasons["missing_metric_geometry"] = (
                    skipped_method_frame_reasons.get("missing_metric_geometry", 0) + 1
                )
                continue
            rgb = (
                None
                if row.rgb_path is None
                else _load_rgb_payload(_resolve_payload(row.rgb_path, observation_sequence))
            )
            depth_m = _load_depth_payload(_resolve_payload(row.depth_path, observation_sequence)) * row.depth_scale_to_m
            points_xyz_world, colors_rgb = depth_map_to_world_points(
                depth_m.astype(np.float32, copy=False),
                row.intrinsics,
                row.T_world_camera,
                rgb=rgb,
                depth_stride_px=reference_cloud_config.depth_stride_px,
            )
            if len(points_xyz_world) == 0:
                skipped_method_frame_reasons["no_valid_depth"] = (
                    skipped_method_frame_reasons.get("no_valid_depth", 0) + 1
                )
                continue
            chunks.append(points_xyz_world)
            if colors_rgb is not None:
                color_chunks.append(colors_rgb)
            source_frame_index = row.provenance.source_frame_index
            contributed_source_frame_indices.append(row.seq if source_frame_index is None else source_frame_index)
            contributed_timestamps_ns.append(row.timestamp_ns)

        if not chunks:
            raise ValueError(f"TUM RGB-D sequence '{self.scene.sequence_id}' has no valid depth samples.")

        points_xyz = np.vstack(chunks).astype(np.float64, copy=False)
        colors_rgb = np.vstack(color_chunks).astype(np.uint8, copy=False) if color_chunks else None
        point_count_before_sampling = int(len(points_xyz))
        points_xyz, colors_rgb = sample_point_cloud_random(
            points_xyz,
            colors_rgb,
            max_points=reference_cloud_config.max_points,
            seed=reference_cloud_config.random_seed,
        )
        cloud_path, metadata_path = _reference_cloud_paths(output_dir)
        cloud_path = write_point_cloud_ply(cloud_path, points_xyz, colors_rgb=colors_rgb)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(
            json.dumps(
                {
                    "dataset": "TUM RGB-D",
                    "dataset_id": DatasetId.TUM_RGBD.value,
                    "sequence_id": self.scene.sequence_id,
                    "source": ReferenceCloudSource.TUM_RGBD.value,
                    "coordinate_status": ReferenceCloudCoordinateStatus.ALIGNED.value,
                    "target_frame": TUM_RGBD_WORLD_FRAME,
                    "native_frame": TUM_RGBD_NATIVE_WORLD_FRAME,
                    "camera_frame": TUM_RGBD_CAMERA_FRAME,
                    "payload_pose_semantics": "registered_depth_unprojected_by_ground_truth_pose",
                    "depth_scale_to_m": TUM_RGBD_DEPTH_SCALE_TO_M,
                    "depth_registered_to_rgb": True,
                    "units": "meters",
                    "method_sample_count": observation_sequence.observation_count,
                    "frame_count": len(contributed_source_frame_indices),
                    "sampled_frame_count": len(contributed_source_frame_indices),
                    "contributing_source_frame_indices": contributed_source_frame_indices,
                    "source_frame_indices": contributed_source_frame_indices,
                    "reference_cloud_sampled_frame_indices": contributed_source_frame_indices,
                    "reference_cloud_sampled_timestamps_ns": contributed_timestamps_ns,
                    "depth_stride_px": reference_cloud_config.depth_stride_px,
                    "depth_pixel_stride_px": reference_cloud_config.depth_stride_px,
                    "point_sampling_policy": (
                        "none" if point_count_before_sampling == len(points_xyz) else "random_without_replacement"
                    ),
                    "seed": reference_cloud_config.random_seed,
                    "point_sampling_seed": reference_cloud_config.random_seed,
                    "point_count_before_sampling": point_count_before_sampling,
                    "point_count_after_sampling": int(len(points_xyz)),
                    "point_count": int(len(points_xyz)),
                    "max_points": reference_cloud_config.max_points,
                    "max_reference_points": reference_cloud_config.max_points,
                    "device": "CPU:0",
                    "source_observation_index_path": str(observation_sequence.index_path),
                    "skipped_method_frame_count": sum(skipped_method_frame_reasons.values()),
                    "skipped_method_frame_reasons": skipped_method_frame_reasons,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return ReferenceCloudRef(
            source=ReferenceCloudSource.TUM_RGBD,
            path=cloud_path,
            metadata_path=metadata_path,
            target_frame=TUM_RGBD_WORLD_FRAME,
            native_frame=TUM_RGBD_NATIVE_WORLD_FRAME,
            coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
        )


def _materialize_sampled_paths(
    paths: TumRgbdSequencePaths,
    selected_frames: list[tuple[int, tum_rgbd_loading.TumRgbdFrameAssociation]],
    output_dir: Path,
) -> TumRgbdSequencePaths:
    import shutil

    source_associations = tum_rgbd_loading.load_tum_rgbd_associations(paths.sequence_dir)
    if len(selected_frames) == len(source_associations):
        return paths
    rgb_dir = output_dir / "rgb"
    rgb_dir.mkdir(parents=True, exist_ok=True)
    rows: list[str] = []
    for written_index, (_source_frame_index, association) in enumerate(selected_frames):
        source_path = association.rgb_path
        target_path = rgb_dir / f"{written_index:06d}{source_path.suffix}"
        if not target_path.exists():
            shutil.copy2(source_path, target_path)
        rows.append(f"{association.rgb_timestamp_s:.9f} rgb/{target_path.name}")
    sampled_rgb_list = output_dir / "rgb.txt"
    sampled_rgb_list.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return paths.model_copy(update={"rgb_list_path": sampled_rgb_list, "sequence_dir": output_dir})


def _select_frame_associations(
    paths: TumRgbdSequencePaths,
    frame_selection: FrameSelectionConfig,
) -> list[tuple[int, tum_rgbd_loading.TumRgbdFrameAssociation]]:
    associations = tum_rgbd_loading.load_tum_rgbd_associations(paths.sequence_dir)
    timestamps_ns = [int(round(association.rgb_timestamp_s * 1e9)) for association in associations]
    stride = frame_selection.stride_for_timestamps_ns(timestamps_ns)
    return [
        (association_index, association)
        for association_index, association in enumerate(associations)
        if association_index % stride == 0
    ]


def _reference_cloud_paths(output_dir: Path) -> tuple[Path, Path]:
    reference_dir = output_dir.parent / "reference" if output_dir.name == "benchmark" else output_dir
    return (
        (reference_dir / "reference_cloud.ply").resolve(),
        (reference_dir / "reference_cloud.metadata.json").resolve(),
    )


def _resolve_payload(path: Path, ref: ObservationSequenceRef) -> Path:
    return path if path.is_absolute() else ref.payload_root / path


def _load_rgb_payload(path: Path) -> np.ndarray:
    image_bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise FileNotFoundError(f"Cannot read TUM RGB-D RGB payload: {path}")
    return np.asarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB), dtype=np.uint8)


def _load_depth_payload(path: Path) -> np.ndarray:
    depth = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if depth is None:
        raise FileNotFoundError(f"Cannot read TUM RGB-D depth payload: {path}")
    return np.asarray(depth, dtype=np.float32)


def _relative_to_sequence_root(path: Path, sequence_dir: Path) -> Path:
    try:
        return path.relative_to(sequence_dir)
    except ValueError as exc:
        raise ValueError(f"Expected TUM RGB-D path '{path}' to live under sequence dir '{sequence_dir}'.") from exc
