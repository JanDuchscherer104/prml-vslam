from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest


def _load_graphify_module() -> Any:
    module_path = Path(__file__).resolve().parents[1] / ".agents" / "scripts" / "graphify_repo.py"
    spec = importlib.util.spec_from_file_location("graphify_repo", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {module_path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GRAPHIFY = _load_graphify_module()


def test_lfs_pointer_detection(tmp_path: Path) -> None:
    pointer = tmp_path / "graph.json"
    pointer.write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:5976b242c80e9c8bf9917509a5a1db12c6775c6e4fe98e6e7158784eb648a099\n"
        "size 9859594\n",
        encoding="utf-8",
    )
    materialized = tmp_path / "materialized.json"
    materialized.write_text('{"nodes": [], "links": []}\n', encoding="utf-8")

    assert GRAPHIFY.is_lfs_pointer(pointer)
    assert not GRAPHIFY.is_lfs_pointer(materialized)


def test_status_reports_pointer_without_json_traceback(tmp_path: Path, monkeypatch: Any, capsys: Any) -> None:
    repo = tmp_path / "repo"
    graphify_out = repo / "graphify-out"
    graphify_out.mkdir(parents=True)
    (graphify_out / "GRAPH_REPORT.md").write_text(
        "# Graph Report - demo (2026-06-12)\n\n## Summary\n- 2 nodes · 3 edges · 1 communities detected\n",
        encoding="utf-8",
    )
    (graphify_out / "graph.json").write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:5976b242c80e9c8bf9917509a5a1db12c6775c6e4fe98e6e7158784eb648a099\n"
        "size 9859594\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(GRAPHIFY, "repo_root", lambda: repo)
    monkeypatch.setattr(GRAPHIFY, "graphify_version", lambda: "0.4.26")
    monkeypatch.setattr(GRAPHIFY, "_git_status", lambda _paths: "clean")

    GRAPHIFY.status()

    output = capsys.readouterr().out
    assert "graph data state: git-lfs pointer" in output
    assert "nodes: 2" in output
    assert "artifact dirty state: clean" in output


def test_mcp_materializes_pointer_then_execs_graphify_server(tmp_path: Path, monkeypatch: Any) -> None:
    repo = tmp_path / "repo"
    graphify_out = repo / "graphify-out"
    graphify_out.mkdir(parents=True)
    graph_path = graphify_out / "graph.json"
    graph_path.write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:5976b242c80e9c8bf9917509a5a1db12c6775c6e4fe98e6e7158784eb648a099\n"
        "size 9859594\n",
        encoding="utf-8",
    )
    captured: dict[str, Any] = {}

    class PullResult:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command: list[str], **kwargs: Any) -> PullResult:
        captured["pull"] = command
        graph_path.write_text('{"nodes": [], "links": []}\n', encoding="utf-8")
        return PullResult()

    def fake_execvp(executable: str, argv: list[str]) -> None:
        captured["exec"] = (executable, argv)
        raise RuntimeError("stop")

    monkeypatch.setenv("UV_BIN", "/tools/uv")
    monkeypatch.setattr(GRAPHIFY, "repo_root", lambda: repo)
    monkeypatch.setattr(GRAPHIFY.subprocess, "run", fake_run)
    monkeypatch.setattr(GRAPHIFY.os, "execvp", fake_execvp)

    with pytest.raises(RuntimeError, match="stop"):
        GRAPHIFY.mcp()

    assert captured["pull"] == ["git", "lfs", "pull", "--include=graphify-out/graph.json", "--exclude="]
    executable, argv = captured["exec"]
    assert executable == "/tools/uv"
    assert argv[-3:] == ["-m", "graphify.serve", "graphify-out/graph.json"]
