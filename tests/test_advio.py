"""Tests for the ADVIO dataset adapter."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from prml_vslam.datasets.advio import (
    AdvioSequence,
    AdvioSequenceConfig,
    download_advio_sequence,
    list_advio_sequence_ids,
    load_advio_calibration,
    load_advio_imu_samples,
    summarize_advio_sequence,
)
from prml_vslam.pipeline.contracts import MethodId


def _write_pose_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "0.0,1.0,2.0,3.0,1.0,0.0,0.0,0.0\n0.1,4.0,5.0,6.0,0.0,1.0,0.0,0.0\n",
        encoding="utf-8",
    )


def _write_advio_sequence(root: Path, *, sequence_id: int = 15, pose_name: str = "poses.csv") -> AdvioSequence:
    config = AdvioSequenceConfig(dataset_root=root, sequence_id=sequence_id)
    sequence_dir = config.sequence_dir
    (sequence_dir / "iphone").mkdir(parents=True, exist_ok=True)
    (sequence_dir / "pixel").mkdir(parents=True, exist_ok=True)
    (sequence_dir / "ground-truth").mkdir(parents=True, exist_ok=True)
    (root / "calibration").mkdir(parents=True, exist_ok=True)

    (sequence_dir / "iphone" / "frames.mov").write_bytes(b"fake-mov")
    (sequence_dir / "iphone" / "frames.csv").write_text("0.0,0\n0.1,1\n0.2,2\n", encoding="utf-8")
    _write_pose_csv(sequence_dir / "ground-truth" / pose_name)
    _write_pose_csv(sequence_dir / "pixel" / "arcore.csv")
    (root / "calibration" / config.calibration_name).write_text("camera: {}\n", encoding="utf-8")

    return AdvioSequence(config=config).assert_ready()


def _augment_advio_modalities(sequence: AdvioSequence) -> None:
    sequence_dir = sequence.config.sequence_dir
    (sequence_dir / "iphone" / "accelerometer.csv").write_text("0.0,0,0,0\n0.1,1,1,1\n", encoding="utf-8")
    (sequence_dir / "iphone" / "gyroscope.csv").write_text("0.0,0,0,0\n0.1,1,1,1\n", encoding="utf-8")
    (sequence_dir / "iphone" / "platform-location.csv").write_text("0.0,1,2,3,4,5,6\n", encoding="utf-8")
    (sequence_dir / "iphone" / "arkit.csv").write_text("0.0,0,0,0,1,0,0,0\n0.1,0,0,0,1,0,0,0\n", encoding="utf-8")
    (sequence_dir / "tango").mkdir(parents=True, exist_ok=True)
    (sequence_dir / "tango" / "frames.mov").write_bytes(b"fake-tango-mov")
    (sequence_dir / "tango" / "frames.csv").write_text("0.0,0\n0.2,1\n0.4,2\n", encoding="utf-8")
    (sequence_dir / "tango" / "area-learning.csv").write_text(
        "0.0,0,0,0,1,0,0,0\n0.2,0,0,0,1,0,0,0\n", encoding="utf-8"
    )
    (sequence_dir / "tango" / "point-cloud-00001.csv").write_text("0,0,0\n1,1,1\n", encoding="utf-8")
    (sequence_dir / "tango" / "point-cloud-00002.csv").write_text("0,0,0\n", encoding="utf-8")


def test_advio_sequence_loads_frame_timestamps_and_builds_request(tmp_path: Path) -> None:
    sequence = _write_advio_sequence(tmp_path, sequence_id=15)

    timestamps_ns = sequence.load_frame_timestamps_ns()
    request = sequence.build_run_request(
        experiment_name="ADVIO 15",
        output_dir=tmp_path / "artifacts",
        method=MethodId.VISTA_SLAM,
        frame_stride=2,
    )

    assert timestamps_ns == [0, 100_000_000, 200_000_000]
    assert request.video_path == sequence.config.video_path
    assert request.capture.calibration_hint_path == sequence.config.calibration_hint_path
    assert request.compare_to_arcore is True
    assert request.enable_dense_mapping is False


def test_advio_sequence_loads_imu_from_official_gyroscope_filename(tmp_path: Path) -> None:
    sequence = _write_advio_sequence(tmp_path, sequence_id=15)
    sequence_dir = sequence.config.sequence_dir
    (sequence_dir / "iphone" / "accelerometer.csv").write_text("0.0,0.0,0.0,0.0\n0.2,2.0,4.0,6.0\n", encoding="utf-8")
    (sequence_dir / "iphone" / "gyroscope.csv").write_text(
        "0.0,1.0,2.0,3.0\n0.1,4.0,5.0,6.0\n0.2,7.0,8.0,9.0\n",
        encoding="utf-8",
    )

    samples = sequence.load_iphone_imu()

    assert [sample.timestamp_s for sample in samples] == pytest.approx([0.0, 0.1, 0.2])
    assert samples[1].accelerometer_values == pytest.approx((1.0, 2.0, 3.0))


def test_advio_sequence_exports_ground_truth_tum(tmp_path: Path) -> None:
    sequence = _write_advio_sequence(tmp_path, sequence_id=15)

    tum_path = sequence.write_ground_truth_tum(tmp_path / "ground_truth.tum")
    lines = tum_path.read_text(encoding="utf-8").strip().splitlines()

    assert lines[0].startswith("# timestamp")
    assert lines[1] == "0.000000000 1.000000000 2.000000000 3.000000000 0.000000000 0.000000000 0.000000000 1.000000000"
    assert lines[2] == "0.100000000 4.000000000 5.000000000 6.000000000 1.000000000 0.000000000 0.000000000 0.000000000"


def test_advio_sequence_supports_legacy_pose_csv_fallback(tmp_path: Path) -> None:
    sequence = _write_advio_sequence(tmp_path, sequence_id=15, pose_name="pose.csv")

    assert sequence.config.ground_truth_path.name == "pose.csv"
    assert len(sequence.load_ground_truth()) == 2


def test_load_advio_calibration_parses_official_yaml_shape(tmp_path: Path) -> None:
    calibration_path = tmp_path / "iphone-03.yaml"
    calibration_path.write_text(
        """
label: "Iphone - original_calibration"
id: 412eab8e4058621f7036b5e765dfe812
cameras:
- camera:
    label: cam0
    id: 54812562fa109c40fe90b29a59dd7798
    image_height: 1280
    image_width: 720
    type: pinhole
    intrinsics:
      cols: 1
      rows: 4
      data: [1082.4, 1084.4, 364.6778, 643.3080]
    distortion:
      type: radial-tangential
      parameters:
        cols: 1
        rows: 4
        data: [0.0366, 0.0803, 0.000783, -0.000215]
    T_cam_imu:
      cols: 4
      rows: 4
      data:
      - [0.9999763379, -0.0040792050, -0.0055392877, -0.0089776684]
      - [-0.0040663863, -0.9999890330, 0.0023234366, 0.0755701232]
      - [-0.0055487047, -0.0023008567, -0.9999819588, -0.0055457739]
      - [0.0, 0.0, 0.0, 1.0]
""".strip(),
        encoding="utf-8",
    )

    calibration = load_advio_calibration(calibration_path)

    assert calibration.image_width_px == 720
    assert calibration.image_height_px == 1280
    assert calibration.camera_model == "pinhole"
    assert calibration.distortion_model == "radial-tangential"
    assert calibration.focal_length_px == pytest.approx((1082.4, 1084.4))
    assert calibration.principal_point_px == pytest.approx((364.6778, 643.3080))
    assert calibration.distortion_coefficients == pytest.approx((0.0366, 0.0803, 0.000783, -0.000215))
    assert calibration.t_cam_imu[0] == pytest.approx((0.9999763379, -0.0040792050, -0.0055392877, -0.0089776684))


def test_load_advio_imu_samples_aligns_accelerometer_to_gyro_grid(tmp_path: Path) -> None:
    accelerometer_path = tmp_path / "accelerometer.csv"
    gyroscope_path = tmp_path / "gyroscope.csv"
    accelerometer_path.write_text("0.0,0.0,0.0,0.0\n0.2,2.0,4.0,6.0\n", encoding="utf-8")
    gyroscope_path.write_text("0.0,1.0,2.0,3.0\n0.1,4.0,5.0,6.0\n0.2,7.0,8.0,9.0\n", encoding="utf-8")

    samples = load_advio_imu_samples(
        accelerometer_path=accelerometer_path,
        gyroscope_path=gyroscope_path,
    )

    assert [sample.timestamp_s for sample in samples] == pytest.approx([0.0, 0.1, 0.2])
    assert samples[1].angular_velocity_rad_s == pytest.approx((4.0, 5.0, 6.0))
    assert samples[1].accelerometer_values == pytest.approx((1.0, 2.0, 3.0))


def test_advio_sequence_selects_calibration_by_sequence_range(tmp_path: Path) -> None:
    config = AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=22)

    assert config.calibration_hint_path.name == "iphone-04.yaml"


def test_advio_sequence_summary_reports_modalities_and_footprint(tmp_path: Path) -> None:
    sequence = _write_advio_sequence(tmp_path, sequence_id=15)
    _augment_advio_modalities(sequence)

    summary = summarize_advio_sequence(sequence.config)

    assert summary.timed_modality_count >= 6
    assert summary.asset_modality_count >= 4
    assert summary.duration_s == pytest.approx(0.4)
    assert summary.point_cloud_snapshot_count == 2
    assert any(modality.slug == "iphone_frames" for modality in summary.timed_modalities)
    assert any(modality.slug == "iphone_gyro" for modality in summary.timed_modalities)
    assert any(modality.slug == "iphone_platform_locations" for modality in summary.timed_modalities)
    assert any(modality.slug == "tango_point_clouds" for modality in summary.asset_modalities)


def test_list_advio_sequence_ids_discovers_extracted_sequences(tmp_path: Path) -> None:
    _write_advio_sequence(tmp_path, sequence_id=7)
    _write_advio_sequence(tmp_path, sequence_id=15)

    assert list_advio_sequence_ids(tmp_path) == [7, 15]


class _BytesResponse(io.BytesIO):
    def __enter__(self) -> _BytesResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def test_download_advio_sequence_downloads_and_extracts_sequence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr("data/advio-15/iphone/frames.mov", b"fake-mov")
        archive.writestr("data/advio-15/iphone/frames.csv", "0.0,0\n0.1,1\n")
        archive.writestr("data/advio-15/ground-truth/poses.csv", "0.0,0,0,0,1,0,0,0\n")
        archive.writestr("data/advio-15/pixel/arcore.csv", "0.0,0,0,0,1,0,0,0\n")
    archive_payload = archive_bytes.getvalue()

    def fake_urlopen(url: str):  # type: ignore[no-untyped-def]
        if str(url).endswith(".zip"):
            return _BytesResponse(archive_payload)
        return _BytesResponse(b"camera: {}\n")

    monkeypatch.setattr("prml_vslam.io.cv2_producer.urllib.request.urlopen", fake_urlopen)

    sequence = download_advio_sequence(
        AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15),
        keep_archive=False,
    )

    assert sequence.config.sequence_dir.exists()
    assert sequence.config.video_path.exists()
    assert sequence.config.calibration_hint_path.exists()
    assert not sequence.config.archive_path.exists()


def test_download_advio_sequence_prefers_complete_extracted_layout_over_stale_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "advio-15").mkdir(parents=True, exist_ok=True)
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr("data/advio-15/iphone/frames.mov", b"fake-mov")
        archive.writestr("data/advio-15/iphone/frames.csv", "0.0,0\n0.1,1\n")
        archive.writestr("data/advio-15/ground-truth/poses.csv", "0.0,0,0,0,1,0,0,0\n")
        archive.writestr("data/advio-15/pixel/arcore.csv", "0.0,0,0,0,1,0,0,0\n")
    archive_payload = archive_bytes.getvalue()

    def fake_urlopen(url: str):  # type: ignore[no-untyped-def]
        if str(url).endswith(".zip"):
            return _BytesResponse(archive_payload)
        return _BytesResponse(
            b"cameras:\n- camera:\n    image_height: 1\n    image_width: 1\n    type: pinhole\n    intrinsics:\n      data: [1, 1, 0, 0]\n    distortion:\n      type: radial-tangential\n      parameters:\n        data: [0, 0, 0, 0]\n    T_cam_imu:\n      data:\n      - [1, 0, 0, 0]\n      - [0, 1, 0, 0]\n      - [0, 0, 1, 0]\n      - [0, 0, 0, 1]\n"
        )

    monkeypatch.setattr("prml_vslam.io.cv2_producer.urllib.request.urlopen", fake_urlopen)

    sequence = download_advio_sequence(
        AdvioSequenceConfig(dataset_root=tmp_path, sequence_id=15),
        keep_archive=False,
    )

    assert sequence.paths.sequence_dir == tmp_path / "data" / "advio-15"
    assert sequence.config.sequence_dir == tmp_path / "data" / "advio-15"
