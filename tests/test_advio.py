"""Tests for the simplified ADVIO adapter and replay stream."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import cv2
import numpy as np
import pytest

import prml_vslam.datasets.advio.advio_replay_adapter as advio_replay_module
from prml_vslam.datasets.advio import (
    AdvioCatalog,
    AdvioDatasetService,
    AdvioDownloadPreset,
    AdvioDownloadRequest,
    AdvioEnvironment,
    AdvioModality,
    AdvioPeopleLevel,
    AdvioPoseSource,
    AdvioSceneMetadata,
    AdvioSequence,
    AdvioSequenceConfig,
    AdvioUpstreamMetadata,
    list_advio_sequence_ids,
    load_advio_sequence,
)
from prml_vslam.datasets.advio.advio_layout import resolve_existing_reference_tum
from prml_vslam.io import Cv2FrameProducer, Cv2ReplayMode
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "0.0,1.0,2.0,3.0,1.0,0.0,0.0,0.0\n0.1,1.5,2.5,3.5,1.0,0.0,0.0,0.0\n0.2,2.0,3.0,4.0,1.0,0.0,0.0,0.0\n",
        encoding="utf-8",
    )


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

    sample = load_advio_sequence(AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    assert sample.sequence_name == "advio-15"
    assert sample.paths.video_path == sequence_dir / "iphone" / "frames.mov"
    assert sample.frame_timestamps_ns.tolist() == [0, 100_000_000, 200_000_000]
    assert sample.calibration.intrinsics.width_px == 64
    assert sample.calibration.intrinsics.height_px == 48
    assert sample.ground_truth.positions_xyz.shape == (3, 3)
    assert sample.ground_truth.quaternions_xyzw[0].tolist() == [0.0, 0.0, 0.0, 1.0]
    assert sample.arcore.positions_xyz[2].tolist() == [2.0, 3.0, 4.0]
    assert sample.duration_s == 0.2


def test_advio_sequence_uses_catalog_calibration_metadata(tmp_path: Path) -> None:
    dataset_root = tmp_path / "data" / "advio"
    _write_advio_sequence(dataset_root)
    _write_calibration(dataset_root / "calibration" / "iphone-custom.yaml")
    catalog = _build_fake_catalog(tmp_path)
    catalog.scenes[0].calibration_name = "iphone-custom.yaml"

    sample = AdvioDatasetService(PathConfig(root=tmp_path), catalog=catalog).load_local_sample(15)

    assert sample.paths.calibration_path == tmp_path / "data" / "advio" / "calibration" / "iphone-custom.yaml"


def test_advio_open_stream_loops_through_sample_with_cv2_producer(tmp_path: Path) -> None:
    _write_advio_sequence(tmp_path)
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    stream = sequence.open_stream(
        pose_source=AdvioPoseSource.GROUND_TRUTH,
        loop=True,
        replay_mode=Cv2ReplayMode.FAST_AS_POSSIBLE,
    )

    assert isinstance(stream, Cv2FrameProducer)
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
    assert packet_0.timestamp_ns == 0
    assert packet_1.timestamp_ns == 100_000_000
    assert packet_0.intrinsics is not None
    assert packet_0.pose is not None
    assert packet_0.pose.tx == 1.0
    assert packet_2.pose is not None
    assert packet_2.pose.tz == 4.0
    assert packet_3.metadata["loop_index"] == 1
    assert packet_0.metadata["dataset"] == "ADVIO"
    assert packet_0.metadata["pose_source"] == AdvioPoseSource.GROUND_TRUTH.value


def test_advio_open_stream_supports_replay_ready_bundle_without_arcore(tmp_path: Path) -> None:
    sequence_dir = _write_advio_sequence(tmp_path)
    (sequence_dir / "pixel" / "arcore.csv").unlink()
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    stream = sequence.open_stream(
        pose_source=AdvioPoseSource.GROUND_TRUTH,
        loop=True,
        replay_mode=Cv2ReplayMode.FAST_AS_POSSIBLE,
    )

    stream.connect()
    packet = stream.wait_for_packet()
    stream.disconnect()

    assert packet.seq == 0
    assert packet.pose is not None
    assert packet.pose.tx == 1.0


def test_advio_open_stream_rotation_opt_in_keeps_default_behavior_without_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_advio_sequence(tmp_path)
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    class _Container:
        streams = type("_Streams", (), {"video": [type("_Stream", (), {"metadata": {}})()]})()

        def __enter__(self) -> _Container:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def decode(self, *, video: int) -> list[object]:
            del video
            return []

    class _Av:
        @staticmethod
        def open(path: str) -> _Container:
            del path
            return _Container()

    monkeypatch.setattr(advio_replay_module, "_load_pyav", lambda: _Av())

    stream = sequence.open_stream(replay_mode=Cv2ReplayMode.FAST_AS_POSSIBLE, respect_video_rotation=True)

    assert isinstance(stream, Cv2FrameProducer)


def test_advio_open_stream_rotation_opt_in_rotates_packets_and_intrinsics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_advio_sequence(tmp_path)
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))
    monkeypatch.setattr(advio_replay_module, "read_advio_video_rotation_degrees", lambda path: 90)

    stream = sequence.open_stream(replay_mode=Cv2ReplayMode.FAST_AS_POSSIBLE, respect_video_rotation=True)
    stream.connect()
    packet = stream.wait_for_packet()
    stream.disconnect()

    assert packet.rgb.shape == (64, 48, 3)
    assert packet.metadata["video_rotation_degrees"] == 90
    assert packet.intrinsics is not None
    assert packet.intrinsics.width_px == 48
    assert packet.intrinsics.height_px == 64
    assert packet.intrinsics.fx == 101.0
    assert packet.intrinsics.fy == 100.0
    assert packet.intrinsics.cx == 24.0
    assert packet.intrinsics.cy == 32.0


def test_advio_open_stream_rotation_opt_in_requires_pyav(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_advio_sequence(tmp_path)
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))
    monkeypatch.setattr(
        advio_replay_module,
        "_load_pyav",
        lambda: (_ for _ in ()).throw(
            RuntimeError(
                "Rotation-aware ADVIO replay requires the optional `av` dependency. Install it with `uv sync --extra replay`."
            )
        ),
    )

    with pytest.raises(RuntimeError, match="uv sync --extra replay"):
        sequence.open_stream(replay_mode=Cv2ReplayMode.FAST_AS_POSSIBLE, respect_video_rotation=True)


def test_advio_sequence_can_normalize_to_sequence_manifest(tmp_path: Path) -> None:
    sequence_dir = _write_advio_sequence(tmp_path)
    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15))

    manifest = sequence.to_sequence_manifest()

    assert manifest.sequence_id == "advio-15"
    assert manifest.video_path == sequence_dir / "iphone" / "frames.mov"
    assert manifest.timestamps_path == sequence_dir / "iphone" / "frames.csv"
    assert manifest.intrinsics_path == tmp_path / "calibration" / "iphone-03.yaml"
    assert manifest.reference_tum_path == sequence_dir / "evaluation" / "ground_truth.tum"
    assert manifest.arcore_tum_path == sequence_dir / "evaluation" / "arcore.tum"
    assert manifest.reference_tum_path.exists()
    assert manifest.arcore_tum_path.exists()


def test_list_advio_sequence_ids_supports_nested_data_layout(tmp_path: Path) -> None:
    _write_advio_sequence(tmp_path, sequence_id=7, nested_layout=True)
    _write_advio_sequence(tmp_path, sequence_id=15)

    assert list_advio_sequence_ids(tmp_path) == [7, 15]


def test_resolve_existing_advio_reference_tum_only_uses_existing_tum(tmp_path: Path) -> None:
    dataset_root = tmp_path / "data" / "advio"
    _write_advio_sequence(dataset_root, sequence_id=15)
    reference_path = resolve_existing_reference_tum(dataset_root, "advio-15")

    assert reference_path is None


def test_resolve_existing_advio_reference_tum_finds_ground_truth(tmp_path: Path) -> None:
    dataset_root = tmp_path / "data" / "advio"
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

    dataset_root = tmp_path / "data" / "advio"
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

    assert status.offline_ready is True
    assert service.list_local_sequence_ids() == [15]
    assert service.load_local_sample(15).sequence_name == "advio-15"


def test_advio_dataset_service_lists_and_loads_local_sequences(tmp_path: Path) -> None:
    dataset_root = tmp_path / "data" / "advio"
    _write_advio_sequence(dataset_root, sequence_id=15)
    service = AdvioDatasetService(PathConfig(root=tmp_path))

    assert service.list_local_sequence_ids() == [15]

    sample = service.load_local_sample(15)

    assert sample.sequence_id == 15
    assert sample.sequence_name == "advio-15"
    assert sample.frame_timestamps_ns.tolist() == [0, 100_000_000, 200_000_000]
