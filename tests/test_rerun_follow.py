"""Tests for offline follow-enabled Rerun artifact generation."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

from prml_vslam.visualization import rerun_follow


def test_default_follow_output_path_adds_follow_suffix() -> None:
    path = Path("/tmp/viewer_recording.rrd")

    assert rerun_follow.default_follow_output_path(path) == Path("/tmp/viewer_recording_follow.rrd")


def test_create_follow_trajectory_artifact_runs_isolated_blueprint_and_merge(tmp_path: Path) -> None:
    source_path = tmp_path / "viewer_recording.rrd"
    output_path = tmp_path / "viewer_recording_follow.rrd"
    blueprint_path = tmp_path / "follow_blueprint.rrd"
    source_path.write_bytes(b"source")
    commands: list[list[str]] = []
    generated_script = ""

    def fake_runner(command: Sequence[str], cwd: Path | None) -> subprocess.CompletedProcess[str]:
        nonlocal generated_script
        assert cwd == tmp_path
        command_list = list(command)
        commands.append(command_list)
        if "python" in command_list:
            script_path = Path(command_list[command_list.index("python") + 1])
            generated_script = script_path.read_text(encoding="utf-8")
            Path(command_list[command_list.index("--output") + 1]).write_bytes(b"blueprint")
        if "merge" in command_list:
            Path(command_list[command_list.index("-o") + 1]).write_bytes(b"merged")
        if "route" in command_list:
            Path(command_list[command_list.index("-o") + 1]).write_bytes(b"routed")
        return subprocess.CompletedProcess(command_list, 0, stdout="", stderr="")

    result = rerun_follow.create_follow_trajectory_artifact(
        source_path,
        output_path=output_path,
        tracking_entity_path="world/live/tracking/camera",
        uvx_executable="uvx-test",
        keep_blueprint_path=blueprint_path,
        cwd=tmp_path,
        command_runner=fake_runner,
    )

    assert len(commands) == 3
    assert commands[0][:4] == ["uvx-test", "--from", "rerun-sdk==0.27.0", "python"]
    assert commands[0][-4:] == [
        "--application-id",
        "prml-vslam",
        "--tracking-entity",
        "world/live/tracking/camera",
    ]
    assert commands[1] == [
        "uvx-test",
        "--from",
        "rerun-sdk==0.27.0",
        "rerun",
        "rrd",
        "merge",
        source_path.resolve().as_posix(),
        blueprint_path.resolve().as_posix(),
        "-o",
        commands[2][commands[2].index("route") + 1],
    ]
    assert commands[2][:6] == ["uvx-test", "--from", "rerun-sdk==0.27.0", "rerun", "rrd", "route"]
    assert commands[2][-4:] == [
        "--recording-id",
        "viewer_recording",
        "-o",
        output_path.resolve().as_posix(),
    ]
    assert "EyeControls3D(tracking_entity=tracking_entity_path)" in generated_script
    assert result.source_rrd_path == source_path.resolve()
    assert result.output_rrd_path == output_path.resolve()
    assert result.blueprint_rrd_path == blueprint_path.resolve()
    assert output_path.read_bytes() == b"routed"


def test_create_follow_trajectory_artifact_accepts_explicit_recording_id(tmp_path: Path) -> None:
    source_path = tmp_path / "viewer_recording.rrd"
    output_path = tmp_path / "viewer_recording_follow.rrd"
    source_path.write_bytes(b"source")
    commands: list[list[str]] = []

    def fake_runner(command: Sequence[str], cwd: Path | None) -> subprocess.CompletedProcess[str]:
        del cwd
        command_list = list(command)
        commands.append(command_list)
        if "merge" in command_list:
            Path(command_list[command_list.index("-o") + 1]).write_bytes(b"merged")
        if "route" in command_list:
            Path(command_list[command_list.index("-o") + 1]).write_bytes(b"routed")
        return subprocess.CompletedProcess(command_list, 0, stdout="", stderr="")

    rerun_follow.create_follow_trajectory_artifact(
        source_path,
        output_path=output_path,
        recording_id="custom-recording",
        command_runner=fake_runner,
    )

    route_command = commands[-1]
    assert route_command[route_command.index("--recording-id") + 1] == "custom-recording"
    assert output_path.read_bytes() == b"routed"


def test_create_follow_trajectory_artifact_refuses_in_place_output(tmp_path: Path) -> None:
    source_path = tmp_path / "viewer_recording.rrd"
    source_path.write_bytes(b"source")

    try:
        rerun_follow.create_follow_trajectory_artifact(source_path, output_path=source_path)
    except ValueError as exc:
        assert "must not replace" in str(exc)
    else:
        raise AssertionError("Expected in-place follow artifact generation to fail.")


def test_create_follow_trajectory_artifact_refuses_existing_output(tmp_path: Path) -> None:
    source_path = tmp_path / "viewer_recording.rrd"
    output_path = tmp_path / "viewer_recording_follow.rrd"
    source_path.write_bytes(b"source")
    output_path.write_bytes(b"existing")

    try:
        rerun_follow.create_follow_trajectory_artifact(source_path, output_path=output_path)
    except FileExistsError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("Expected existing follow artifact generation to fail without overwrite.")
