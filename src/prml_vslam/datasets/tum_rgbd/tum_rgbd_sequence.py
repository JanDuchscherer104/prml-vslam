from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ConfigDict

from prml_vslam.benchmark import ReferenceSource
from prml_vslam.datasets.contracts import FrameSelectionConfig
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, ReferenceTrajectoryRef
from prml_vslam.io import Cv2ReplayMode
from prml_vslam.protocols import FramePacketStream
from prml_vslam.utils import BaseData

from . import tum_rgbd_layout, tum_rgbd_loading
from .tum_rgbd_models import TumRgbdCatalog, TumRgbdPoseSource, TumRgbdSequenceConfig
from .tum_rgbd_replay_adapter import open_tum_rgbd_stream

if TYPE_CHECKING:
    from prml_vslam.interfaces.ingest import SequenceManifest


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
        from prml_vslam.interfaces.ingest import SequenceManifest

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
        return PreparedBenchmarkInputs(
            reference_trajectories=[ReferenceTrajectoryRef(source=ReferenceSource.GROUND_TRUTH, path=reference_path)]
        )

    def open_stream(
        self,
        *,
        pose_source: TumRgbdPoseSource = TumRgbdPoseSource.GROUND_TRUTH,
        stride: int = 1,
        loop: bool = True,
        replay_mode: Cv2ReplayMode = Cv2ReplayMode.REALTIME,
        include_depth: bool = True,
    ) -> FramePacketStream:
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
