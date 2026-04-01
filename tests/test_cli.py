"""CLI smoke tests."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from typer.testing import CliRunner

from prml_vslam.main import app

runner = CliRunner()


def _write_video(path: Path, *, num_frames: int = 4) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (64, 48))
    for index in range(num_frames):
        frame = np.full((48, 64, 3), index * 40, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def _write_advio_sequence(root: Path, *, sequence_id: int = 15) -> Path:
    sequence_dir = root / f"advio-{sequence_id:02d}"
    (sequence_dir / "iphone").mkdir(parents=True, exist_ok=True)
    (sequence_dir / "pixel").mkdir(parents=True, exist_ok=True)
    (sequence_dir / "ground-truth").mkdir(parents=True, exist_ok=True)
    (root / "calibration").mkdir(parents=True, exist_ok=True)

    _write_video(sequence_dir / "iphone" / "frames.mov", num_frames=3)
    (sequence_dir / "iphone" / "frames.csv").write_text("0.0,0\n0.1,1\n0.2,2\n", encoding="utf-8")
    (sequence_dir / "ground-truth" / "pose.csv").write_text(
        "0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0\n0.1,0.1,0.0,0.0,1.0,0.0,0.0,0.0\n",
        encoding="utf-8",
    )
    (sequence_dir / "iphone" / "arkit.csv").write_text(
        "0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0\n",
        encoding="utf-8",
    )
    (sequence_dir / "pixel" / "arcore.csv").write_text(
        "0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0\n",
        encoding="utf-8",
    )
    (root / "calibration" / "iphone-03.yaml").write_text("camera: {}\n", encoding="utf-8")
    return sequence_dir


def test_info_command_runs() -> None:
    result = runner.invoke(app, ["info"])

    assert result.exit_code == 0
    assert "prml-vslam" in result.stdout


def test_plan_run_command_prints_batch_plan() -> None:
    result = runner.invoke(
        app,
        [
            "plan-run",
            "Lobby Sweep 01",
            "captures/lobby.mp4",
            "--output-dir",
            "artifacts",
            "--method",
            "vista_slam",
        ],
    )

    assert result.exit_code == 0
    assert "artifacts/lobby-sweep-01/batch/vista_slam" in result.stdout
    assert "capture_manifest" in result.stdout


def test_materialize_run_command_creates_workspace(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "materialize-run",
            "Studio Sweep",
            "captures/studio.mp4",
            "--output-dir",
            str(tmp_path / "artifacts"),
            "--method",
            "mast3r_slam",
            "--device-label",
            "Pixel 8 Pro",
        ],
    )

    assert result.exit_code == 0
    artifact_root = tmp_path / "artifacts" / "studio-sweep" / "batch" / "mast3r_slam"
    assert (artifact_root / "input" / "capture_manifest.json").exists()
    assert (artifact_root / "planning" / "run_plan.toml").exists()


def test_run_offline_command_executes_in_materialized_workspace(tmp_path: Path) -> None:
    video_path = tmp_path / "captures" / "studio.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    _write_video(video_path)

    result = runner.invoke(
        app,
        [
            "run-offline",
            "Studio Sweep",
            str(video_path),
            "--output-dir",
            str(tmp_path / "artifacts"),
            "--method",
            "vista_slam",
            "--max-frames",
            "3",
        ],
    )

    assert result.exit_code == 0
    artifact_root = tmp_path / "artifacts" / "studio-sweep" / "batch" / "vista_slam"
    assert (artifact_root / "input" / "capture_manifest.json").exists()
    assert (artifact_root / "planning" / "run_request.toml").exists()
    assert (artifact_root / "planning" / "run_plan.toml").exists()
    assert (artifact_root / "input" / "frames" / "000000.png").exists()
    assert (artifact_root / "slam" / "trajectory.tum").exists()
    assert (artifact_root / "slam" / "trajectory.metadata.json").exists()


def test_advio_download_command_reports_downloaded_sequence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dataset_root = tmp_path / "data" / "advio"

    def fake_download(config, **kwargs):  # type: ignore[no-untyped-def]
        _write_advio_sequence(dataset_root, sequence_id=config.sequence_id)
        return type(
            "FakeSequence",
            (),
            {
                "config": type(
                    "FakeConfig",
                    (),
                    {
                        "sequence_dir": dataset_root / "advio-15",
                        "archive_path": dataset_root / "advio-15.zip",
                        "video_path": dataset_root / "advio-15" / "iphone" / "frames.mov",
                        "ground_truth_path": dataset_root / "advio-15" / "ground-truth" / "pose.csv",
                        "calibration_hint_path": dataset_root / "calibration" / "iphone-03.yaml",
                    },
                )(),
            },
        )()

    monkeypatch.setattr("prml_vslam.cli_advio.download_advio_sequence", fake_download)

    result = runner.invoke(
        app,
        [
            "advio",
            "download",
            "15",
            "--dataset-root",
            str(dataset_root),
        ],
    )

    assert result.exit_code == 0
    assert "ADVIO 15" in result.stdout


def test_advio_export_gt_command_writes_tum_file(tmp_path: Path) -> None:
    dataset_root = tmp_path / "data" / "advio"
    _write_advio_sequence(dataset_root)
    output_path = tmp_path / "exports" / "advio-15.tum"

    result = runner.invoke(
        app,
        [
            "advio",
            "export-gt",
            "15",
            "--dataset-root",
            str(dataset_root),
            "--output-path",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()
    assert output_path.with_suffix(".metadata.json").exists()


def test_advio_run_command_executes_in_materialized_workspace(tmp_path: Path) -> None:
    dataset_root = tmp_path / "data" / "advio"
    _write_advio_sequence(dataset_root)

    result = runner.invoke(
        app,
        [
            "advio",
            "run",
            "15",
            "--dataset-root",
            str(dataset_root),
            "--output-dir",
            str(tmp_path / "artifacts"),
            "--method",
            "vista_slam",
            "--max-frames",
            "2",
        ],
    )

    assert result.exit_code == 0
    artifact_root = tmp_path / "artifacts" / "advio-15" / "batch" / "vista_slam"
    assert (artifact_root / "input" / "capture_manifest.json").exists()
    assert (artifact_root / "planning" / "run_request.toml").exists()
    assert (artifact_root / "input" / "frames" / "000000.png").exists()
    assert (artifact_root / "slam" / "trajectory.tum").exists()


def test_evaluate_trajectory_command_writes_summary(tmp_path: Path) -> None:
    pytest.importorskip("evo")

    reference_path = tmp_path / "reference.tum"
    estimate_path = tmp_path / "estimate.tum"
    output_path = tmp_path / "summary.json"
    reference_path.write_text(
        "# timestamp tx ty tz qx qy qz qw\n0.0 0 0 0 0 0 0 1\n1.0 1 0 0 0 0 0 1\n",
        encoding="utf-8",
    )
    estimate_path.write_text(
        "# timestamp tx ty tz qx qy qz qw\n0.0 0 0 0 0 0 0 1\n1.0 1.1 0 0 0 0 0 1\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "evaluate-trajectory",
            str(reference_path),
            str(estimate_path),
            "--output-path",
            str(output_path),
            "--no-align",
            "--no-correct-scale",
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()
    assert "Trajectory evaluation summary" in result.stdout
