"""Tests for repo-local path configuration."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.path_config import PathConfig


def test_path_config_load_derives_related_roots(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PRML_VSLAM_REPO_ROOT", str(tmp_path))

    config = PathConfig.load()

    assert config.repo_root == tmp_path
    assert config.data_root == tmp_path / "data"
    assert config.artifacts_root == tmp_path / "artifacts"
    assert config.advio_root == tmp_path / "data" / "advio"


def test_path_config_load_respects_explicit_overrides(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    data_root = tmp_path / "datasets"
    artifacts_root = tmp_path / "outputs"
    advio_root = tmp_path / "advio-local"

    monkeypatch.setenv("PRML_VSLAM_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("PRML_VSLAM_DATA_ROOT", str(data_root))
    monkeypatch.setenv("PRML_VSLAM_ARTIFACTS_ROOT", str(artifacts_root))
    monkeypatch.setenv("PRML_VSLAM_ADVIO_ROOT", str(advio_root))

    config = PathConfig.load()

    assert config.repo_root == repo_root
    assert config.data_root == data_root
    assert config.artifacts_root == artifacts_root
    assert config.advio_root == advio_root
