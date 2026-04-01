"""Tests for dataset adapters."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from prml_vslam.datasets import AdvioSequence, AdvioSequenceConfig, load_advio_frame_timestamps_ns
from prml_vslam.pipeline.contracts import MethodId, TimestampSource


def _write_video(path: Path, *, num_frames: int = 3) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (64, 48))
    for index in range(num_frames):
        frame = np.full((48, 64, 3), index * 30, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def _write_fake_advio_sequence(dataset_root: Path, *, sequence_id: int = 15) -> Path:
    sequence_dir = dataset_root / f"advio-{sequence_id:02d}"
    (sequence_dir / "iphone").mkdir(parents=True, exist_ok=True)
    (sequence_dir / "pixel").mkdir(parents=True, exist_ok=True)
    (sequence_dir / "ground-truth").mkdir(parents=True, exist_ok=True)
    (dataset_root / "calibration").mkdir(parents=True, exist_ok=True)

    _write_video(sequence_dir / "iphone" / "frames.mov")
    (sequence_dir / "iphone" / "frames.csv").write_text("0.000000,0\n0.100000,1\n0.200000,2\n", encoding="utf-8")
    (sequence_dir / "iphone" / "arkit.csv").write_text(
        "0.0,0,0,0,1,0,0,0\n0.1,0,0,0.1,1,0,0,0\n",
        encoding="utf-8",
    )
    (sequence_dir / "pixel" / "arcore.csv").write_text(
        "0.0,0,0,0,1,0,0,0\n0.1,0,0,0.1,1,0,0,0\n",
        encoding="utf-8",
    )
    (sequence_dir / "ground-truth" / "pose.csv").write_text(
        "0.0,1,2,3,1,0,0,0\n0.1,1.1,2.1,3.1,1,0,0,0\n",
        encoding="utf-8",
    )
    (dataset_root / "calibration" / "iphone-03.yaml").write_text("camera: test\n", encoding="utf-8")
    return sequence_dir


def test_advio_sequence_loads_timestamps_and_exports_tum(tmp_path: Path) -> None:
    dataset_root = tmp_path / "advio"
    _write_fake_advio_sequence(dataset_root)

    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=dataset_root, sequence_id=15)).assert_ready()

    timestamps_ns = load_advio_frame_timestamps_ns(sequence.paths.frame_timestamps_path)
    assert timestamps_ns == [0, 100_000_000, 200_000_000]

    tum_path = tmp_path / "ground_truth.tum"
    sequence.write_ground_truth_tum(tum_path)
    tum_lines = tum_path.read_text(encoding="utf-8").splitlines()
    assert tum_lines[0].startswith("# timestamp")
    assert tum_lines[1].split() == [
        "0.000000000",
        "1.000000000",
        "2.000000000",
        "3.000000000",
        "0.000000000",
        "0.000000000",
        "0.000000000",
        "1.000000000",
    ]


def test_advio_sequence_builds_run_request(tmp_path: Path) -> None:
    dataset_root = tmp_path / "advio"
    sequence_dir = _write_fake_advio_sequence(dataset_root)

    sequence = AdvioSequence(config=AdvioSequenceConfig(dataset_root=dataset_root, sequence_id=15)).assert_ready()
    request = sequence.build_run_request(
        experiment_name="ADVIO 15",
        output_dir=tmp_path / "artifacts",
        method=MethodId.VISTA_SLAM,
        frame_stride=2,
    )

    assert request.video_path == sequence_dir / "iphone" / "frames.mov"
    assert request.capture.timestamp_source is TimestampSource.CAPTURE
    assert request.capture.arcore_log_path == sequence_dir / "pixel" / "arcore.csv"
    assert request.capture.calibration_hint_path == dataset_root / "calibration" / "iphone-03.yaml"
