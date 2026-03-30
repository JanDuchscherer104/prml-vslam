"""CLI smoke tests."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from typer.testing import CliRunner

from prml_vslam.main import app

runner = CliRunner()


def _write_video(path: Path, *, num_frames: int = 4) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (64, 48))
    for index in range(num_frames):
        frame = np.full((48, 64, 3), index * 40, dtype=np.uint8)
        writer.write(frame)
    writer.release()


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
