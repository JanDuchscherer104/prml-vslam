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


def test_mempalace_bin_prefers_environment_override(monkeypatch) -> None:
    mempalace_repo = _load_mempalace_repo_module()
    monkeypatch.setenv("MEMPALACE_BIN", "/opt/bin/mempalace")

    assert mempalace_repo.mempalace_bin() == "/opt/bin/mempalace"


def test_run_mempalace_uses_cli_and_repo_palace_env(monkeypatch) -> None:
    mempalace_repo = _load_mempalace_repo_module()
    monkeypatch.setenv("MEMPALACE_BIN", "/opt/bin/mempalace")
    calls = []

    def fake_run(command, cwd, env, text, check, capture_output=False):
        calls.append(
            {
                "command": command,
                "cwd": cwd,
                "env": env,
                "text": text,
                "check": check,
                "capture_output": capture_output,
            }
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(mempalace_repo.subprocess, "run", fake_run)

    mempalace_repo.run_mempalace("search", "pipeline DTO", capture_output=True)

    assert calls == [
        {
            "command": ["/opt/bin/mempalace", "search", "pipeline DTO"],
            "cwd": mempalace_repo.repo_root(),
            "env": {
                **os.environ,
                "MEMPALACE_BIN": "/opt/bin/mempalace",
                "MEMPALACE_PALACE_PATH": str(mempalace_repo.palace_path()),
            },
            "text": True,
            "check": True,
            "capture_output": True,
        }
    ]


def test_mcp_passes_explicit_repo_palace_path(monkeypatch) -> None:
    mempalace_repo = _load_mempalace_repo_module()
    monkeypatch.setenv("MEMPALACE_BIN", "/opt/bin/mempalace")
    commands = []

    def fake_run(command, cwd, env, text, check, capture_output=False):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(mempalace_repo.subprocess, "run", fake_run)

    mempalace_repo.mcp()

    assert commands == [
        ["/opt/bin/mempalace", "--version"],
        ["/opt/bin/mempalace", "--palace", str(mempalace_repo.palace_path()), "mcp"],
    ]
