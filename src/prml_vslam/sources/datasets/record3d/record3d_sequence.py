"""Record3D `.r3d` sequence owner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

from prml_vslam.interfaces import (
    OBSERVATION_SEQUENCE_FORMAT,
    ObservationIndexEntry,
    ObservationProvenance,
    ObservationSequenceIndex,
    ObservationSequenceRef,
    write_camera_intrinsics_yaml,
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
from prml_vslam.sources.datasets.normalized_store import load_depth_array
from prml_vslam.sources.replay import ImageSequenceObservationSource, ObservationStream, ReplayMode
from prml_vslam.utils import BaseData
from prml_vslam.utils.geometry import (
    depth_map_to_world_points,
    sample_point_cloud_random,
    write_point_cloud_ply,
    write_tum_trajectory,
)

from . import record3d_layout, record3d_loading
from .record3d_models import Record3DCatalog, Record3DSequenceConfig

if TYPE_CHECKING:
    from prml_vslam.sources.contracts import SequenceManifest

RECORD3D_WORLD_FRAME = "record3d_world"
RECORD3D_SOURCE_ID = "record3d_dataset"
RECORD3D_DEPTH_SCALE_TO_M = 0.001


class Record3DSequencePaths(BaseData):
    """Resolved local paths for one Record3D sequence."""

    config: Record3DSequenceConfig
    archive_path: Path
    cache_dir: Path

    @classmethod
    def resolve(cls, config: Record3DSequenceConfig) -> Record3DSequencePaths:
        archive_path = record3d_layout.archive_path_for_sequence(config.dataset_root, config.sequence_id)
        if not archive_path.exists():
            raise FileNotFoundError(f"Record3D archive is missing: {archive_path}")
        return cls(
            config=config,
            archive_path=archive_path,
            cache_dir=record3d_layout.cache_dir_for_sequence(config.dataset_root, config.sequence_id),
        )


class Record3DSequence(BaseData):
    """Load and materialize one local Record3D `.r3d` archive."""

    config: Record3DSequenceConfig
    catalog: Record3DCatalog | None = None

    @property
    def scene(self):
        return record3d_layout.scene_for_sequence_id(
            self.catalog or record3d_layout.load_record3d_catalog(),
            self.config.dataset_root,
            self.config.sequence_id,
        )

    @property
    def paths(self) -> Record3DSequencePaths:
        return Record3DSequencePaths.resolve(self.config)

    def load_offline_sample(self) -> record3d_loading.Record3DOfflineSample:
        paths = self.paths
        metadata = record3d_loading.read_archive_metadata(paths.archive_path)
        frames = record3d_loading.index_archive_frames(paths.archive_path, metadata)
        rgb_intrinsics = record3d_loading.build_rgb_intrinsics(metadata)
        return record3d_loading.Record3DOfflineSample(
            sequence_id=self.scene.sequence_id,
            sequence_name=self.scene.display_name,
            archive_path=paths.archive_path,
            metadata=metadata,
            frames=frames,
            rgb_intrinsics=rgb_intrinsics,
            depth_intrinsics=record3d_loading.build_depth_intrinsics(rgb_intrinsics, metadata),
            timestamps_ns=record3d_loading.timestamps_ns_from_metadata(metadata),
            poses_world_camera=record3d_loading.poses_from_metadata(
                metadata,
                pose_frame_mode=self.config.materialization.pose_frame_mode,
            ),
        )

    def to_sequence_manifest(
        self,
        *,
        output_dir: Path | None = None,
        frame_selection: FrameSelectionConfig | None = None,
    ) -> SequenceManifest:
        from prml_vslam.sources.contracts import SequenceManifest

        output = self.paths.cache_dir / "manifest" if output_dir is None else output_dir
        sample = self.load_offline_sample()
        stride = (frame_selection or FrameSelectionConfig()).stride_for_timestamps_ns(sample.timestamps_ns)
        rgb_dir = output / "rgb"
        rgb_dir.mkdir(parents=True, exist_ok=True)
        selected_timestamps: list[int] = []
        for written_index, frame in enumerate(sample.frames[::stride]):
            rgb = record3d_loading.decode_rgb_frame(sample.archive_path, frame)
            target_path = rgb_dir / f"{written_index:06d}.png"
            cv2.imwrite(str(target_path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
            selected_timestamps.append(sample.timestamps_ns[frame.index])
        timestamps_path = record3d_loading.write_timestamps_json(selected_timestamps, output / "timestamps.json")
        intrinsics_path = write_camera_intrinsics_yaml(sample.rgb_intrinsics, output / "intrinsics.yaml")
        return SequenceManifest(
            sequence_id=sample.sequence_id,
            dataset_id=DatasetId.RECORD3D,
            rgb_dir=rgb_dir.resolve(),
            timestamps_path=timestamps_path,
            intrinsics_path=intrinsics_path,
        )

    def to_benchmark_inputs(
        self,
        *,
        output_dir: Path | None = None,
        frame_selection: FrameSelectionConfig | None = None,
    ) -> PreparedBenchmarkInputs:
        output = self.paths.cache_dir / "evaluation" if output_dir is None else output_dir
        sample = self.load_offline_sample()
        stride = (frame_selection or FrameSelectionConfig()).stride_for_timestamps_ns(sample.timestamps_ns)
        selected_frames = list(sample.frames[::stride])
        output.mkdir(parents=True, exist_ok=True)
        trajectory_path = write_tum_trajectory(
            output / "record3d_arkit.tum",
            sample.poses_world_camera,
            [timestamp_ns / 1e9 for timestamp_ns in sample.timestamps_ns],
        )
        trajectory_metadata_path = _write_json(
            output / "record3d_arkit.metadata.json",
            {
                "dataset_id": DatasetId.RECORD3D.value,
                "source_id": RECORD3D_SOURCE_ID,
                "sequence_id": sample.sequence_id,
                "pose_source": ReferenceSource.ARKIT.value,
                "pose_frame_mode": self.config.materialization.pose_frame_mode.value,
                "target_frame": RECORD3D_WORLD_FRAME,
                "native_frame": RECORD3D_WORLD_FRAME,
            },
        )
        observation_sequence = self._prepare_observation_sequence(
            sample=sample,
            selected_frames=selected_frames,
            output_dir=output / "observations",
        )
        reference_cloud = self._prepare_reference_cloud(
            sample=sample,
            selected_frames=selected_frames,
            output_dir=output / "reference",
        )
        return PreparedBenchmarkInputs(
            reference_trajectories=[
                ReferenceTrajectoryRef(
                    source=ReferenceSource.ARKIT,
                    path=trajectory_path,
                    target_frame=RECORD3D_WORLD_FRAME,
                    native_frame=RECORD3D_WORLD_FRAME,
                    coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
                    metadata_path=trajectory_metadata_path,
                )
            ],
            reference_clouds=[reference_cloud],
            observation_sequences=[observation_sequence],
        )

    def open_stream(
        self,
        *,
        stride: int = 1,
        loop: bool = True,
        replay_mode: ReplayMode = ReplayMode.REALTIME,
        include_depth: bool = True,
    ) -> ObservationStream:
        sample = self.load_offline_sample()
        sequence_ref = self._prepare_observation_sequence(
            sample=sample,
            selected_frames=list(sample.frames),
            output_dir=self.paths.cache_dir / "preview" / "observations",
        )
        index = ObservationSequenceIndex.model_validate_json(sequence_ref.index_path.read_text(encoding="utf-8"))
        return ImageSequenceObservationSource(
            sequence_dir=sequence_ref.payload_root,
            rows=index.rows,
            stride=stride,
            loop=loop,
            replay_mode=replay_mode,
            include_depth=include_depth,
            depth_loader=load_depth_array,
        )

    def _prepare_observation_sequence(
        self,
        *,
        sample: record3d_loading.Record3DOfflineSample,
        selected_frames: list[record3d_loading.Record3DArchiveFrame],
        output_dir: Path,
    ) -> ObservationSequenceRef:
        rgb_dir = output_dir / "rgb"
        depth_dir = output_dir / "depth"
        rgb_dir.mkdir(parents=True, exist_ok=True)
        depth_dir.mkdir(parents=True, exist_ok=True)
        rows: list[ObservationIndexEntry] = []
        for seq, frame in enumerate(selected_frames):
            rgb = record3d_loading.resize_rgb_to_depth(
                record3d_loading.decode_rgb_frame(sample.archive_path, frame), sample.metadata
            )
            depth_m = record3d_loading.decode_depth_frame_m(
                sample.archive_path,
                frame,
                sample.metadata,
                depth_unit_scale=self.config.materialization.depth_unit_scale,
            )
            rgb_path = rgb_dir / f"{seq:06d}.png"
            depth_path = depth_dir / f"{seq:06d}.png"
            cv2.imwrite(str(rgb_path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
            _write_depth_png(depth_path, depth_m)
            rows.append(
                ObservationIndexEntry(
                    seq=seq,
                    timestamp_ns=sample.timestamps_ns[frame.index],
                    rgb_path=rgb_path.relative_to(output_dir),
                    depth_path=depth_path.relative_to(output_dir),
                    depth_scale_to_m=RECORD3D_DEPTH_SCALE_TO_M,
                    T_world_camera=sample.poses_world_camera[frame.index],
                    intrinsics=sample.depth_intrinsics,
                    provenance=ObservationProvenance(
                        source_id=RECORD3D_SOURCE_ID,
                        dataset_id=DatasetId.RECORD3D.value,
                        sequence_id=sample.sequence_id,
                        sequence_name=sample.sequence_name,
                        pose_source=ReferenceSource.ARKIT.value,
                        world_frame=RECORD3D_WORLD_FRAME,
                        raster_space="depth",
                        source_frame_index=frame.index,
                    ),
                )
            )
        index = ObservationSequenceIndex(
            source_id=RECORD3D_SOURCE_ID,
            sequence_id=sample.sequence_id,
            world_frame=RECORD3D_WORLD_FRAME,
            raster_space="depth",
            observation_count=len(rows),
            rows=rows,
        )
        index_path = output_dir / "observations.json"
        index_path.write_text(json.dumps(index.model_dump(mode="json"), indent=2), encoding="utf-8")
        return ObservationSequenceRef(
            format_version=OBSERVATION_SEQUENCE_FORMAT,
            source_id=RECORD3D_SOURCE_ID,
            sequence_id=sample.sequence_id,
            index_path=index_path.resolve(),
            payload_root=output_dir.resolve(),
            observation_count=len(rows),
            world_frame=RECORD3D_WORLD_FRAME,
            raster_space="depth",
        )

    def _prepare_reference_cloud(
        self,
        *,
        sample: record3d_loading.Record3DOfflineSample,
        selected_frames: list[record3d_loading.Record3DArchiveFrame],
        output_dir: Path,
    ) -> ReferenceCloudRef:
        materialization = self.config.materialization
        reference_cloud = self.config.reference_cloud
        output_dir.mkdir(parents=True, exist_ok=True)
        points_batches: list[np.ndarray] = []
        color_batches: list[np.ndarray] = []
        candidate_count = 0
        rejected_count = 0
        contributed_source_frame_indices: list[int] = []
        contributed_timestamps_ns: list[int] = []
        for frame in selected_frames:
            rgb = record3d_loading.resize_rgb_to_depth(
                record3d_loading.decode_rgb_frame(sample.archive_path, frame), sample.metadata
            )
            depth_m = record3d_loading.decode_depth_frame_m(
                sample.archive_path,
                frame,
                sample.metadata,
                depth_unit_scale=materialization.depth_unit_scale,
            )
            confidence = record3d_loading.decode_confidence_frame(sample.archive_path, frame, sample.metadata)
            depth_for_projection = np.nan_to_num(depth_m, nan=0.0, posinf=0.0, neginf=0.0)
            if reference_cloud.min_confidence is not None:
                depth_for_projection = np.where(confidence >= reference_cloud.min_confidence, depth_for_projection, 0.0)
            sampled_depth = depth_for_projection[:: reference_cloud.depth_stride_px, :: reference_cloud.depth_stride_px]
            candidate_count += int(sampled_depth.size)
            rejected_count += int(np.count_nonzero(~np.isfinite(sampled_depth) | (sampled_depth <= 0.0)))
            points_xyz_world, colors_rgb = depth_map_to_world_points(
                depth_for_projection.astype(np.float32, copy=False),
                sample.depth_intrinsics,
                sample.poses_world_camera[frame.index],
                rgb=rgb,
                depth_stride_px=reference_cloud.depth_stride_px,
            )
            if len(points_xyz_world) == 0:
                continue
            points_batches.append(points_xyz_world)
            if colors_rgb is not None:
                color_batches.append(colors_rgb)
            contributed_source_frame_indices.append(frame.index)
            contributed_timestamps_ns.append(sample.timestamps_ns[frame.index])
        points_xyz = np.concatenate(points_batches, axis=0) if points_batches else np.empty((0, 3), dtype=np.float64)
        colors_rgb = np.concatenate(color_batches, axis=0) if color_batches else None
        point_count_before_sampling = int(len(points_xyz))
        points_xyz, colors_rgb = sample_point_cloud_random(
            points_xyz,
            colors_rgb,
            max_points=reference_cloud.max_points,
            seed=reference_cloud.random_seed,
        )
        if len(points_xyz) == 0:
            raise RuntimeError(
                "Record3D reference cloud sampling produced no valid points. "
                "Lower `reference_cloud.min_confidence`, increase the sampling budget, or inspect the depth payload."
            )
        cloud_path = write_point_cloud_ply(
            output_dir / "record3d_lidar_reference.ply", points_xyz, colors_rgb=colors_rgb
        )
        metadata_path = _write_json(
            output_dir / "record3d_lidar_reference.metadata.json",
            {
                "dataset_id": DatasetId.RECORD3D.value,
                "source_id": RECORD3D_SOURCE_ID,
                "sequence_id": sample.sequence_id,
                "source": ReferenceCloudSource.RECORD3D_LIDAR.value,
                "target_frame": RECORD3D_WORLD_FRAME,
                "native_frame": RECORD3D_WORLD_FRAME,
                "coordinate_status": ReferenceCloudCoordinateStatus.ALIGNED.value,
                "pose_frame_mode": materialization.pose_frame_mode.value,
                "selected_frame_count": len(selected_frames),
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
                "candidate_count": candidate_count,
                "rejected_count": rejected_count,
            },
        )
        return ReferenceCloudRef(
            source=ReferenceCloudSource.RECORD3D_LIDAR,
            path=cloud_path,
            metadata_path=metadata_path,
            target_frame=RECORD3D_WORLD_FRAME,
            native_frame=RECORD3D_WORLD_FRAME,
            coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
        )


def _write_depth_png(path: Path, depth_m: np.ndarray) -> None:
    depth = np.asarray(depth_m, dtype=np.float32)
    encoded = np.nan_to_num(depth, nan=0.0, posinf=0.0, neginf=0.0)
    encoded = np.clip(np.rint(np.maximum(encoded, 0.0) / RECORD3D_DEPTH_SCALE_TO_M), 0, np.iinfo(np.uint16).max)
    if not cv2.imwrite(str(path), encoded.astype(np.uint16), [cv2.IMWRITE_PNG_COMPRESSION, 9]):
        raise RuntimeError(f"Failed to write Record3D depth PNG: {path}")


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path.resolve()
