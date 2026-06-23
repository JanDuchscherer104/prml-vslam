"""Tests for the simplified ADVIO adapter and replay stream."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import cv2
import numpy as np
import pytest

import prml_vslam.sources.replay.video as replay_video_module
from prml_vslam.interfaces import ObservationSequenceIndex
from prml_vslam.sources.config import AdvioSourceConfig, normalized_profile_for_source_config
from prml_vslam.sources.contracts import (
    ReferenceCloudCoordinateStatus,
    ReferenceSource,
)
from prml_vslam.sources.datasets.advio import (
    AdvioCatalog,
    AdvioDatasetService,
    AdvioDownloadRequest,
    AdvioEnvironment,
    AdvioPeopleLevel,
    AdvioPoseFrameMode,
    AdvioPoseSource,
    AdvioSceneMetadata,
    AdvioSequence,
    AdvioSequenceConfig,
    AdvioServingConfig,
    AdvioUpstreamMetadata,
)
from prml_vslam.sources.datasets.advio.advio_frames import (
    APPLE_Y_UP_TO_RDF,
    transform_advio_trajectory_to_rdf,
)
from prml_vslam.sources.datasets.advio.advio_layout import list_local_sequence_ids, resolve_existing_reference_tum
from prml_vslam.sources.datasets.advio.advio_loading import (
    _read_numeric_csv,
    load_advio_calibration,
    load_advio_trajectory,
)
from prml_vslam.sources.datasets.contracts import (
    ADVIO_FIXEDPOINT_COMMON_START_TRAJECTORY_CONVENTION,
    ADVIO_LOCAL_FIRST_POSE_TRAJECTORY_CONVENTION,
    DatasetId,
)
from prml_vslam.sources.datasets.normalization import normalize_dataset_entry
from prml_vslam.sources.datasets.normalized_query import query_normalized_dataset
from prml_vslam.sources.datasets.normalized_store import NormalizedDatasetProfile, normalized_store_for_path_config
from prml_vslam.sources.replay import PyAvVideoObservationSource, ReplayMode
from prml_vslam.utils import PathConfig
from prml_vslam.utils.geometry import load_tum_trajectory


def _write_video(path: Path, *, num_frames: int = 3) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (64, 48))
    for index in range(num_frames):
        frame = np.full((48, 64, 3), index * 50, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def _write_calibration(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """
cameras:
- camera:
    image_height: 48
    image_width: 64
    type: pinhole
    intrinsics:
      data: [100.0, 101.0, 32.0, 24.0]
    distortion:
      type: radial-tangential
      parameters:
        data: [0.1, 0.01, 0.0, 0.0]
    T_cam_imu:
      data:
      - [1.0, 0.0, 0.0, 0.01]
      - [0.0, 1.0, 0.0, 0.02]
      - [0.0, 0.0, 1.0, 0.03]
      - [0.0, 0.0, 0.0, 1.0]
""".strip(),
        encoding="utf-8",
    )


def _write_pose_csv(path: Path) -> None:
    _write_pose_csv_rows(
        path,
        rows=((0.0, 1.0, 2.0, 3.0), (0.1, 1.5, 2.5, 3.5), (0.2, 2.0, 3.0, 4.0)),
    )


def test_advio_basis_helpers_convert_provider_positions_to_rdf(tmp_path: Path) -> None:
    assert np.linalg.det(APPLE_Y_UP_TO_RDF) == pytest.approx(1.0)

    pose_csv = tmp_path / "arkit.csv"
    _write_pose_csv_rows(pose_csv, rows=((0.0, 1.0, 2.0, 3.0), (0.1, 1.5, 2.5, 3.5), (0.2, 2.0, 3.0, 4.0)))
    trajectory = transform_advio_trajectory_to_rdf(
        load_advio_trajectory(pose_csv),
        AdvioPoseSource.ARKIT,
    )
    assert np.allclose(trajectory.positions_xyz[0], np.array([3.0, -2.0, 1.0]))


def test_advio_apple_basis_preserves_upstream_top_view_handedness() -> None:
    raw_points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    rdf_points = raw_points @ APPLE_Y_UP_TO_RDF.T

    upstream_top_area = _signed_area(raw_points[:, [2, 0]])
    repo_top_area = _signed_area(rdf_points[:, [0, 2]])

    assert repo_top_area == pytest.approx(upstream_top_area)


def _signed_area(points_xy: np.ndarray) -> float:
    x = points_xy[:, 0]
    y = points_xy[:, 1]
    return float(0.5 * np.sum(x[:-1] * y[1:] - x[1:] * y[:-1]))


def _write_pose_csv_rows(path: Path, *, rows: tuple[tuple[float, float, float, float], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(f"{t},{x},{y},{z},1.0,0.0,0.0,0.0" for t, x, y, z in rows) + "\n",
        encoding="utf-8",
    )


def _write_fixpoints_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for timestamp_s in np.linspace(0.0, 0.2, 6):
        x = 1.0 + 5.0 * timestamp_s
        y = 2.0 + 5.0 * timestamp_s
        z = 3.0 + 5.0 * timestamp_s
        rows.append(f"{timestamp_s:.6f},{x:.6f},{z:.6f},{y:.6f}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _write_advio_sequence(
    dataset_root: Path,
    *,
    sequence_id: int = 15,
    nested_layout: bool = False,
    official_archive_names: bool = False,
) -> Path:
    sequence_name = f"advio-{sequence_id:02d}"
    sequence_dir = (dataset_root / "data" / sequence_name) if nested_layout else (dataset_root / sequence_name)
    (sequence_dir / "iphone").mkdir(parents=True, exist_ok=True)
    (sequence_dir / "pixel").mkdir(parents=True, exist_ok=True)
    (sequence_dir / "ground-truth").mkdir(parents=True, exist_ok=True)

    _write_video(sequence_dir / "iphone" / "frames.mov")
    (sequence_dir / "iphone" / "frames.csv").write_text(
        "0.0,0\n0.1,1\n0.2,2\n",
        encoding="utf-8",
    )
    sensor_names = (
        (
            "platform-locations.csv",
            "accelerometer.csv",
            "gyro.csv",
            "magnetometer.csv",
            "barometer.csv",
        )
        if official_archive_names
        else (
            "platform-location.csv",
            "accelerometer.csv",
            "gyroscope.csv",
            "magnetometer.csv",
            "barometer.csv",
        )
    )
    for name in sensor_names:
        (sequence_dir / "iphone" / name).write_text("0.0,0.0,0.0,0.0\n", encoding="utf-8")
    ground_truth_name = "pose.csv" if official_archive_names else "poses.csv"
    _write_pose_csv(sequence_dir / "ground-truth" / ground_truth_name)
    _write_fixpoints_csv(sequence_dir / "ground-truth" / "fixpoints.csv")
    _write_pose_csv(sequence_dir / "pixel" / "arcore.csv")
    _write_pose_csv(sequence_dir / "iphone" / "arkit.csv")
    _write_calibration(dataset_root / "calibration" / "iphone-03.yaml")
    return sequence_dir


def _write_advio_archive(source_dir: Path, archive_path: Path, *, include_directory_entries: bool = False) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive_path, "w") as archive:
        if include_directory_entries:
            for path in sorted(source_dir.rglob("*")):
                if path.is_dir():
                    archive.writestr(path.relative_to(source_dir).as_posix() + "/", "")
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir():
                continue
            archive.write(path, arcname=path.relative_to(source_dir).as_posix())


def _build_fake_catalog(tmp_path: Path, *, sequence_id: int = 15) -> AdvioCatalog:
    scene_slug = f"advio-{sequence_id:02d}"
    archive_path = tmp_path / "upstream" / f"{scene_slug}.zip"
    source_root = tmp_path / "upstream" / "scene-root"
    _write_advio_sequence(source_root / "data", sequence_id=sequence_id)
    _write_advio_archive(source_root, archive_path)
    calibration_source_dir = tmp_path / "upstream" / "calibration"
    _write_calibration(calibration_source_dir / "iphone-03.yaml")
    import hashlib

    digest = hashlib.md5(archive_path.read_bytes()).hexdigest()
    return AdvioCatalog(
        dataset_id="advio",
        dataset_label="ADVIO",
        upstream=AdvioUpstreamMetadata(
            repo_url="https://github.com/AaltoVision/ADVIO",
            zenodo_record_url="https://zenodo.org/records/1476931",
            doi="10.5281/zenodo.1320824",
            license="CC BY-NC 4.0",
            calibration_base_url=calibration_source_dir.as_uri() + "/",
        ),
        scenes=[
            AdvioSceneMetadata(
                sequence_id=sequence_id,
                sequence_slug=scene_slug,
                venue="Office",
                dataset_code="03",
                environment=AdvioEnvironment.INDOOR,
                has_stairs=False,
                has_escalator=False,
                has_elevator=False,
                people_level=AdvioPeopleLevel.NONE,
                has_vehicles=False,
                calibration_name="iphone-03.yaml",
                archive_url=archive_path.as_uri(),
                archive_size_bytes=archive_path.stat().st_size,
                archive_md5=digest,
            )
        ],
    )


def test_load_advio_sequence_returns_offline_sample(tmp_path: Path) -> None:
    sequence_dir = _write_advio_sequence(tmp_path)

    sample = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15)).load_offline_sample()

    assert sample.sequence_name == "advio-15"
    assert sample.paths.video_path == sequence_dir / "iphone" / "frames.mov"
    assert sample.frame_timestamps_ns.tolist() == [0, 100_000_000, 200_000_000]
    assert sample.calibration.intrinsics.width_px == 64
    assert sample.calibration.intrinsics.height_px == 48
    assert sample.ground_truth.positions_xyz.shape == (3, 3)
    assert sample.ground_truth.orientations_quat_wxyz[0].tolist() == [1.0, 0.0, 0.0, 0.0]
    assert sample.arcore.positions_xyz[2].tolist() == [2.0, 3.0, 4.0]
    assert sample.duration_s == 0.2


def test_advio_numeric_csv_loader_rejects_non_rectangular_rows(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("0.0,1.0\n0.1,1.0,2.0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="rectangular"):
        _read_numeric_csv(path, min_columns=2)


def test_advio_sequence_uses_catalog_calibration_metadata(tmp_path: Path) -> None:
    dataset_root = tmp_path / ".data" / "advio"
    _write_advio_sequence(dataset_root)
    _write_calibration(dataset_root / "calibration" / "iphone-custom.yaml")
    catalog = _build_fake_catalog(tmp_path)
    catalog.scenes[0].calibration_name = "iphone-custom.yaml"

    sample = AdvioDatasetService(PathConfig(root=tmp_path), catalog=catalog).load_local_sample(15)

    assert sample.paths.calibration_path == tmp_path / ".data" / "advio" / "calibration" / "iphone-custom.yaml"


def test_load_advio_calibration_tolerates_tab_indentation(tmp_path: Path) -> None:
    calibration_path = tmp_path / "iphone-tabs.yaml"
    calibration_path.write_text(
        "\n".join(
            [
                "cameras:",
                "- camera:",
                "\timage_height: 48",
                "\timage_width: 64",
                "\ttype: pinhole",
                "\tintrinsics:",
                "\t  data: [100.0, 101.0, 32.0, 24.0]",
                "\tdistortion:",
                "\t  type: radial-tangential",
                "\t  parameters:",
                "\t    data: [0.1, 0.01, 0.0, 0.0]",
                "\tT_cam_imu:",
                "\t  data:",
                "\t  - [1.0, 0.0, 0.0, 0.01]",
                "\t  - [0.0, 1.0, 0.0, 0.02]",
                "\t  - [0.0, 0.0, 1.0, 0.03]",
                "\t  - [0.0, 0.0, 0.0, 1.0]\t\t",
            ]
        ),
        encoding="utf-8",
    )

    calibration = load_advio_calibration(calibration_path)

    assert calibration.intrinsics.fx == 100.0
    assert calibration.intrinsics.height_px == 48
    assert calibration.t_cam_imu.tx == 0.01


def test_advio_open_stream_loops_through_sample_with_pyav_replay(tmp_path: Path) -> None:
    _write_advio_sequence(tmp_path)
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    stream = sequence.open_stream(
        pose_source=AdvioPoseSource.GROUND_TRUTH,
        loop=True,
        replay_mode=ReplayMode.FAST_AS_POSSIBLE,
    )

    assert isinstance(stream, PyAvVideoObservationSource)
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
    assert packet_0.timestamp_ns == 0
    assert packet_1.timestamp_ns == 100_000_000
    assert packet_0.intrinsics is not None
    assert packet_0.T_world_camera is not None
    assert [packet_0.T_world_camera.tx, packet_0.T_world_camera.ty, packet_0.T_world_camera.tz] == [3.0, -2.0, 1.0]
    assert packet_2.T_world_camera is not None
    assert [packet_2.T_world_camera.tx, packet_2.T_world_camera.ty, packet_2.T_world_camera.tz] == [4.0, -3.0, 2.0]
    assert packet_3.loop_index == 1
    assert packet_0.provenance.dataset_id == "advio"
    assert packet_0.provenance.pose_source == AdvioPoseSource.GROUND_TRUTH.value


def test_advio_open_stream_supports_replay_ready_bundle_without_arcore(tmp_path: Path) -> None:
    sequence_dir = _write_advio_sequence(tmp_path)
    (sequence_dir / "pixel" / "arcore.csv").unlink()
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    stream = sequence.open_stream(
        pose_source=AdvioPoseSource.GROUND_TRUTH,
        loop=True,
        replay_mode=ReplayMode.FAST_AS_POSSIBLE,
    )

    stream.connect()
    packet = stream.wait_for_observation()
    stream.disconnect()

    assert packet.seq == 0
    assert packet.T_world_camera is not None
    assert [packet.T_world_camera.tx, packet.T_world_camera.ty, packet.T_world_camera.tz] == [3.0, -2.0, 1.0]


def test_advio_open_stream_orientation_normalization_keeps_default_behavior_without_metadata(
    tmp_path: Path,
) -> None:
    _write_advio_sequence(tmp_path)
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    stream = sequence.open_stream(replay_mode=ReplayMode.FAST_AS_POSSIBLE, normalize_video_orientation=True)

    assert isinstance(stream, PyAvVideoObservationSource)


def test_read_video_rotation_degrees_uses_opencv_orientation_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video_path = tmp_path / "demo.mp4"
    _write_video(video_path)

    class FakeCapture:
        def isOpened(self) -> bool:
            return True

        def get(self, prop_id: int) -> float:
            del prop_id
            return 90.0

        def release(self) -> None:
            return None

    monkeypatch.setattr(cv2, "CAP_PROP_ORIENTATION_META", 48, raising=False)
    monkeypatch.setattr(cv2, "VideoCapture", lambda path: FakeCapture())

    assert replay_video_module.read_video_rotation_degrees(video_path) == 90


def test_advio_open_stream_orientation_normalization_rotates_packets_and_intrinsics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_advio_sequence(tmp_path)
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))
    monkeypatch.setattr(replay_video_module, "read_video_rotation_degrees", lambda path: 90)

    stream = sequence.open_stream(replay_mode=ReplayMode.FAST_AS_POSSIBLE, normalize_video_orientation=True)
    stream.connect()
    packet = stream.wait_for_observation()
    stream.disconnect()

    assert packet.rgb.shape == (64, 48, 3)
    assert packet.provenance.video_rotation_degrees == 90
    assert packet.provenance.original_width == 64
    assert packet.provenance.original_height == 48
    assert packet.intrinsics is not None
    assert packet.intrinsics.width_px == 48
    assert packet.intrinsics.height_px == 64
    assert packet.intrinsics.fx == 101.0
    assert packet.intrinsics.fy == 100.0
    assert packet.intrinsics.cx == 24.0
    assert packet.intrinsics.cy == 32.0


def test_advio_open_stream_orientation_normalization_uses_pyav_replay_source(tmp_path: Path) -> None:
    _write_advio_sequence(tmp_path)
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    stream = sequence.open_stream(replay_mode=ReplayMode.FAST_AS_POSSIBLE, normalize_video_orientation=True)

    assert isinstance(stream, PyAvVideoObservationSource)
    assert stream.normalize_video_orientation is True


def test_advio_sequence_can_normalize_to_sequence_manifest(tmp_path: Path) -> None:
    sequence_dir = _write_advio_sequence(tmp_path)
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    manifest = sequence.to_sequence_manifest(
        dataset_serving=AdvioServingConfig(
            pose_source=AdvioPoseSource.ARCORE,
            pose_frame_mode=AdvioPoseFrameMode.PROVIDER_WORLD,
        )
    )
    benchmark_inputs = sequence.to_benchmark_inputs()

    assert manifest.sequence_id == "advio-15"
    assert manifest.dataset_id == "advio"
    assert manifest.dataset_serving is not None
    assert manifest.dataset_serving.pose_source is AdvioPoseSource.ARCORE
    assert manifest.video_path == sequence_dir / "iphone" / "frames.mov"
    assert manifest.timestamps_path == sequence_dir / "iphone" / "frames.csv"
    assert manifest.intrinsics_path == tmp_path / "calibration" / "iphone-03.yaml"
    assert manifest.advio is not None
    assert manifest.advio.fixpoints_csv_path == sequence_dir / "ground-truth" / "fixpoints.csv"
    assert manifest.advio.pose_refs.selected_pose_csv_path == sequence_dir / "pixel" / "arcore.csv"
    assert manifest.advio.T_cam_imu.tx == 0.01
    assert [reference.source.value for reference in benchmark_inputs.reference_trajectories] == [
        "ground_truth",
        "arcore",
        "arcore",
        "arkit",
        "arkit",
    ]
    assert benchmark_inputs.reference_trajectories[0].path == sequence_dir / "evaluation" / "ground_truth.tum"
    assert benchmark_inputs.reference_trajectories[1].path == sequence_dir / "evaluation" / "arcore.tum"
    assert benchmark_inputs.reference_trajectories[2].path == sequence_dir / "evaluation" / "arcore_aligned_to_gt.tum"
    assert benchmark_inputs.reference_trajectories[3].path == sequence_dir / "evaluation" / "arkit.tum"
    assert benchmark_inputs.reference_trajectories[4].path == sequence_dir / "evaluation" / "arkit_aligned_to_gt.tum"
    assert all(reference.path.exists() for reference in benchmark_inputs.reference_trajectories)
    assert [reference.coordinate_status for reference in benchmark_inputs.reference_trajectories] == [
        ReferenceCloudCoordinateStatus.SOURCE_NATIVE,
        ReferenceCloudCoordinateStatus.SOURCE_NATIVE,
        ReferenceCloudCoordinateStatus.ALIGNED,
        ReferenceCloudCoordinateStatus.SOURCE_NATIVE,
        ReferenceCloudCoordinateStatus.ALIGNED,
    ]
    assert benchmark_inputs.reference_trajectories[2].target_frame == "advio_gt_world"
    assert benchmark_inputs.reference_trajectories[4].target_frame == "advio_gt_world"
    assert benchmark_inputs.reference_clouds == []


def test_advio_benchmark_inputs_sanitize_optional_provider_trajectory(tmp_path: Path) -> None:
    sequence_dir = _write_advio_sequence(tmp_path)
    (sequence_dir / "pixel" / "arcore.csv").write_text(
        "\n".join(
            [
                "0.2,2.0,3.0,4.0,1.0,0.0,0.0,0.0",
                "0.0,1.0,2.0,3.0,1.0,0.0,0.0,0.0",
                "0.0,1.5,2.5,3.5,1.0,0.0,0.0,0.0",
                "0.1,1.5,2.5,3.5,1.0,0.0,0.0,0.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    benchmark_inputs = sequence.to_benchmark_inputs()

    assert [reference.source.value for reference in benchmark_inputs.reference_trajectories] == [
        "ground_truth",
        "arcore",
        "arcore",
        "arkit",
        "arkit",
    ]
    arcore_metadata = json.loads((sequence_dir / "evaluation" / "arcore.metadata.json").read_text(encoding="utf-8"))
    assert arcore_metadata["sanitization"]["dropped_duplicate_timestamps"] == 1
    assert arcore_metadata["sanitization"]["reordered_timestamps"] is True
    assert (sequence_dir / "evaluation" / "arcore_aligned_to_gt.tum").exists()
    arcore_aligned_metadata = json.loads(
        (sequence_dir / "evaluation" / "arcore_aligned_to_gt.metadata.json").read_text(encoding="utf-8")
    )
    assert arcore_aligned_metadata["coordinate_status"] == "aligned"
    assert arcore_aligned_metadata["target_frame"] == "advio_gt_world"
    assert arcore_aligned_metadata["alignment"]["matched_pairs"] >= 3


def test_advio_benchmark_inputs_project_near_so3_optional_provider_rotations(tmp_path: Path) -> None:
    sequence_dir = _write_advio_sequence(tmp_path)
    (sequence_dir / "iphone" / "arkit.csv").write_text(
        "\n".join(
            [
                "0.0,1.0,2.0,3.0,1.01,0.0,0.0,0.0",
                "0.1,1.5,2.5,3.5,1.01,0.0,0.0,0.0",
                "0.2,2.0,3.0,4.0,1.01,0.0,0.0,0.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    benchmark_inputs = sequence.to_benchmark_inputs()

    assert any(
        reference.source is ReferenceSource.ARKIT
        and reference.coordinate_status is ReferenceCloudCoordinateStatus.SOURCE_NATIVE
        for reference in benchmark_inputs.reference_trajectories
    )
    arkit_metadata = json.loads((sequence_dir / "evaluation" / "arkit.metadata.json").read_text())
    assert arkit_metadata["sanitization"]["normalized_quaternion_rows"] == 3
    assert (sequence_dir / "evaluation" / "arkit_aligned_to_gt.tum").exists()
    assert any(
        reference.source is ReferenceSource.ARKIT
        and reference.coordinate_status is ReferenceCloudCoordinateStatus.ALIGNED
        and reference.target_frame == "advio_gt_world"
        for reference in benchmark_inputs.reference_trajectories
    )


def test_advio_dataset_service_builds_normalization_materializer(tmp_path: Path) -> None:
    _write_advio_sequence(tmp_path / "advio")

    source = AdvioDatasetService(PathConfig(root=tmp_path, data_dir=tmp_path))._build_normalization_materializer(
        sequence_id=15,
        dataset_serving=AdvioServingConfig(pose_source=AdvioPoseSource.GROUND_TRUTH),
    )

    assert source is not None
    assert source.prepare_sequence_manifest(tmp_path / "manifest").sequence_id == "advio-15"
    assert not hasattr(source, "open_stream")
    benchmark_inputs = source.prepare_benchmark_inputs(tmp_path / "benchmark")
    assert benchmark_inputs.candidate_trajectories[0].path.exists()


def test_advio_source_config_requires_normalized_store_entry(tmp_path: Path) -> None:
    _write_advio_sequence(tmp_path / ".data" / "advio", sequence_id=15)
    source = AdvioSourceConfig(sequence_id="advio-15").setup_target(path_config=PathConfig(root=tmp_path))

    with pytest.raises(FileNotFoundError, match="prml-vslam dataset normalize --dataset advio"):
        source.prepare_sequence_manifest(tmp_path / "prepared")


def test_advio_normalized_entry_replays_display_oriented_observations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_advio_sequence(tmp_path / ".data" / "advio", sequence_id=15)
    monkeypatch.setattr(replay_video_module, "read_video_rotation_degrees", lambda path: 90)
    path_config = PathConfig(root=tmp_path)
    service = AdvioDatasetService(path_config)
    source_config = AdvioSourceConfig(sequence_id="advio-15")

    entry = normalize_dataset_entry(
        dataset_id=DatasetId.ADVIO,
        path_config=path_config,
        service=service,
        source_config=source_config,
    )
    benchmark_inputs = json.loads(entry.benchmark_inputs_path.read_text(encoding="utf-8"))
    sequence_manifest = json.loads(entry.sequence_manifest_path.read_text(encoding="utf-8"))
    observation_ref = benchmark_inputs["observation_sequences"][0]
    observation_index = ObservationSequenceIndex.model_validate_json(
        Path(observation_ref["index_path"]).read_text(encoding="utf-8")
    )

    stream = source_config.setup_target(path_config=path_config).open_stream(loop=False)
    stream.connect()
    packet = stream.wait_for_observation()
    stream.disconnect()

    assert observation_ref["raster_space"] == "display_downscaled"
    assert sequence_manifest.get("video_path") is None
    assert sequence_manifest["rgb_dir"] == (entry.root / "observations" / "rgb").as_posix()
    assert observation_index.raster_space == "display_downscaled"
    assert Path(observation_ref["payload_root"]).relative_to(entry.root).as_posix() == "observations"
    assert (entry.root / "observations" / "rgb").is_dir()
    assert not (entry.root / "observations" / "rgb.mp4").exists()
    assert json.loads((entry.root / "observations" / "rgb.metadata.json").read_text()) == {
        "dimension_multiple": 14,
        "raster_space": "display_downscaled",
        "rgb_max_width_px": 392,
        "source_raster_space": "display",
    }
    assert (
        benchmark_inputs["reference_trajectories"][0]["path"]
        == (entry.root / "benchmark" / "trajectories" / "ground_truth.tum").as_posix()
    )
    assert (
        benchmark_inputs["reference_trajectories"][1]["path"]
        == (entry.root / "benchmark" / "trajectories" / "arcore.tum").as_posix()
    )
    assert (
        benchmark_inputs["reference_trajectories"][2]["path"]
        == (entry.root / "benchmark" / "trajectories" / "arkit.tum").as_posix()
    )
    assert (
        benchmark_inputs["reference_trajectories"][3]["path"]
        == (entry.root / "benchmark" / "trajectories" / "arcore_aligned_to_gt.tum").as_posix()
    )
    assert [trajectory["path"] for trajectory in benchmark_inputs["candidate_trajectories"]] == [
        (entry.root / "benchmark" / "trajectories" / "arcore.tum").as_posix(),
        (entry.root / "benchmark" / "trajectories" / "arkit.tum").as_posix(),
    ]
    assert all("aligned_to_gt" not in trajectory["path"] for trajectory in benchmark_inputs["candidate_trajectories"])
    assert sequence_manifest["dataset_serving"]["pose_frame_mode"] == "fixedpoint_common_start_local"
    assert sequence_manifest["advio"]["pose_refs"] is None
    assert sequence_manifest["advio"]["fixpoints_csv_path"] is None
    assert not any(
        path.name in {"ground_truth_pose.csv", "arcore.csv", "arkit.csv", "selected_pose.csv", "fixpoints.csv"}
        for path in entry.root.rglob("*.csv")
    )
    source_native_frames = {
        "ground_truth": "advio_gt_world_rdf",
        "arcore": "advio_arcore_world_rdf",
        "arkit": "advio_arkit_world_rdf",
    }
    for trajectory_ref in benchmark_inputs["reference_trajectories"]:
        trajectory = load_tum_trajectory(Path(trajectory_ref["path"]))
        trajectory_metadata = json.loads(Path(trajectory_ref["metadata_path"]).read_text())
        assert trajectory_metadata["trajectory_origin"] == "advio_fixedpoint_common_start"
        assert trajectory_metadata["pose_normalization"] == "fixedpoint_common_start_local"
        if trajectory_ref["coordinate_status"] == "registered":
            assert np.allclose(trajectory.poses_se3[0], np.eye(4), atol=1e-9)
            assert trajectory_ref["target_frame"] == "advio_fixedpoint_common_start_local"
            assert trajectory_ref["native_frame"] == source_native_frames[trajectory_ref["source"]]
        else:
            assert trajectory_ref["target_frame"] == "advio_fixedpoint_common_start_local"
            assert trajectory_ref["native_frame"] == source_native_frames[trajectory_ref["source"]]
            assert trajectory_metadata["alignment"]["matched_pairs"] >= 3
    for trajectory_ref in benchmark_inputs["candidate_trajectories"]:
        trajectory = load_tum_trajectory(Path(trajectory_ref["path"]))
        assert np.allclose(trajectory.poses_se3[0], np.eye(4), atol=1e-9)
        assert trajectory_ref["coordinate_status"] == "registered"
    assert observation_index.rows[0].rgb_path == Path("rgb/000000.png")
    assert observation_index.world_frame == "advio_fixedpoint_common_start_local"
    assert observation_index.rows[0].T_world_camera is not None
    assert observation_index.rows[0].T_world_camera.tx == pytest.approx(0.0, abs=1e-9)
    assert (entry.root / "observations" / observation_index.rows[0].rgb_path).is_file()
    assert observation_index.rows[0].provenance.source_frame_index == 0
    assert observation_index.rows[0].provenance.raster_space == "display_downscaled"
    assert observation_index.rows[0].provenance.original_width == 48
    assert observation_index.rows[0].provenance.original_height == 64
    assert observation_index.rows[0].intrinsics is not None
    assert observation_index.rows[0].intrinsics.width_px == 42
    assert observation_index.rows[0].intrinsics.height_px == 56
    assert packet.rgb is not None
    assert packet.rgb.shape == (56, 42, 3)
    assert packet.intrinsics is not None
    assert packet.intrinsics.width_px == 42
    assert packet.intrinsics.height_px == 56
    assert packet.source_frame_index == 0
    assert packet.provenance.source_frame_index == 0
    assert packet.T_world_camera is not None
    assert packet.T_world_camera.tx == pytest.approx(0.0, abs=1e-9)


def test_advio_normalized_entry_rejects_raw_sidecars_under_entry_root(tmp_path: Path) -> None:
    _write_advio_sequence(tmp_path / ".data" / "advio", sequence_id=15)
    path_config = PathConfig(root=tmp_path)
    service = AdvioDatasetService(path_config)
    source_config = AdvioSourceConfig(sequence_id="advio-15")
    entry = normalize_dataset_entry(
        dataset_id=DatasetId.ADVIO,
        path_config=path_config,
        service=service,
        source_config=source_config,
    )
    profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.ADVIO,
        sequence_id="advio-15",
        source_id=source_config.source_id,
        payload=source_config.model_dump(mode="json"),
    )
    rogue_sidecar = entry.root / "input" / "advio" / "arcore.csv"
    rogue_sidecar.parent.mkdir(parents=True, exist_ok=True)
    rogue_sidecar.write_text("0.0,1.0,2.0,3.0,1.0,0.0,0.0,0.0\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="must not persist raw pose or fixpoint sidecars"):
        normalized_store_for_path_config(DatasetId.ADVIO, path_config).load_entry(profile)


def test_advio_normalization_target_fps_changes_profile_and_observation_count(tmp_path: Path) -> None:
    _write_advio_sequence(tmp_path / ".data" / "advio", sequence_id=15)
    path_config = PathConfig(root=tmp_path)
    service = AdvioDatasetService(path_config)
    full_config = AdvioSourceConfig(sequence_id="advio-15")
    sampled_config = AdvioSourceConfig(sequence_id="advio-15", target_fps=5.0)

    full_entry = normalize_dataset_entry(
        dataset_id=DatasetId.ADVIO,
        path_config=path_config,
        service=service,
        source_config=full_config,
    )
    sampled_entry = normalize_dataset_entry(
        dataset_id=DatasetId.ADVIO,
        path_config=path_config,
        service=service,
        source_config=sampled_config,
    )
    sampled_inputs = json.loads(sampled_entry.benchmark_inputs_path.read_text(encoding="utf-8"))
    sampled_index = ObservationSequenceIndex.model_validate_json(
        Path(sampled_inputs["observation_sequences"][0]["index_path"]).read_text(encoding="utf-8")
    )

    assert sampled_entry.profile_key != full_entry.profile_key
    assert sampled_index.observation_count == 2
    assert [row.provenance.source_frame_index for row in sampled_index.rows] == [0, 2]


def test_advio_normalized_store_rejects_sampling_profile_mismatch(tmp_path: Path) -> None:
    _write_advio_sequence(tmp_path / ".data" / "advio", sequence_id=15)
    path_config = PathConfig(root=tmp_path)
    service = AdvioDatasetService(path_config)
    source_config = AdvioSourceConfig(sequence_id="advio-15", target_fps=5.0)
    normalize_dataset_entry(
        dataset_id=DatasetId.ADVIO,
        path_config=path_config,
        service=service,
        source_config=source_config,
    )
    requested_profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.ADVIO,
        sequence_id="advio-15",
        source_id=source_config.source_id,
        payload=source_config.model_copy(update={"target_fps": None}).model_dump(mode="json"),
    )

    with pytest.raises(FileNotFoundError):
        normalized_store_for_path_config(DatasetId.ADVIO, path_config).load_entry_for_runtime(requested_profile)


def test_advio_profile_convention_rejects_missing_convention_entries(tmp_path: Path) -> None:
    _write_advio_sequence(tmp_path / ".data" / "advio", sequence_id=15)
    path_config = PathConfig(root=tmp_path)
    service = AdvioDatasetService(path_config)
    source_config = AdvioSourceConfig(sequence_id="advio-15")
    legacy_profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.ADVIO,
        sequence_id="advio-15",
        source_id=source_config.source_id,
        payload=source_config.model_dump(mode="json"),
    )
    legacy_profile = NormalizedDatasetProfile(
        dataset_id=legacy_profile.dataset_id,
        sequence_id=legacy_profile.sequence_id,
        source_id=legacy_profile.source_id,
        source_profile={
            key: value for key, value in legacy_profile.source_profile.items() if key != "trajectory_convention"
        },
    )
    store = normalized_store_for_path_config(DatasetId.ADVIO, path_config)
    legacy_entry = store.create_entry_from_source(
        profile=legacy_profile,
        source=service._build_normalization_materializer(
            sequence_id=15,
            frame_selection=source_config,
            dataset_serving=source_config.dataset_serving,
            rgb_max_width_px=source_config.rgb_max_width_px,
            rgb_dimension_multiple=source_config.rgb_dimension_multiple,
        ),
    )
    current_profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.ADVIO,
        sequence_id="advio-15",
        source_id=source_config.source_id,
        payload=source_config.model_dump(mode="json"),
    )

    assert legacy_entry.root.exists()
    assert current_profile.profile_key != legacy_profile.profile_key
    assert (
        current_profile.source_profile["trajectory_convention"] == ADVIO_FIXEDPOINT_COMMON_START_TRAJECTORY_CONVENTION
    )
    with pytest.raises(FileNotFoundError):
        store.load_entry_for_runtime(current_profile)
    with pytest.raises(RuntimeError, match="fixedpoint common-start"):
        store.load_entry_by_key_for_runtime(sequence_id="advio-15", profile_key=legacy_profile.profile_key)
    with pytest.raises(FileNotFoundError):
        source_config.setup_target(path_config=path_config).prepare_sequence_manifest(tmp_path / "runtime")

    query = query_normalized_dataset(DatasetId.ADVIO, path_config)
    assert query.records == []


def test_advio_profile_convention_rejects_legacy_local_first_pose_convention_by_key(
    tmp_path: Path,
) -> None:
    _write_advio_sequence(tmp_path / ".data" / "advio", sequence_id=15)
    path_config = PathConfig(root=tmp_path)
    service = AdvioDatasetService(path_config)
    source_config = AdvioSourceConfig(sequence_id="advio-15")
    current_profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.ADVIO,
        sequence_id="advio-15",
        source_id=source_config.source_id,
        payload=source_config.model_dump(mode="json"),
    )
    legacy_profile = NormalizedDatasetProfile(
        dataset_id=current_profile.dataset_id,
        sequence_id=current_profile.sequence_id,
        source_id=current_profile.source_id,
        source_profile=current_profile.source_profile.as_dict()
        | {"trajectory_convention": ADVIO_LOCAL_FIRST_POSE_TRAJECTORY_CONVENTION},
    )
    store = normalized_store_for_path_config(DatasetId.ADVIO, path_config)
    legacy_entry = store.create_entry_from_source(
        profile=legacy_profile,
        source=service._build_normalization_materializer(
            sequence_id=15,
            frame_selection=source_config,
            dataset_serving=source_config.dataset_serving,
            rgb_max_width_px=source_config.rgb_max_width_px,
            rgb_dimension_multiple=source_config.rgb_dimension_multiple,
        ),
    )
    benchmark_payload = json.loads(legacy_entry.benchmark_inputs_path.read_text(encoding="utf-8"))
    for collection in ("reference_trajectories", "candidate_trajectories"):
        for trajectory in benchmark_payload[collection]:
            if trajectory["coordinate_status"] == "source_native":
                trajectory["coordinate_status"] = "registered"
    legacy_entry.benchmark_inputs_path.write_text(json.dumps(benchmark_payload), encoding="utf-8")

    assert current_profile.profile_key != legacy_profile.profile_key
    with pytest.raises(FileNotFoundError):
        store.load_entry_for_runtime(current_profile)
    with pytest.raises(RuntimeError, match="fixedpoint common-start"):
        store.load_entry_by_key_for_runtime(sequence_id="advio-15", profile_key=legacy_entry.profile_key)


def test_advio_local_first_pose_mode_rebases_provider_poses(tmp_path: Path) -> None:
    sequence_dir = _write_advio_sequence(tmp_path)
    _write_pose_csv_rows(
        sequence_dir / "pixel" / "arcore.csv",
        rows=((0.0, 10.0, 20.0, 30.0), (0.1, 10.5, 20.5, 30.5), (0.2, 11.0, 21.0, 31.0)),
    )
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    provider_world = sequence.open_stream(
        dataset_serving=AdvioServingConfig(
            pose_source=AdvioPoseSource.ARCORE,
            pose_frame_mode=AdvioPoseFrameMode.PROVIDER_WORLD,
        ),
        loop=False,
        replay_mode=ReplayMode.FAST_AS_POSSIBLE,
    )
    local_first = sequence.open_stream(
        dataset_serving=AdvioServingConfig(
            pose_source=AdvioPoseSource.ARCORE,
            pose_frame_mode=AdvioPoseFrameMode.LOCAL_FIRST_POSE,
        ),
        loop=False,
        replay_mode=ReplayMode.FAST_AS_POSSIBLE,
    )

    provider_world.connect()
    provider_packet = provider_world.wait_for_observation()
    provider_world.disconnect()
    local_first.connect()
    local_packet = local_first.wait_for_observation()
    local_first.disconnect()

    assert provider_packet.T_world_camera is not None
    assert local_packet.T_world_camera is not None
    assert [
        provider_packet.T_world_camera.tx,
        provider_packet.T_world_camera.ty,
        provider_packet.T_world_camera.tz,
    ] == [30.0, -20.0, 10.0]
    assert local_packet.T_world_camera.tx == pytest.approx(0.0, abs=1e-6)


def test_list_advio_sequence_ids_supports_nested_data_layout(tmp_path: Path) -> None:
    _write_advio_sequence(tmp_path, sequence_id=7, nested_layout=True)
    _write_advio_sequence(tmp_path, sequence_id=15)

    assert list_local_sequence_ids(tmp_path) == [7, 15]


def test_resolve_existing_advio_reference_tum_only_uses_existing_tum(tmp_path: Path) -> None:
    dataset_root = tmp_path / ".data" / "advio"
    _write_advio_sequence(dataset_root, sequence_id=15)
    reference_path = resolve_existing_reference_tum(dataset_root, "advio-15")

    assert reference_path is None


def test_resolve_existing_advio_reference_tum_finds_ground_truth(tmp_path: Path) -> None:
    dataset_root = tmp_path / ".data" / "advio"
    sequence_dir = _write_advio_sequence(dataset_root, sequence_id=15)
    reference_path = sequence_dir / "ground-truth" / "ground_truth.tum"
    reference_path.write_text("0.0 0 0 0 0 0 0 1\n", encoding="utf-8")
    assert resolve_existing_reference_tum(dataset_root, "advio-15") == reference_path


def test_advio_dataset_service_downloads_full_scene_from_cached_archive(tmp_path: Path) -> None:
    catalog = _build_fake_catalog(tmp_path)
    service = AdvioDatasetService(PathConfig(root=tmp_path), catalog=catalog)
    request = AdvioDownloadRequest(sequence_ids=[15])

    first_result = service.download(request)
    second_result = service.download(request)

    dataset_root = tmp_path / ".data" / "advio"
    archive_path = dataset_root / ".archives" / "advio-15.zip"
    assert first_result.downloaded_archive_count == 1
    assert first_result.reused_archive_count == 0
    assert second_result.downloaded_archive_count == 0
    assert second_result.reused_archive_count == 1
    assert archive_path.exists()
    assert (dataset_root / "calibration" / "iphone-03.yaml").exists()
    assert (dataset_root / "data" / "advio-15" / "iphone" / "frames.mov").exists()
    assert (dataset_root / "data" / "advio-15" / "iphone" / "frames.csv").exists()
    assert (dataset_root / "data" / "advio-15" / "pixel" / "arcore.csv").exists()

    status = service.local_scene_statuses()[0]
    assert status.archive_path == archive_path
    assert status.arcore_ready is True
    assert status.arkit_ready is True
    assert status.replay_ready is True
    assert status.offline_ready is True


def test_advio_dataset_service_extracts_complete_ground_truth_files(tmp_path: Path) -> None:
    catalog = _build_fake_catalog(tmp_path)
    service = AdvioDatasetService(PathConfig(root=tmp_path), catalog=catalog)

    result = service.download(AdvioDownloadRequest(sequence_ids=[15]))

    dataset_root = tmp_path / ".data" / "advio"
    ground_truth_dir = dataset_root / "data" / "advio-15" / "ground-truth"

    assert result.downloaded_archive_count == 1
    assert (ground_truth_dir / "poses.csv").exists()
    assert (ground_truth_dir / "fixpoints.csv").exists()
    assert service.local_scene_statuses()[0].offline_ready is True


def test_advio_ground_truth_modality_requires_fixpoints_csv(tmp_path: Path) -> None:
    catalog = _build_fake_catalog(tmp_path)
    dataset_root = tmp_path / ".data" / "advio"
    sequence_dir = _write_advio_sequence(dataset_root, sequence_id=15)
    (sequence_dir / "ground-truth" / "fixpoints.csv").unlink()
    service = AdvioDatasetService(PathConfig(root=tmp_path), catalog=catalog)

    status = service.local_scene_statuses()[0]

    assert status.replay_ready is False
    assert status.offline_ready is False


def test_advio_dataset_service_full_scene_downloads_evaluation_ready_bundle(tmp_path: Path) -> None:
    catalog = _build_fake_catalog(tmp_path)
    service = AdvioDatasetService(PathConfig(root=tmp_path), catalog=catalog)

    result = service.download(AdvioDownloadRequest(sequence_ids=[15]))

    assert result.downloaded_archive_count == 1
    summary = service.summarize()
    status = service.local_scene_statuses()[0]

    assert summary.total_scene_count == 1
    assert summary.local_scene_count == 1
    assert summary.offline_ready_scene_count == 1
    assert status.replay_ready is True
    assert status.offline_ready is True


def test_advio_dataset_service_refreshes_corrupted_cached_archive(tmp_path: Path) -> None:
    catalog = _build_fake_catalog(tmp_path)
    service = AdvioDatasetService(PathConfig(root=tmp_path), catalog=catalog)
    request = AdvioDownloadRequest(sequence_ids=[15])

    service.download(request)
    archive_path = tmp_path / ".data" / "advio" / ".archives" / "advio-15.zip"
    archive_path.write_bytes(b"corrupted")

    result = service.download(request)

    assert result.downloaded_archive_count == 1
    assert result.reused_archive_count == 0
    assert archive_path.stat().st_size == catalog.scenes[0].archive_size_bytes


def test_advio_dataset_service_summarize_reuses_precomputed_statuses(tmp_path: Path) -> None:
    catalog = _build_fake_catalog(tmp_path)
    service = AdvioDatasetService(PathConfig(root=tmp_path), catalog=catalog)
    statuses = service.local_scene_statuses()
    service.local_scene_statuses = lambda: pytest.fail("local_scene_statuses should not be recomputed")  # type: ignore[method-assign]

    summary = service.summarize(statuses)

    assert summary.total_scene_count == 1
    assert summary.local_scene_count == 0
    assert summary.offline_ready_scene_count == 0


def test_advio_dataset_service_handles_official_archive_layout(tmp_path: Path) -> None:
    scene_slug = "advio-15"
    archive_path = tmp_path / "upstream" / f"{scene_slug}.zip"
    source_root = tmp_path / "upstream" / "scene-root"
    _write_advio_sequence(source_root / "data", sequence_id=15, official_archive_names=True)
    _write_advio_archive(source_root, archive_path, include_directory_entries=True)

    calibration_source_dir = tmp_path / "upstream" / "calibration"
    _write_calibration(calibration_source_dir / "iphone-03.yaml")

    import hashlib

    digest = hashlib.md5(archive_path.read_bytes()).hexdigest()
    catalog = AdvioCatalog(
        dataset_id="advio",
        dataset_label="ADVIO",
        upstream=AdvioUpstreamMetadata(
            repo_url="https://github.com/AaltoVision/ADVIO",
            zenodo_record_url="https://zenodo.org/records/1476931",
            doi="10.5281/zenodo.1320824",
            license="CC BY-NC 4.0",
            calibration_base_url=calibration_source_dir.as_uri() + "/",
        ),
        scenes=[
            AdvioSceneMetadata(
                sequence_id=15,
                sequence_slug=scene_slug,
                venue="Office",
                dataset_code="03",
                environment=AdvioEnvironment.INDOOR,
                has_stairs=False,
                has_escalator=False,
                has_elevator=False,
                people_level=AdvioPeopleLevel.NONE,
                has_vehicles=False,
                calibration_name="iphone-03.yaml",
                archive_url=archive_path.as_uri(),
                archive_size_bytes=archive_path.stat().st_size,
                archive_md5=digest,
            )
        ],
    )
    service = AdvioDatasetService(PathConfig(root=tmp_path), catalog=catalog)

    service.download(AdvioDownloadRequest(sequence_ids=[15]))

    status = service.local_scene_statuses()[0]
    ground_truth_dir = tmp_path / ".data" / "advio" / "data" / "advio-15" / "ground-truth"

    assert status.offline_ready is True
    assert (ground_truth_dir / "pose.csv").exists()
    assert (ground_truth_dir / "fixpoints.csv").exists()
    assert service.list_local_sequence_ids() == [15]
    assert service.load_local_sample(15).sequence_name == "advio-15"


def test_advio_dataset_service_lists_and_loads_local_sequences(tmp_path: Path) -> None:
    dataset_root = tmp_path / ".data" / "advio"
    _write_advio_sequence(dataset_root, sequence_id=15)
    service = AdvioDatasetService(PathConfig(root=tmp_path))

    assert service.list_local_sequence_ids() == [15]

    sample = service.load_local_sample(15)

    assert sample.sequence_id == 15
    assert sample.sequence_name == "advio-15"
    assert sample.frame_timestamps_ns.tolist() == [0, 100_000_000, 200_000_000]
