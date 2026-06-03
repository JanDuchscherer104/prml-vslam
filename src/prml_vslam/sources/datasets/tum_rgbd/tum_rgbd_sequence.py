from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from pydantic import ConfigDict

from prml_vslam.interfaces import (
    CAMERA_RDF_FRAME,
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
from prml_vslam.sources.replay import ObservationStream, ReplayMode
from prml_vslam.utils import BaseData
from prml_vslam.utils.geometry import pointmap_from_depth, transform_points_world_camera, write_point_cloud_ply

from . import tum_rgbd_layout, tum_rgbd_loading
from .tum_rgbd_models import TumRgbdCatalog, TumRgbdPoseSource, TumRgbdSequenceConfig
from .tum_rgbd_replay_adapter import open_tum_rgbd_stream

TUM_RGBD_WORLD_FRAME = "tum_rgbd_mocap_world"
TUM_RGBD_CAMERA_FRAME = CAMERA_RDF_FRAME
TUM_RGBD_REFERENCE_CLOUD_FRAME_STRIDE = 10
TUM_RGBD_REFERENCE_CLOUD_MAX_FRAMES = 20
TUM_RGBD_REFERENCE_CLOUD_DEPTH_STRIDE_PX = 8
TUM_RGBD_REFERENCE_CLOUD_MAX_POINTS = 100_000

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
            paths = _materialize_sampled_paths(paths, frame_selection, output_dir)
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

    def to_benchmark_inputs(self, *, output_dir: Path | None = None) -> PreparedBenchmarkInputs:
        paths = self.paths
        evaluation_dir = paths.sequence_dir / "evaluation" if output_dir is None else output_dir
        reference_path = tum_rgbd_loading.ensure_ground_truth_tum(
            paths.sequence_dir, evaluation_dir / "ground_truth.tum"
        )
        observation_sequence = self._prepare_observation_sequence(paths=paths, output_dir=evaluation_dir)
        reference_cloud = self._prepare_reference_cloud(paths=paths, output_dir=evaluation_dir)
        return PreparedBenchmarkInputs(
            reference_trajectories=[
                ReferenceTrajectoryRef(
                    source=ReferenceSource.GROUND_TRUTH,
                    path=reference_path,
                    target_frame=TUM_RGBD_WORLD_FRAME,
                    native_frame=TUM_RGBD_WORLD_FRAME,
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
        output_dir: Path,
    ) -> ObservationSequenceRef | None:
        """Write a durable observation index for reconstruction, if depth exists."""
        associations = tum_rgbd_loading.load_tum_rgbd_associations(paths.sequence_dir)
        trajectory = tum_rgbd_loading.load_tum_rgbd_ground_truth(paths.ground_truth_path)
        intrinsics = tum_rgbd_loading.load_tum_rgbd_intrinsics(self.scene.sequence_id, paths.sequence_dir)
        rows: list[ObservationIndexEntry] = []
        for source_index, association in enumerate(associations):
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
                        source_frame_index=source_index,
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
        paths: TumRgbdSequencePaths,
        output_dir: Path,
    ) -> ReferenceCloudRef | None:
        """Fuse sampled registered-depth frames into an aligned TUM RGB-D reference cloud."""
        if paths.depth_list_path is None:
            return None

        associations = tum_rgbd_loading.load_tum_rgbd_associations(paths.sequence_dir)
        depth_associations = [
            association
            for association in associations
            if association.depth_path is not None and association.pose_index is not None
        ]
        if not depth_associations:
            raise ValueError(
                f"TUM RGB-D sequence '{self.scene.sequence_id}' has depth rows but no RGB/depth/pose associations."
            )

        trajectory = tum_rgbd_loading.load_tum_rgbd_ground_truth(paths.ground_truth_path)
        intrinsics = tum_rgbd_loading.load_tum_rgbd_intrinsics(self.scene.sequence_id, paths.sequence_dir)
        chunks: list[np.ndarray] = []
        point_count = 0
        sampled_frame_count = 0
        for association in depth_associations[::TUM_RGBD_REFERENCE_CLOUD_FRAME_STRIDE]:
            if (
                sampled_frame_count >= TUM_RGBD_REFERENCE_CLOUD_MAX_FRAMES
                or point_count >= TUM_RGBD_REFERENCE_CLOUD_MAX_POINTS
            ):
                break

            depth_path = association.depth_path
            pose_index = association.pose_index
            if depth_path is None or pose_index is None:
                continue

            depth_map_m = tum_rgbd_loading.load_depth_image_m(depth_path)
            depth_map_m = np.where(np.isfinite(depth_map_m), depth_map_m, 0.0).astype(np.float32, copy=False)
            sampled_depth = depth_map_m[
                ::TUM_RGBD_REFERENCE_CLOUD_DEPTH_STRIDE_PX,
                ::TUM_RGBD_REFERENCE_CLOUD_DEPTH_STRIDE_PX,
            ]
            valid_mask = sampled_depth > 0.0
            if not np.any(valid_mask):
                continue

            pointmap = pointmap_from_depth(
                depth_map_m,
                intrinsics,
                stride_px=TUM_RGBD_REFERENCE_CLOUD_DEPTH_STRIDE_PX,
            )
            points_xyz_camera = pointmap.reshape(-1, 3)[valid_mask.reshape(-1)].astype(np.float64, copy=False)
            T_world_camera = FrameTransform.from_matrix(
                np.asarray(trajectory.poses_se3[pose_index], dtype=np.float64),
                target_frame=TUM_RGBD_WORLD_FRAME,
                source_frame=TUM_RGBD_CAMERA_FRAME,
            )
            points_xyz_world = transform_points_world_camera(points_xyz_camera, T_world_camera)

            remaining = TUM_RGBD_REFERENCE_CLOUD_MAX_POINTS - point_count
            chunks.append(points_xyz_world[:remaining])
            point_count += min(len(points_xyz_world), remaining)
            sampled_frame_count += 1

        if not chunks:
            raise ValueError(f"TUM RGB-D sequence '{self.scene.sequence_id}' has no valid depth samples.")

        points_xyz = np.vstack(chunks).astype(np.float64, copy=False)
        cloud_path = write_point_cloud_ply(output_dir / "reference_cloud.tum_rgbd.aligned.ply", points_xyz)
        metadata_path = (output_dir / "reference_cloud.tum_rgbd.aligned.metadata.json").resolve()
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
                    "native_frame": TUM_RGBD_WORLD_FRAME,
                    "camera_frame": TUM_RGBD_CAMERA_FRAME,
                    "payload_pose_semantics": "registered_depth_unprojected_by_ground_truth_pose",
                    "depth_scale_to_m": 1.0 / 5000.0,
                    "depth_registered_to_rgb": True,
                    "units": "meters",
                    "source_association_count": len(associations),
                    "depth_association_count": len(depth_associations),
                    "sampled_frame_count": sampled_frame_count,
                    "point_count": int(len(points_xyz)),
                    "reference_cloud_frame_stride": TUM_RGBD_REFERENCE_CLOUD_FRAME_STRIDE,
                    "reference_cloud_depth_stride_px": TUM_RGBD_REFERENCE_CLOUD_DEPTH_STRIDE_PX,
                    "reference_cloud_max_frames": TUM_RGBD_REFERENCE_CLOUD_MAX_FRAMES,
                    "reference_cloud_max_points": TUM_RGBD_REFERENCE_CLOUD_MAX_POINTS,
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
            native_frame=TUM_RGBD_WORLD_FRAME,
            coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
        )


def _materialize_sampled_paths(
    paths: TumRgbdSequencePaths,
    frame_selection: FrameSelectionConfig,
    output_dir: Path,
) -> TumRgbdSequencePaths:
    import shutil

    associations = tum_rgbd_loading.load_tum_rgbd_associations(paths.sequence_dir)
    timestamps_ns = [int(round(association.rgb_timestamp_s * 1e9)) for association in associations]
    stride = frame_selection.stride_for_timestamps_ns(timestamps_ns)
    if stride <= 1:
        return paths
    rgb_dir = output_dir / "rgb"
    rgb_dir.mkdir(parents=True, exist_ok=True)
    rows: list[str] = []
    for written_index, association in enumerate(associations[::stride]):
        target_path = rgb_dir / f"{written_index:06d}{association.rgb_path.suffix}"
        if not target_path.exists():
            shutil.copy2(association.rgb_path, target_path)
        rows.append(f"{association.rgb_timestamp_s:.9f} rgb/{target_path.name}")
    sampled_rgb_list = output_dir / "rgb.txt"
    sampled_rgb_list.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return paths.model_copy(update={"rgb_list_path": sampled_rgb_list, "sequence_dir": output_dir})


def _relative_to_sequence_root(path: Path, sequence_dir: Path) -> Path:
    try:
        return path.relative_to(sequence_dir)
    except ValueError as exc:
        raise ValueError(f"Expected TUM RGB-D path '{path}' to live under sequence dir '{sequence_dir}'.") from exc
