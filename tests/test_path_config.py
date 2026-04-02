"""Tests for centralized repository path handling."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from prml_vslam.utils import PathConfig


def test_path_config_resolves_root_relative_defaults(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path)

    assert path_config.artifacts_dir == (tmp_path / "artifacts").resolve()
    assert path_config.captures_dir == (tmp_path / "captures").resolve()
    assert path_config.data_dir == (tmp_path / "data").resolve()
    assert path_config.logs_dir == (tmp_path / ".logs").resolve()
    assert path_config.method_repos_dir == (tmp_path / ".logs" / "repos").resolve()
    assert path_config.method_envs_dir == (tmp_path / ".logs" / "venvs").resolve()
    assert path_config.checkpoints_dir == (tmp_path / ".logs" / "ckpts").resolve()


def test_path_config_routes_bare_video_names_into_captures_dir(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path)

    assert path_config.resolve_video_path("lobby.mp4") == (tmp_path / "captures" / "lobby.mp4").resolve()
    assert path_config.resolve_video_path("captures/lobby.mp4") == (tmp_path / "captures" / "lobby.mp4").resolve()


def test_path_config_builds_canonical_run_layout(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path)

    run_paths = path_config.plan_run_paths(
        experiment_name="Lobby Sweep 01",
        method_slug="vista",
        output_dir="artifacts",
    )

    expected_root = (tmp_path / "artifacts" / "lobby-sweep-01" / "vista").resolve()
    assert run_paths.artifact_root == expected_root
    assert run_paths.capture_manifest_path == expected_root / "input" / "capture_manifest.json"
    assert run_paths.sequence_manifest_path == expected_root / "input" / "sequence_manifest.json"
    assert run_paths.trajectory_path == expected_root / "slam" / "trajectory.tum"
    assert run_paths.trajectory_metrics_path == expected_root / "evaluation" / "trajectory_metrics.json"
    assert run_paths.summary_path == expected_root / "summary" / "run_summary.json"
    assert run_paths.plotly_scene_path("vista") == expected_root / "visualization" / "vista_scene.html"


def test_path_config_uses_configured_default_output_dir_when_none(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=Path("custom-artifacts"))

    assert path_config.resolve_output_dir() == (tmp_path / "custom-artifacts").resolve()


def test_path_config_builds_method_repo_and_checkpoint_paths(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path)

    repo_dir = path_config.resolve_method_repo_dir("vista-slam")
    env_dir = path_config.resolve_method_env_dir("vista")
    checkpoint_dir = path_config.resolve_checkpoint_dir("vista")

    assert repo_dir == (tmp_path / ".logs" / "repos" / "vista-slam").resolve()
    assert env_dir == (tmp_path / ".logs" / "venvs" / "vista").resolve()
    assert checkpoint_dir == (tmp_path / ".logs" / "ckpts" / "vista").resolve()


def test_path_config_builds_dataset_paths(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path)

    dataset_dir = path_config.resolve_dataset_dir("advio")

    assert dataset_dir == (tmp_path / "data" / "advio").resolve()


def test_path_config_rejects_non_toml_config_paths(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path)

    with pytest.raises(ValueError, match=".toml"):
        path_config.resolve_toml_path("configs/run-config")


def test_path_config_is_immutable_after_construction(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path)

    with pytest.raises(ValidationError, match="frozen"):
        path_config.root = tmp_path
