from __future__ import annotations

import tarfile
from pathlib import Path

import cv2
import numpy as np

from prml_vslam.datasets.contracts import DatasetId, FrameSelectionConfig
from prml_vslam.datasets.registry import list_sequence_slugs, resolve_reference_path
from prml_vslam.datasets.tum_rgbd import (
    TumRgbdCatalog,
    TumRgbdDatasetService,
    TumRgbdDownloadRequest,
    TumRgbdModality,
    TumRgbdSceneMetadata,
    TumRgbdSequence,
    TumRgbdSequenceConfig,
)
from prml_vslam.io import Cv2ReplayMode
from prml_vslam.reconstruction import FileRgbdObservationSource
from prml_vslam.utils import PathConfig
from prml_vslam.utils.geometry import load_tum_trajectory


def _write_tum_rgbd_sequence(
    dataset_root: Path,
    *,
    sequence_id: str = "freiburg1_desk",
    image_shape: tuple[int, int] = (48, 64),
) -> Path:
    sequence_dir = dataset_root / f"rgbd_dataset_{sequence_id}"
    (sequence_dir / "rgb").mkdir(parents=True, exist_ok=True)
    (sequence_dir / "depth").mkdir(parents=True, exist_ok=True)
    rgb_rows: list[str] = []
    depth_rows: list[str] = []
    ground_truth_rows: list[str] = []
    height_px, width_px = image_shape
    for index, timestamp_s in enumerate((0.0, 0.1, 0.2)):
        rgb_path = sequence_dir / "rgb" / f"{timestamp_s:.6f}.png"
        depth_path = sequence_dir / "depth" / f"{timestamp_s:.6f}.png"
        rgb = np.full((height_px, width_px, 3), index * 50, dtype=np.uint8)
        depth = np.full((height_px, width_px), 5000 + index, dtype=np.uint16)
        assert cv2.imwrite(str(rgb_path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        assert cv2.imwrite(str(depth_path), depth)
        rgb_rows.append(f"{timestamp_s:.6f} rgb/{timestamp_s:.6f}.png")
        depth_rows.append(f"{timestamp_s:.6f} depth/{timestamp_s:.6f}.png")
        ground_truth_rows.append(f"{timestamp_s:.6f} {index:.3f} 0.0 0.0 0.0 0.0 0.0 1.0")
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
    assert benchmark_inputs.rgbd_observation_sequences[0].observation_count == 3
    assert load_tum_trajectory(benchmark_inputs.reference_trajectories[0].path).positions_xyz.shape == (3, 3)
    assert list_sequence_slugs(DatasetId.TUM_RGBD, tmp_path) == ["freiburg1_desk"]
    assert (
        resolve_reference_path(DatasetId.TUM_RGBD, tmp_path, "freiburg1_desk")
        == sequence_dir / "evaluation" / "ground_truth.tum"
    )


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
    _write_tum_rgbd_sequence(tmp_path)
    sequence = TumRgbdSequence(config=TumRgbdSequenceConfig(dataset_root=tmp_path, sequence_id="freiburg1_desk"))

    stream = sequence.open_stream(loop=True, replay_mode=Cv2ReplayMode.FAST_AS_POSSIBLE)

    stream.connect()
    packet_0 = stream.wait_for_packet()
    packet_1 = stream.wait_for_packet()
    packet_2 = stream.wait_for_packet()
    packet_3 = stream.wait_for_packet()
    stream.disconnect()

    assert packet_0.seq == 0
    assert packet_1.seq == 1
    assert packet_2.seq == 2
    assert packet_3.seq == 0
    assert packet_3.provenance.loop_index == 1
    assert packet_0.rgb.shape == (48, 64, 3)
    assert packet_0.depth is not None
    assert packet_0.depth.shape == (48, 64)
    assert packet_0.intrinsics is not None
    assert packet_0.intrinsics.width_px == 640
    assert packet_2.pose is not None
    assert packet_2.pose.tx == 2.0
    assert packet_2.pose.target_frame == "tum_rgbd_mocap_world"
    assert packet_2.pose.source_frame == "tum_rgbd_rgb_camera"
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
    sequence_ref = benchmark_inputs.rgbd_observation_sequences[0]
    observations = list(FileRgbdObservationSource(sequence_ref).iter_observations())

    assert sequence_ref.source_id == "tum_rgbd"
    assert sequence_ref.observation_count == 3
    assert len(observations) == 3
    assert observations[0].image_rgb is not None
    assert observations[0].image_rgb.shape == (480, 640, 3)
    assert observations[0].depth_map_m.shape == (480, 640)
    assert observations[0].camera_intrinsics.width_px == 640
    assert observations[0].camera_intrinsics.height_px == 480
    assert observations[2].T_world_camera.tx == 2.0
    assert observations[2].T_world_camera.target_frame == "tum_rgbd_mocap_world"
    assert observations[2].T_world_camera.source_frame == "tum_rgbd_rgb_camera"
    assert observations[0].provenance.dataset_id == "tum_rgbd"
    assert observations[0].provenance.world_frame == "tum_rgbd_mocap_world"
