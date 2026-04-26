"""Tests for the simplified ADVIO adapter and replay stream."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import cv2
import numpy as np
import pytest

import prml_vslam.sources.replay.video as replay_video_module
from prml_vslam.sources.contracts import ReferenceCloudCoordinateStatus, ReferenceCloudSource
from prml_vslam.sources.datasets.advio import (
    AdvioCatalog,
    AdvioDatasetService,
    AdvioDownloadPreset,
    AdvioDownloadRequest,
    AdvioEnvironment,
    AdvioModality,
    AdvioPeopleLevel,
    AdvioPoseFrameMode,
    AdvioPoseSource,
    AdvioSceneMetadata,
    AdvioSequence,
    AdvioSequenceConfig,
    AdvioServingConfig,
    AdvioStreamingSourceConfig,
    AdvioUpstreamMetadata,
)
from prml_vslam.sources.datasets.advio.advio_frames import (
    APPLE_Y_UP_TO_RDF,
    TANGO_Z_UP_TO_RDF,
    transform_advio_points_to_rdf,
    transform_advio_trajectory_to_rdf,
)
from prml_vslam.sources.datasets.advio.advio_layout import list_local_sequence_ids, resolve_existing_reference_tum
from prml_vslam.sources.datasets.advio.advio_loading import (
    _read_numeric_csv,
    load_advio_calibration,
    load_advio_trajectory,
)
from prml_vslam.sources.replay import PyAvVideoObservationSource, ReplayMode
from prml_vslam.utils import PathConfig


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
    apple_points = transform_advio_points_to_rdf(
        np.array([[1.0, 2.0, 3.0]], dtype=np.float64),
        AdvioPoseSource.ARKIT,
    )
    tango_points = transform_advio_points_to_rdf(
        np.array([[1.0, 2.0, 3.0]], dtype=np.float64),
        ReferenceCloudSource.TANGO_AREA_LEARNING,
    )

    assert np.array_equal(APPLE_Y_UP_TO_RDF, np.diag([1.0, -1.0, 1.0]))
    assert np.array_equal(TANGO_Z_UP_TO_RDF @ np.array([1.0, 2.0, 3.0]), np.array([1.0, -3.0, 2.0]))
    assert np.array_equal(apple_points, np.array([[1.0, -2.0, 3.0]]))
    assert np.array_equal(tango_points, np.array([[1.0, -3.0, 2.0]]))

    pose_csv = tmp_path / "arkit.csv"
    _write_pose_csv_rows(pose_csv, rows=((0.0, 1.0, 2.0, 3.0), (0.1, 1.5, 2.5, 3.5), (0.2, 2.0, 3.0, 4.0)))
    trajectory = transform_advio_trajectory_to_rdf(
        load_advio_trajectory(pose_csv),
        AdvioPoseSource.ARKIT,
    )
    assert np.allclose(trajectory.positions_xyz[0], np.array([1.0, -2.0, 3.0]))


def _write_pose_csv_rows(path: Path, *, rows: tuple[tuple[float, float, float, float], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(f"{t},{x},{y},{z},1.0,0.0,0.0,0.0" for t, x, y, z in rows) + "\n",
        encoding="utf-8",
    )


def _write_tango_point_cloud_payload(path: Path, *, depth_offset: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"0.0,0.0,{1.0 + depth_offset:.3f}",
                f"0.1,0.0,{1.1 + depth_offset:.3f}",
                f"0.0,0.1,{1.2 + depth_offset:.3f}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_fixpoints_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("0.0,1.0,2.0,3.0\n0.2,2.0,3.0,4.0\n", encoding="utf-8")


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
    (sequence_dir / "tango").mkdir(parents=True, exist_ok=True)

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
    _write_pose_csv(sequence_dir / "tango" / "raw.csv")
    _write_pose_csv(sequence_dir / "tango" / "area-learning.csv")
    (sequence_dir / "tango" / "point-cloud.csv").write_text(
        "0.0,1\n0.1,2\n0.2,3\n",
        encoding="utf-8",
    )
    _write_tango_point_cloud_payload(sequence_dir / "tango" / "point-cloud-00001.csv", depth_offset=0.0)
    _write_tango_point_cloud_payload(sequence_dir / "tango" / "point-cloud-00002.csv", depth_offset=0.1)
    _write_tango_point_cloud_payload(sequence_dir / "tango" / "point-cloud-00003.csv", depth_offset=0.2)
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
    assert packet_0.T_world_camera.tx == 1.0
    assert packet_2.T_world_camera is not None
    assert packet_2.T_world_camera.tz == 4.0
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
    assert packet.T_world_camera.tx == 1.0


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
            pose_frame_mode=AdvioPoseFrameMode.REFERENCE_WORLD,
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
    assert manifest.advio.pose_refs.tango_raw_csv_path == sequence_dir / "tango" / "raw.csv"
    assert manifest.advio.pose_refs.tango_area_learning_csv_path == sequence_dir / "tango" / "area-learning.csv"
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
    assert benchmark_inputs.reference_trajectories[0].path.exists()
    assert benchmark_inputs.reference_trajectories[1].path.exists()
    assert benchmark_inputs.reference_trajectories[2].path.exists()
    assert benchmark_inputs.reference_trajectories[2].coordinate_status is ReferenceCloudCoordinateStatus.ALIGNED
    assert [reference.source.value for reference in benchmark_inputs.reference_point_cloud_sequences] == [
        "tango_area_learning",
        "tango_area_learning",
    ]
    assert [reference.source.value for reference in benchmark_inputs.reference_clouds] == [
        "tango_area_learning",
        "tango_area_learning",
    ]
    assert benchmark_inputs.reference_point_cloud_sequences[0].trajectory_path.exists()
    assert benchmark_inputs.reference_clouds[0].path.exists()
    cloud_metadata = benchmark_inputs.reference_clouds[0].metadata_path.read_text(encoding="utf-8")
    assert '"point_count": 9' in cloud_metadata
    assert '"point_stride": 1' in cloud_metadata
    assert '"skipped_out_of_range_payloads": 0' in cloud_metadata


def test_advio_tango_reference_clouds_skip_out_of_range_payloads(tmp_path: Path) -> None:
    sequence_dir = _write_advio_sequence(tmp_path)
    _write_pose_csv_rows(
        sequence_dir / "tango" / "area-learning.csv",
        rows=((0.0, 1.0, 2.0, 3.0), (0.1, 1.5, 2.5, 3.5)),
    )
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    benchmark_inputs = sequence.to_benchmark_inputs()

    area_learning_native = next(
        reference
        for reference in benchmark_inputs.reference_clouds
        if reference.source is ReferenceCloudSource.TANGO_AREA_LEARNING
        and reference.coordinate_status is ReferenceCloudCoordinateStatus.SOURCE_NATIVE
    )
    metadata = area_learning_native.metadata_path.read_text(encoding="utf-8")
    assert '"point_count": 6' in metadata
    assert '"payloads_used": 2' in metadata
    assert '"skipped_out_of_range_payloads": 1' in metadata


def test_advio_benchmark_inputs_skip_invalid_optional_provider_trajectory(tmp_path: Path) -> None:
    sequence_dir = _write_advio_sequence(tmp_path)
    _write_pose_csv_rows(
        sequence_dir / "pixel" / "arcore.csv",
        rows=((0.0, 1.0, 2.0, 3.0), (0.0, 1.5, 2.5, 3.5), (0.2, 2.0, 3.0, 4.0)),
    )
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    benchmark_inputs = sequence.to_benchmark_inputs()

    assert [reference.source.value for reference in benchmark_inputs.reference_trajectories] == [
        "ground_truth",
        "arkit",
        "arkit",
    ]
    assert not (sequence_dir / "evaluation" / "arcore.tum").exists()


def test_advio_benchmark_inputs_skip_invalid_optional_tango_cloud_trajectory(tmp_path: Path) -> None:
    sequence_dir = _write_advio_sequence(tmp_path)
    _write_pose_csv_rows(
        sequence_dir / "tango" / "area-learning.csv",
        rows=((0.0, 1.0, 2.0, 3.0), (0.0, 1.5, 2.5, 3.5), (0.2, 2.0, 3.0, 4.0)),
    )
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    benchmark_inputs = sequence.to_benchmark_inputs()

    assert not benchmark_inputs.reference_clouds
    assert not benchmark_inputs.reference_point_cloud_sequences
    assert not (sequence_dir / "evaluation" / "tango_area_learning.tum").exists()


def test_advio_streaming_source_config_rehydrates_process_source(tmp_path: Path) -> None:
    _write_advio_sequence(tmp_path)

    source = AdvioStreamingSourceConfig(
        dataset_root=tmp_path,
        sequence_id=15,
        dataset_serving=AdvioServingConfig(pose_source=AdvioPoseSource.GROUND_TRUTH),
        frame_stride=1,
    ).setup_target()

    assert source is not None
    assert source.prepare_sequence_manifest(tmp_path / "manifest").sequence_id == "advio-15"
    stream = source.open_stream(loop=False)
    stream.connect()
    packet = stream.wait_for_observation()
    stream.disconnect()
    assert packet.T_world_camera is not None
    assert packet.T_world_camera.tx == 1.0


def test_advio_open_stream_supports_tango_raw_provider_and_point_cloud_payload(tmp_path: Path) -> None:
    _write_advio_sequence(tmp_path)
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    stream = sequence.open_stream(
        dataset_serving=AdvioServingConfig(pose_source=AdvioPoseSource.TANGO_RAW),
        loop=False,
        replay_mode=ReplayMode.FAST_AS_POSSIBLE,
    )

    stream.connect()
    packet = stream.wait_for_observation()
    stream.disconnect()

    assert packet.T_world_camera is not None
    assert packet.pointmap_xyz is None
    assert packet.point_cloud_xyz is None
    assert packet.provenance.pose_source == AdvioPoseSource.TANGO_RAW.value


def test_advio_reference_world_and_local_first_pose_modes_transform_provider_poses(tmp_path: Path) -> None:
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
    reference_world = sequence.open_stream(
        dataset_serving=AdvioServingConfig(
            pose_source=AdvioPoseSource.ARCORE,
            pose_frame_mode=AdvioPoseFrameMode.REFERENCE_WORLD,
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
    reference_world.connect()
    reference_packet = reference_world.wait_for_observation()
    reference_world.disconnect()

    assert provider_packet.T_world_camera is not None
    assert local_packet.T_world_camera is not None
    assert reference_packet.T_world_camera is not None
    assert provider_packet.T_world_camera.tx == 10.0
    assert local_packet.T_world_camera.tx == pytest.approx(0.0, abs=1e-6)
    assert reference_packet.T_world_camera.tx == pytest.approx(1.0, abs=1e-3)


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


def test_advio_dataset_service_downloads_selected_modalities_from_cached_archive(tmp_path: Path) -> None:
    catalog = _build_fake_catalog(tmp_path)
    service = AdvioDatasetService(PathConfig(root=tmp_path), catalog=catalog)
    request = AdvioDownloadRequest(
        sequence_ids=[15],
        modalities=[AdvioModality.CALIBRATION, AdvioModality.IPHONE_VIDEO],
    )

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
    assert not (dataset_root / "data" / "advio-15" / "pixel" / "arcore.csv").exists()

    status = service.local_scene_statuses()[0]
    assert status.archive_path == archive_path
    assert status.local_modalities == [AdvioModality.CALIBRATION, AdvioModality.IPHONE_VIDEO]
    assert status.replay_ready is False
    assert status.offline_ready is False


def test_advio_dataset_service_extracts_complete_ground_truth_bundle(tmp_path: Path) -> None:
    catalog = _build_fake_catalog(tmp_path)
    service = AdvioDatasetService(PathConfig(root=tmp_path), catalog=catalog)

    result = service.download(
        AdvioDownloadRequest(
            sequence_ids=[15],
            modalities=[AdvioModality.GROUND_TRUTH],
        )
    )

    dataset_root = tmp_path / ".data" / "advio"
    ground_truth_dir = dataset_root / "data" / "advio-15" / "ground-truth"

    assert result.downloaded_archive_count == 1
    assert (ground_truth_dir / "poses.csv").exists()
    assert (ground_truth_dir / "fixpoints.csv").exists()
    assert service.local_scene_statuses()[0].local_modalities == [AdvioModality.GROUND_TRUTH]


def test_advio_ground_truth_modality_requires_fixpoints_csv(tmp_path: Path) -> None:
    catalog = _build_fake_catalog(tmp_path)
    dataset_root = tmp_path / ".data" / "advio"
    sequence_dir = _write_advio_sequence(dataset_root, sequence_id=15)
    (sequence_dir / "ground-truth" / "fixpoints.csv").unlink()
    service = AdvioDatasetService(PathConfig(root=tmp_path), catalog=catalog)

    status = service.local_scene_statuses()[0]

    assert AdvioModality.GROUND_TRUTH not in status.local_modalities
    assert status.replay_ready is False
    assert status.offline_ready is False


def test_advio_dataset_service_offline_preset_downloads_evaluation_ready_bundle(tmp_path: Path) -> None:
    catalog = _build_fake_catalog(tmp_path)
    service = AdvioDatasetService(PathConfig(root=tmp_path), catalog=catalog)

    result = service.download(
        AdvioDownloadRequest(
            sequence_ids=[15],
            preset=AdvioDownloadPreset.OFFLINE,
        )
    )

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
    request = AdvioDownloadRequest(
        sequence_ids=[15],
        modalities=[AdvioModality.CALIBRATION, AdvioModality.IPHONE_VIDEO],
    )

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

    service.download(AdvioDownloadRequest(sequence_ids=[15], preset=AdvioDownloadPreset.OFFLINE))

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
