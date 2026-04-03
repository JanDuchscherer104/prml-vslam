"""Tests for method mock path bookkeeping helpers."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.methods import MethodId, MethodInstallationService
from prml_vslam.utils import PathConfig


def test_method_install_service_uses_centralized_repo_and_checkpoint_paths(tmp_path: Path) -> None:
    service = MethodInstallationService(path_config=PathConfig(root=tmp_path))

    assert service.get_repo_path(MethodId.VISTA) == (tmp_path / ".logs" / "repos" / "vista-slam").resolve()
    assert service.get_repo_path(MethodId.MSTR) == (tmp_path / ".logs" / "repos" / "MASt3R-SLAM").resolve()
    assert service.get_environment_dir(MethodId.VISTA) == (tmp_path / ".logs" / "venvs" / "vista").resolve()
    assert service.get_environment_dir(MethodId.MSTR) == (tmp_path / ".logs" / "venvs" / "mstr").resolve()
    assert service.get_checkpoint_dir(MethodId.VISTA) == (tmp_path / ".logs" / "ckpts" / "vista").resolve()
    assert service.get_checkpoint_dir(MethodId.MSTR) == (tmp_path / ".logs" / "ckpts" / "mstr").resolve()


def test_method_install_service_links_repo_checkpoints_to_shared_dir(tmp_path: Path) -> None:
    service = MethodInstallationService(path_config=PathConfig(root=tmp_path))
    repo_path = service.get_repo_path(MethodId.VISTA)
    repo_path.mkdir(parents=True)

    link_path = service.ensure_shared_checkpoint_link(MethodId.VISTA)

    assert link_path == (repo_path / "pretrains")
    assert link_path.is_symlink()
    assert link_path.resolve() == service.get_checkpoint_dir(MethodId.VISTA)


def test_method_install_service_migrates_existing_repo_checkpoint_files(tmp_path: Path) -> None:
    service = MethodInstallationService(path_config=PathConfig(root=tmp_path))
    repo_path = service.get_repo_path(MethodId.VISTA)
    checkpoint_dir = service.get_checkpoint_dir(MethodId.VISTA)
    pretrains_dir = repo_path / "pretrains"
    pretrains_dir.mkdir(parents=True)
    (pretrains_dir / "README.md").write_text("hello\n", encoding="utf-8")

    link_path = service.ensure_shared_checkpoint_link(MethodId.VISTA)

    assert (checkpoint_dir / "README.md").read_text(encoding="utf-8") == "hello\n"
    assert link_path.is_symlink()
    assert link_path.resolve() == checkpoint_dir


def test_method_install_service_writes_mock_environment_marker(tmp_path: Path) -> None:
    service = MethodInstallationService(path_config=PathConfig(root=tmp_path))

    python_executable = service.sync_environment(MethodId.MSTR)
    expected_env_dir = service.get_environment_dir(MethodId.MSTR)

    assert service.get_environment_ready_marker(MethodId.MSTR).read_text(encoding="utf-8") == "mstr\n"
    assert service.is_environment_ready(MethodId.MSTR) is False
    assert python_executable == service.get_python_executable(MethodId.MSTR)
    assert expected_env_dir == (tmp_path / ".logs" / "venvs" / "mstr").resolve()
