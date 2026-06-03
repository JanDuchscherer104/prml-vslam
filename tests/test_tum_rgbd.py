from __future__ import annotations

import json
import tarfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from prml_vslam.interfaces import CAMERA_RDF_FRAME
from prml_vslam.sources import FileObservationSequenceLoader
from prml_vslam.sources.contracts import ReferenceCloudCoordinateStatus, ReferenceCloudSource
from prml_vslam.sources.datasets.contracts import DatasetId, FrameSelectionConfig
from prml_vslam.sources.datasets.registry import list_sequence_slugs, resolve_reference_path
from prml_vslam.sources.datasets.tum_rgbd import (
    TumRgbdCatalog,
    TumRgbdDatasetService,
    TumRgbdDownloadRequest,
    TumRgbdModality,
    TumRgbdSceneMetadata,
    TumRgbdSequence,
    TumRgbdSequenceConfig,
)
from prml_vslam.sources.replay import ReplayMode
from prml_vslam.utils import PathConfig
from prml_vslam.utils.geometry import load_point_cloud_ply, load_tum_trajectory


def _write_tum_rgbd_sequence(
    dataset_root: Path,
    *,
    sequence_id: str = "freiburg1_desk",
    image_shape: tuple[int, int] = (48, 64),
    frame_count: int = 3,
    zero_depth_pixels: dict[int, list[tuple[int, int]]] | None = None,
    depth_timestamp_offset_s: float = 0.0,
    pose_timestamp_offset_s: float = 0.0,
) -> Path:
    sequence_dir = dataset_root / f"rgbd_dataset_{sequence_id}"
    (sequence_dir / "rgb").mkdir(parents=True, exist_ok=True)
    (sequence_dir / "depth").mkdir(parents=True, exist_ok=True)
    rgb_rows: list[str] = []
    depth_rows: list[str] = []
    ground_truth_rows: list[str] = []
    height_px, width_px = image_shape
    for index in range(frame_count):
        timestamp_s = index * 0.1
        depth_timestamp_s = timestamp_s + depth_timestamp_offset_s
        pose_timestamp_s = timestamp_s + pose_timestamp_offset_s
        rgb_path = sequence_dir / "rgb" / f"{timestamp_s:.6f}.png"
        depth_path = sequence_dir / "depth" / f"{depth_timestamp_s:.6f}.png"
        rgb = np.full((height_px, width_px, 3), (index * 50) % 256, dtype=np.uint8)
        depth = np.full((height_px, width_px), 5000 + index, dtype=np.uint16)
        for row_px, col_px in (zero_depth_pixels or {}).get(index, []):
            depth[row_px, col_px] = 0
        assert cv2.imwrite(str(rgb_path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        assert cv2.imwrite(str(depth_path), depth)
        rgb_rows.append(f"{timestamp_s:.6f} rgb/{timestamp_s:.6f}.png")
        depth_rows.append(f"{depth_timestamp_s:.6f} depth/{depth_timestamp_s:.6f}.png")
        ground_truth_rows.append(f"{pose_timestamp_s:.6f} {index:.3f} 0.0 0.0 0.0 0.0 0.0 1.0")
    (sequence_dir / "rgb.txt").write_text("\n".join(rgb_rows) + "\n", encoding="utf-8")
    (sequence_dir / "depth.txt").write_text("\n".join(depth_rows) + "\n", encoding="utf-8")
    (sequence_dir / "groundtruth.txt").write_text("\n".join(ground_truth_rows) + "\n", encoding="utf-8")
    return sequence_dir


def _write_tum_rgbd_archive(source_dir: Path, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "w:gz") as archive:
        for path in sorted(source_dir.rglob("*")):
            archive.add(path, arcname=path.relative_to(source_dir).as_posix())


def _build_fake_catalog(tmp_path: Path) -> TumRgbdCatalog:
    source_root = tmp_path / "upstream"
    _write_tum_rgbd_sequence(source_root, sequence_id="freiburg1_desk")
    archive_path = tmp_path / "archives" / "rgbd_dataset_freiburg1_desk.tgz"
    _write_tum_rgbd_archive(source_root, archive_path)
    return TumRgbdCatalog(
        dataset_id="tum_rgbd",
        dataset_label="TUM RGB-D",
        upstream={
            "dataset_url": "https://cvg.cit.tum.de/data/datasets/rgbd-dataset",
            "file_formats_url": "https://cvg.cit.tum.de/data/datasets/rgbd-dataset/file_formats",
        },
        scenes=[
            TumRgbdSceneMetadata(
                sequence_id="freiburg1_desk",
                folder_name="rgbd_dataset_freiburg1_desk",
                display_name="fr1/desk",
                category="Handheld SLAM",
                archive_url=archive_path.as_uri(),
                archive_size_bytes=archive_path.stat().st_size,
            )
        ],
    )


def test_tum_rgbd_sequence_loads_normalizes_and_registers(tmp_path: Path) -> None:
    sequence_dir = _write_tum_rgbd_sequence(tmp_path)
    sequence = TumRgbdSequence(config=TumRgbdSequenceConfig(dataset_root=tmp_path, sequence_id="freiburg1_desk"))

    sample = sequence.load_offline_sample()
    manifest = sequence.to_sequence_manifest()
    benchmark_inputs = sequence.to_benchmark_inputs()

    assert sample.sequence_id == "freiburg1_desk"
    assert sample.sequence_name == "fr1/desk"
    assert sample.frame_timestamps_ns.tolist() == [0, 100_000_000, 200_000_000]
    assert sample.intrinsics.fx == 517.3
    assert sample.ground_truth.positions_xyz[2].tolist() == [2.0, 0.0, 0.0]
    assert sample.associations[0].rgb_path == sequence_dir / "rgb" / "0.000000.png"
    assert sample.associations[0].depth_path == sequence_dir / "depth" / "0.000000.png"
    assert sample.duration_s == 0.2
    assert manifest.sequence_id == "freiburg1_desk"
    assert manifest.dataset_id is DatasetId.TUM_RGBD
    assert manifest.rgb_dir == sequence_dir / "rgb"
    assert manifest.timestamps_path == sequence_dir / "rgb.txt"
    assert manifest.intrinsics_path == sequence_dir / "intrinsics.yaml"
    assert manifest.intrinsics_path.exists()
    assert benchmark_inputs.reference_trajectories[0].path == sequence_dir / "evaluation" / "ground_truth.tum"
    reference_cloud = benchmark_inputs.reference_clouds[0]
    reference_cloud_points = load_point_cloud_ply(reference_cloud.path)
    reference_cloud_metadata = json.loads(reference_cloud.metadata_path.read_text(encoding="utf-8"))
    assert reference_cloud.source is ReferenceCloudSource.TUM_RGBD
    assert reference_cloud.coordinate_status is ReferenceCloudCoordinateStatus.ALIGNED
    assert reference_cloud.target_frame == "tum_rgbd_mocap_world"
    assert reference_cloud.native_frame == "tum_rgbd_mocap_world"
    assert reference_cloud.path == sequence_dir / "evaluation" / "reference_cloud.tum_rgbd.aligned.ply"
    assert (
        reference_cloud.metadata_path == sequence_dir / "evaluation" / "reference_cloud.tum_rgbd.aligned.metadata.json"
    )
    assert reference_cloud_metadata["source"] == "tum_rgbd"
    assert reference_cloud_metadata["depth_scale_to_m"] == 1.0 / 5000.0
    assert reference_cloud_metadata["payload_pose_semantics"] == "registered_depth_unprojected_by_ground_truth_pose"
    assert reference_cloud_metadata["point_count"] == len(reference_cloud_points)
    assert len(reference_cloud_points) > 0
    assert benchmark_inputs.observation_sequences[0].observation_count == 3
    assert load_tum_trajectory(benchmark_inputs.reference_trajectories[0].path).positions_xyz.shape == (3, 3)
    assert list_sequence_slugs(DatasetId.TUM_RGBD, tmp_path) == ["freiburg1_desk"]
    assert (
        resolve_reference_path(DatasetId.TUM_RGBD, tmp_path, "freiburg1_desk")
        == sequence_dir / "evaluation" / "ground_truth.tum"
    )


def test_tum_rgbd_reference_cloud_masks_invalid_depth_and_bounds_frames(tmp_path: Path) -> None:
    _write_tum_rgbd_sequence(
        tmp_path,
        image_shape=(16, 16),
        frame_count=250,
        zero_depth_pixels={0: [(0, 0)]},
    )
    sequence = TumRgbdSequence(config=TumRgbdSequenceConfig(dataset_root=tmp_path, sequence_id="freiburg1_desk"))

    benchmark_inputs = sequence.to_benchmark_inputs(output_dir=tmp_path / "benchmark")
    reference_cloud = benchmark_inputs.reference_clouds[0]
    points = load_point_cloud_ply(reference_cloud.path)
    metadata = json.loads(reference_cloud.metadata_path.read_text(encoding="utf-8"))

    assert points.shape == (79, 3)
    assert not np.any(np.all(np.isclose(points, 0.0), axis=1))
    assert metadata["source_association_count"] == 250
    assert metadata["sampled_frame_count"] == 20
    assert metadata["reference_cloud_frame_stride"] == 10
    assert metadata["reference_cloud_depth_stride_px"] == 8
    assert metadata["reference_cloud_max_frames"] == 20
    assert metadata["reference_cloud_max_points"] == 100_000


def test_tum_rgbd_association_window_matches_vista_slam_default(tmp_path: Path) -> None:
    _write_tum_rgbd_sequence(
        tmp_path,
        depth_timestamp_offset_s=0.05,
        pose_timestamp_offset_s=0.05,
    )
    sequence = TumRgbdSequence(config=TumRgbdSequenceConfig(dataset_root=tmp_path, sequence_id="freiburg1_desk"))

    sample = sequence.load_offline_sample()
    benchmark_inputs = sequence.to_benchmark_inputs(output_dir=tmp_path / "benchmark")
    metadata = json.loads(benchmark_inputs.reference_clouds[0].metadata_path.read_text(encoding="utf-8"))

    assert len(sample.associations) == 3
    assert sample.associations[0].depth_timestamp_s == pytest.approx(0.05)
    assert sample.associations[0].pose_timestamp_s == pytest.approx(0.05)
    assert benchmark_inputs.observation_sequences[0].observation_count == 3
    assert metadata["source_association_count"] == 3


def test_tum_rgbd_sequence_manifest_materializes_sampled_rgb_dir(tmp_path: Path) -> None:
    _write_tum_rgbd_sequence(tmp_path)
    sequence = TumRgbdSequence(config=TumRgbdSequenceConfig(dataset_root=tmp_path, sequence_id="freiburg1_desk"))

    manifest = sequence.to_sequence_manifest(
        output_dir=tmp_path / "manifest", frame_selection=FrameSelectionConfig(frame_stride=2)
    )

    assert manifest.rgb_dir == tmp_path / "manifest" / "rgb"
    assert sorted(path.name for path in manifest.rgb_dir.glob("*.png")) == ["000000.png", "000001.png"]
    assert manifest.timestamps_path.read_text(encoding="utf-8").splitlines() == [
        "0.000000000 rgb/000000.png",
        "0.200000000 rgb/000001.png",
    ]


def test_tum_rgbd_stream_loops_rgbd_frames_with_pose_metadata(tmp_path: Path) -> None:
    _write_tum_rgbd_sequence(tmp_path, image_shape=(480, 640))
    sequence = TumRgbdSequence(config=TumRgbdSequenceConfig(dataset_root=tmp_path, sequence_id="freiburg1_desk"))

    stream = sequence.open_stream(loop=True, replay_mode=ReplayMode.FAST_AS_POSSIBLE)

    stream.connect()
    packet_0 = stream.wait_for_observation()
    packet_1 = stream.wait_for_observation()
    packet_2 = stream.wait_for_observation()
    packet_3 = stream.wait_for_observation()
    stream.disconnect()

    assert packet_0.seq == 0
    assert packet_1.seq == 1
    assert packet_2.seq == 2
    assert packet_3.seq == 3
    assert packet_3.source_frame_index == 0
    assert packet_3.loop_index == 1
    assert packet_0.rgb.shape == (480, 640, 3)
    assert packet_0.depth_m is not None
    assert packet_0.depth_m.shape == (480, 640)
    assert packet_0.intrinsics is not None
    assert packet_0.intrinsics.width_px == 640
    assert packet_2.T_world_camera is not None
    assert packet_2.T_world_camera.tx == 2.0
    assert packet_2.T_world_camera.target_frame == "tum_rgbd_mocap_world"
    assert packet_2.T_world_camera.source_frame == CAMERA_RDF_FRAME
    assert packet_0.provenance.source_id == "tum_rgbd"
    assert packet_0.provenance.dataset_id == "tum_rgbd"


def test_tum_rgbd_dataset_service_downloads_selected_modalities(tmp_path: Path) -> None:
    catalog = _build_fake_catalog(tmp_path)
    service = TumRgbdDatasetService(PathConfig(root=tmp_path), catalog=catalog)

    result = service.download(
        TumRgbdDownloadRequest(
            sequence_ids=["freiburg1_desk"],
            modalities=[TumRgbdModality.RGB, TumRgbdModality.GROUND_TRUTH],
        )
    )

    dataset_root = tmp_path / ".data" / "tum_rgbd"
    archive_path = dataset_root / ".archives" / "rgbd_dataset_freiburg1_desk.tgz"
    assert result.downloaded_archive_count == 1
    assert archive_path.exists()
    assert (dataset_root / "rgbd_dataset_freiburg1_desk" / "rgb.txt").exists()
    assert (dataset_root / "rgbd_dataset_freiburg1_desk" / "rgb" / "0.000000.png").exists()
    assert (dataset_root / "rgbd_dataset_freiburg1_desk" / "groundtruth.txt").exists()
    assert not (dataset_root / "rgbd_dataset_freiburg1_desk" / "depth.txt").exists()

    status = service.local_scene_statuses()[0]
    assert status.archive_path == archive_path
    assert status.local_modalities == [TumRgbdModality.RGB, TumRgbdModality.GROUND_TRUTH]
    assert status.replay_ready is True
    assert status.offline_ready is False


def test_tum_rgbd_prepares_file_backed_rgbd_observations(tmp_path: Path) -> None:
    _write_tum_rgbd_sequence(tmp_path, image_shape=(480, 640))
    sequence = TumRgbdSequence(config=TumRgbdSequenceConfig(dataset_root=tmp_path, sequence_id="freiburg1_desk"))

    benchmark_inputs = sequence.to_benchmark_inputs(output_dir=tmp_path / "benchmark")
    sequence_ref = benchmark_inputs.observation_sequences[0]
    observations = list(FileObservationSequenceLoader(sequence_ref).iter_observations())

    assert sequence_ref.source_id == "tum_rgbd"
    assert sequence_ref.observation_count == 3
    assert len(observations) == 3
    assert observations[0].rgb is not None
    assert observations[0].rgb.shape == (480, 640, 3)
    assert observations[0].depth_m is not None
    assert observations[0].depth_m.shape == (480, 640)
    assert observations[0].intrinsics is not None
    assert observations[0].intrinsics.width_px == 640
    assert observations[0].intrinsics.height_px == 480
    assert observations[2].T_world_camera.tx == 2.0
    assert observations[2].T_world_camera.target_frame == "tum_rgbd_mocap_world"
    assert observations[2].T_world_camera.source_frame == CAMERA_RDF_FRAME
    assert observations[0].provenance.dataset_id == "tum_rgbd"
    assert observations[0].provenance.world_frame == "tum_rgbd_mocap_world"
