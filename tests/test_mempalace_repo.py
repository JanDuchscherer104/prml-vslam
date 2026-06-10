"""Tests for the repo-local MemPalace wrapper."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _load_mempalace_repo_module() -> Any:
    module_path = (
        Path(__file__).resolve().parents[1] / ".agents" / "skills" / "mempalace-repo" / "scripts" / "mempalace_repo.py"
    )
    spec = importlib.util.spec_from_file_location("mempalace_repo", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_mempalace_executable_prefers_environment_override(monkeypatch) -> None:
    mempalace_repo = _load_mempalace_repo_module()
    monkeypatch.setenv("MEMPALACE_BIN", "/opt/bin/mempalace")

    assert mempalace_repo.mempalace_executable() == "/opt/bin/mempalace"


def test_run_mempalace_uses_cli_and_explicit_repo_palace(monkeypatch) -> None:
    mempalace_repo = _load_mempalace_repo_module()
    palace_path = Path("/repo/.artifacts/mempalace/palace")
    monkeypatch.setenv("MEMPALACE_BIN", "/opt/bin/mempalace")
    monkeypatch.setattr(mempalace_repo, "palace_path", lambda: palace_path)
    calls = []

    def fake_run(command, cwd, env, text, check, capture_output=False, stdout=None):
        calls.append(
            {
                "command": command,
                "cwd": cwd,
                "env": env,
                "text": text,
                "check": check,
                "capture_output": capture_output,
                "stdout": stdout,
            }
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(mempalace_repo.subprocess, "run", fake_run)

    mempalace_repo.run_mempalace("search", "pipeline DTO", capture_output=True)

    assert calls == [
        {
            "command": [
                "/opt/bin/mempalace",
                "--palace",
                str(palace_path),
                "search",
                "pipeline DTO",
            ],
            "cwd": mempalace_repo.repo_root(),
            "env": {
                **os.environ,
                "MEMPALACE_BIN": "/opt/bin/mempalace",
                "MEMPALACE_PALACE_PATH": str(palace_path),
            },
            "text": True,
            "check": True,
            "capture_output": True,
            "stdout": None,
        }
    ]


def test_mcp_execs_mempalace_mcp_with_explicit_repo_palace(monkeypatch) -> None:
    mempalace_repo = _load_mempalace_repo_module()
    palace_path = Path("/repo/.artifacts/mempalace/palace")
    monkeypatch.setenv("MEMPALACE_BIN", "/opt/bin/mempalace")
    monkeypatch.setenv("MEMPALACE_MCP_BIN", "/opt/bin/mempalace-mcp")
    monkeypatch.setattr(mempalace_repo, "palace_path", lambda: palace_path)
    commands = []
    exec_calls = []

    def fake_run(command, cwd, env, text, check, capture_output=False, stdout=None):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    def fake_execve(path, argv, env):
        exec_calls.append((path, argv, env))
        raise SystemExit(0)

    monkeypatch.setattr(mempalace_repo.subprocess, "run", fake_run)
    monkeypatch.setattr(mempalace_repo.os, "execve", fake_execve)

    try:
        mempalace_repo.mcp()
    except SystemExit as exc:
        assert exc.code == 0

    assert commands == [["/opt/bin/mempalace", "--version"]]
    assert exec_calls == [
        (
            "/opt/bin/mempalace-mcp",
            ["/opt/bin/mempalace-mcp", "--palace", str(palace_path)],
            {
                **os.environ,
                "MEMPALACE_BIN": "/opt/bin/mempalace",
                "MEMPALACE_MCP_BIN": "/opt/bin/mempalace-mcp",
                "MEMPALACE_PALACE_PATH": str(palace_path),
            },
        )
    ]


def test_worktree_without_local_palace_uses_shared_repo_root(monkeypatch, tmp_path) -> None:
    mempalace_repo = _load_mempalace_repo_module()
    shared_root = tmp_path / "main"
    worktree_root = tmp_path / "worktree"
    shared_root.mkdir()
    worktree_root.mkdir()
    (shared_root / ".artifacts" / "mempalace" / "palace").mkdir(parents=True)

    monkeypatch.setattr(mempalace_repo, "repo_root", lambda: worktree_root)
    monkeypatch.setattr(mempalace_repo, "shared_repo_root", lambda: shared_root)

    assert mempalace_repo.mempalace_root() == shared_root / ".artifacts" / "mempalace"
