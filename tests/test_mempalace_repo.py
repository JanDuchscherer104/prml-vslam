from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any


def _load_mempalace_module() -> Any:
    module_path = (
        Path(__file__).resolve().parents[1] / ".agents" / "skills" / "mempalace-repo" / "scripts" / "mempalace_repo.py"
    )
    spec = importlib.util.spec_from_file_location("mempalace_repo", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {module_path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MEMPALACE = _load_mempalace_module()


def test_run_mempalace_uses_cli_and_explicit_repo_palace(monkeypatch: Any) -> None:
    calls: list[dict[str, Any]] = []
    palace = Path("/repo/.artifacts/mempalace/palace")

    def fake_run(command: list[str], **kwargs: Any) -> object:
        calls.append({"command": command, **kwargs})

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setenv("MEMPALACE_BIN", "/tools/mempalace")
    monkeypatch.setattr(MEMPALACE, "repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(MEMPALACE, "palace_path", lambda: palace)
    monkeypatch.setattr(MEMPALACE.subprocess, "run", fake_run)

    MEMPALACE.run_mempalace("search", "pipeline")

    assert calls[0]["command"] == ["/tools/mempalace", "--palace", str(palace), "search", "pipeline"]
    assert calls[0]["cwd"] == Path("/repo")
    assert calls[0]["env"]["MEMPALACE_PALACE_PATH"] == str(palace)


def test_mcp_execs_mempalace_mcp_with_repo_palace(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}
    palace = Path("/repo/.artifacts/mempalace/palace")

    monkeypatch.setenv("MEMPALACE_MCP_BIN", "/tools/mempalace-mcp")
    monkeypatch.setattr(MEMPALACE, "ensure_runtime", lambda: None)
    monkeypatch.setattr(MEMPALACE, "palace_path", lambda: palace)

    def fake_execve(executable: str, argv: list[str], env: dict[str, str]) -> None:
        captured.update({"executable": executable, "argv": argv, "env": env})
        raise RuntimeError("stop")

    monkeypatch.setattr(MEMPALACE.os, "execve", fake_execve)

    try:
        MEMPALACE.mcp()
    except RuntimeError as exc:
        assert str(exc) == "stop"

    assert captured["executable"] == "/tools/mempalace-mcp"
    assert captured["argv"] == ["/tools/mempalace-mcp", "--palace", str(palace)]
    assert captured["env"]["MEMPALACE_PALACE_PATH"] == str(palace)


def test_linked_worktree_uses_shared_palace_when_local_palace_missing(tmp_path: Path, monkeypatch: Any) -> None:
    worktree = tmp_path / "repo.worktrees" / "branch"
    shared = tmp_path / "repo"
    (worktree / ".agents" / "skills" / "mempalace-repo" / "scripts").mkdir(parents=True)
    (shared / ".artifacts" / "mempalace" / "palace").mkdir(parents=True)

    monkeypatch.setattr(MEMPALACE, "repo_root", lambda: worktree)
    monkeypatch.setattr(MEMPALACE, "shared_repo_root", lambda: shared)

    assert MEMPALACE.palace_path() == shared / ".artifacts" / "mempalace" / "palace"
    assert MEMPALACE.sources_root() == shared / ".artifacts" / "mempalace" / "sources"


def test_docs_mining_includes_agent_scaffold(tmp_path: Path, monkeypatch: Any) -> None:
    repo = tmp_path / "repo"
    skill = repo / ".agents" / "skills" / "scientific-writing" / "SKILL.md"
    reference = repo / ".agents" / "references" / "agent_reference.md"
    backlog = repo / ".agents" / "issues.toml"
    codex_config = repo / ".codex" / "config.toml"
    for path in (skill, reference, backlog, codex_config, repo / "README.md"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content", encoding="utf-8")

    monkeypatch.setattr(MEMPALACE, "repo_root", lambda: repo)

    docs = {path.relative_to(repo) for path in MEMPALACE._iter_docs_files()}

    assert Path(".agents/skills/scientific-writing/SKILL.md") in docs
    assert Path(".agents/references/agent_reference.md") in docs
    assert Path(".agents/issues.toml") in docs
    assert Path(".codex/config.toml") in docs


def test_init_llm_args_default_local_and_explicit_external_opt_in(monkeypatch: Any) -> None:
    assert MEMPALACE._init_llm_args() == ["--no-llm"]

    monkeypatch.setenv("MEMPALACE_INIT_LLM", "1")
    monkeypatch.setenv("MEMPALACE_INIT_LLM_PROVIDER", "openai-compat")
    monkeypatch.setenv("MEMPALACE_INIT_LLM_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("MEMPALACE_INIT_LLM_ENDPOINT", "https://api.example.test/v1")
    monkeypatch.setenv("MEMPALACE_INIT_LLM_API_KEY", "test-key")
    monkeypatch.setenv("MEMPALACE_ACCEPT_EXTERNAL_LLM", "1")

    assert MEMPALACE._init_llm_args() == [
        "--llm-provider",
        "openai-compat",
        "--llm-model",
        "gpt-4.1-mini",
        "--llm-endpoint",
        "https://api.example.test/v1",
        "--llm-api-key",
        "test-key",
        "--accept-external-llm",
    ]


def test_mempalace_executable_uses_env_override(monkeypatch: Any) -> None:
    monkeypatch.setenv("MEMPALACE_BIN", "/custom/mempalace")

    assert MEMPALACE.mempalace_executable() == "/custom/mempalace"
    assert os.environ["MEMPALACE_BIN"] == "/custom/mempalace"
