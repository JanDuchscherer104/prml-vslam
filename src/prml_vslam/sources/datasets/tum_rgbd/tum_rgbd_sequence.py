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
from prml_vslam.sources.datasets.rgb_preprocessing import (
    preprocess_rgb_for_normalized_store,
    resize_depth_to_rgb_preprocessing,
    scale_intrinsics_for_rgb_preprocessing,
    write_preprocessed_rgb_png,
)
from prml_vslam.sources.observation_sequence import load_observation_sequence_index
from prml_vslam.sources.replay import ObservationStream, ReplayMode
from prml_vslam.utils import BaseData
from prml_vslam.utils.geometry import depth_map_to_world_points, sample_point_cloud_random, write_point_cloud_ply

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
        selected_frames = None
        if frame_selection is not None and output_dir is not None:
            selected_frames = _select_frame_associations(paths, frame_selection)
        intrinsics_path = tum_rgbd_loading.ensure_tum_rgbd_intrinsics_yaml(
            self.scene.sequence_id,
            paths.sequence_dir,
            None if output_dir is None else output_dir / "intrinsics.yaml",
        )
        timestamps_path = paths.rgb_list_path
        if output_dir is not None and selected_frames is not None:
            timestamps_path = output_dir / "timestamps.json"
            timestamps_path.parent.mkdir(parents=True, exist_ok=True)
            timestamps_path.write_text(
                json.dumps(
                    {
                        "timestamps_ns": [
                            int(round(association.rgb_timestamp_s * 1e9)) for _, association in selected_frames
                        ]
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        return SequenceManifest(
            sequence_id=self.scene.sequence_id,
            dataset_id=DatasetId.TUM_RGBD,
            rgb_dir=None if output_dir is not None else paths.sequence_dir / "rgb",
            timestamps_path=timestamps_path,
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
            output_dir=evaluation_dir / "observations",
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
        rgb_dir = output_dir / "rgb"
        depth_dir = output_dir / "depth"
        output_dir.mkdir(parents=True, exist_ok=True)
        rgb_dir.mkdir(parents=True, exist_ok=True)
        depth_dir.mkdir(parents=True, exist_ok=True)
        for source_frame_index, association in selected_frames:
            if association.depth_path is None or association.pose_index is None:
                continue
            seq = len(rows)
            rgb_path = rgb_dir / f"{seq:06d}.png"
            depth_path = depth_dir / f"{seq:06d}.png"
            rgb = _load_rgb_payload(association.rgb_path)
            depth = _load_depth_payload(association.depth_path, preserve_dtype=True)
            preprocessed = preprocess_rgb_for_normalized_store(
                rgb,
                max_width_px=self.config.rgb_max_width_px,
                dimension_multiple=self.config.rgb_dimension_multiple,
            )
            scaled_depth = resize_depth_to_rgb_preprocessing(depth, preprocessed)
            scaled_intrinsics = scale_intrinsics_for_rgb_preprocessing(intrinsics, preprocessed)
            write_preprocessed_rgb_png(rgb_path, preprocessed.rgb)
            if not cv2.imwrite(str(depth_path), scaled_depth, [cv2.IMWRITE_PNG_COMPRESSION, 9]):
                raise RuntimeError(f"Failed to write TUM RGB-D depth PNG: {depth_path}")
            rows.append(
                ObservationIndexEntry(
                    seq=seq,
                    timestamp_ns=int(round(association.rgb_timestamp_s * 1e9)),
                    rgb_path=rgb_path.relative_to(output_dir),
                    depth_path=depth_path.relative_to(output_dir),
                    depth_scale_to_m=TUM_RGBD_DEPTH_SCALE_TO_M,
                    T_world_camera=FrameTransform.from_matrix(
                        np.asarray(trajectory.poses_se3[association.pose_index], dtype=np.float64),
                        target_frame=TUM_RGBD_WORLD_FRAME,
                        source_frame=TUM_RGBD_CAMERA_FRAME,
                    ),
                    intrinsics=scaled_intrinsics,
                    provenance=ObservationProvenance(
                        source_id="tum_rgbd",
                        dataset_id="tum_rgbd",
                        sequence_id=self.scene.sequence_id,
                        sequence_name=self.scene.display_name,
                        pose_source=ReferenceSource.GROUND_TRUTH.value,
                        world_frame=TUM_RGBD_WORLD_FRAME,
                        raster_space="display_downscaled",
                        source_frame_index=source_frame_index,
                        original_width=preprocessed.original_width,
                        original_height=preprocessed.original_height,
                    ),
                )
            )
        if not rows:
            return None
        index = ObservationSequenceIndex(
            source_id="tum_rgbd",
            sequence_id=self.scene.sequence_id,
            world_frame=TUM_RGBD_WORLD_FRAME,
            raster_space="display_downscaled",
            observation_count=len(rows),
            rows=rows,
        )
        (output_dir / "rgb.metadata.json").write_text(
            json.dumps(
                {
                    "raster_space": "display_downscaled",
                    "source_raster_space": "source",
                    "rgb_max_width_px": self.config.rgb_max_width_px,
                    "dimension_multiple": self.config.rgb_dimension_multiple,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        index_path = (output_dir / "observations.json").resolve()
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(json.dumps(index.model_dump(mode="json"), indent=2), encoding="utf-8")
        return ObservationSequenceRef(
            source_id="tum_rgbd",
            sequence_id=self.scene.sequence_id,
            index_path=index_path,
            payload_root=output_dir.resolve(),
            observation_count=len(rows),
            world_frame=TUM_RGBD_WORLD_FRAME,
            raster_space="display_downscaled",
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
        reference_cloud = self.config.reference_cloud
        chunks: list[np.ndarray] = []
        color_chunks: list[np.ndarray] = []
        skipped_method_frame_reasons: dict[str, int] = {}
        contributed_source_frame_indices: list[int] = []
        contributed_timestamps_ns: list[int] = []
        observation_index = load_observation_sequence_index(observation_sequence.index_path)
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
                depth_stride_px=reference_cloud.depth_stride_px,
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
            max_points=reference_cloud.max_points,
            seed=reference_cloud.random_seed,
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
                    "source_frame_indices": contributed_source_frame_indices,
                    "source_timestamps_ns": contributed_timestamps_ns,
                    "depth_stride_px": reference_cloud.depth_stride_px,
                    "min_confidence": reference_cloud.min_confidence,
                    "max_points": reference_cloud.max_points,
                    "random_seed": reference_cloud.random_seed,
                    "point_sampling_policy": (
                        "none" if point_count_before_sampling == len(points_xyz) else "random_without_replacement"
                    ),
                    "point_count_before_sampling": point_count_before_sampling,
                    "point_count_after_sampling": int(len(points_xyz)),
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


def _load_depth_payload(path: Path, *, preserve_dtype: bool = False) -> np.ndarray:
    depth = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if depth is None:
        raise FileNotFoundError(f"Cannot read TUM RGB-D depth payload: {path}")
    if preserve_dtype:
        return np.asarray(depth)
    return np.asarray(depth, dtype=np.float32)
