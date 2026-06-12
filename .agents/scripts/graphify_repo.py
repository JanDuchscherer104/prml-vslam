#!/usr/bin/env python3
"""Repo-local Graphify helper for status, reports, and MCP startup."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

GRAPHIFY_DIR = Path("graphify-out")
GRAPHIFY_REPORT = GRAPHIFY_DIR / "GRAPH_REPORT.md"
GRAPHIFY_GRAPH = GRAPHIFY_DIR / "graph.json"
GRAPHIFY_HTML = GRAPHIFY_DIR / "graph.html"
LFS_POINTER_PREFIX = "version https://git-lfs.github.com/spec/v1"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def is_lfs_pointer(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        return _read_text(path).startswith(LFS_POINTER_PREFIX)
    except UnicodeDecodeError:
        return False


def graphify_version() -> str:
    try:
        return version("graphifyy")
    except PackageNotFoundError:
        return "missing"


def _report_summary() -> dict[str, str]:
    report_path = repo_root() / GRAPHIFY_REPORT
    if not report_path.exists():
        return {}
    report = _read_text(report_path)
    date = re.search(r"^# Graph Report - .*\(([^)]*)\)", report, re.M)
    summary = re.search(r"^- (\d+) nodes .+? (\d+) edges .+? (\d+) communities detected", report, re.M)
    return {
        "date": date.group(1) if date else "unknown",
        "nodes": summary.group(1) if summary else "unknown",
        "links": summary.group(2) if summary else "unknown",
        "communities": summary.group(3) if summary else "unknown",
    }


def _materialized_graph_summary() -> dict[str, str]:
    graph = json.loads(_read_text(repo_root() / GRAPHIFY_GRAPH))
    nodes = graph.get("nodes", [])
    links = graph.get("links", graph.get("edges", []))
    return {"nodes": str(len(nodes)), "links": str(len(links))}


def _git_status(paths: list[Path]) -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--", *[str(path) for path in paths]],
            cwd=repo_root(),
            text=True,
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unknown"
    return "modified" if result.stdout.strip() else "clean"


def status() -> None:
    for path, label in (
        (GRAPHIFY_DIR, "graphify directory"),
        (GRAPHIFY_REPORT, "graphify report"),
        (GRAPHIFY_GRAPH, "graphify graph data"),
    ):
        if not (repo_root() / path).exists():
            raise SystemExit(f"Missing {label}: {path}")

    print(f"graphify artifacts: {GRAPHIFY_DIR}")
    print(f"report: {GRAPHIFY_REPORT}")
    print(f"graph data: {GRAPHIFY_GRAPH}")
    if (repo_root() / GRAPHIFY_HTML).exists():
        print(f"viewer: {GRAPHIFY_HTML}")
    print(
        f"runtime: {'available (graphifyy ' + graphify_version() + ')' if graphify_version() != 'missing' else 'missing'}"
    )

    summary = _report_summary()
    if is_lfs_pointer(repo_root() / GRAPHIFY_GRAPH):
        print("graph data state: git-lfs pointer")
        print(
            "graph data hydration: run `git lfs pull --include=graphify-out/graph.json` or `make graphify-rebuild` before MCP startup"
        )
    else:
        summary.update(_materialized_graph_summary())
        print("graph data state: materialized")
    if summary:
        print(f"graph date: {summary.get('date', 'unknown')}")
        print(f"nodes: {summary.get('nodes', 'unknown')}")
        print(f"links: {summary.get('links', 'unknown')}")
        print(f"communities: {summary.get('communities', 'unknown')}")
    print(f"artifact dirty state: {_git_status([GRAPHIFY_REPORT, GRAPHIFY_GRAPH, GRAPHIFY_HTML])}")
    print("next: make graphify-report | make graphify-rebuild | make graphify-hook-install")


def report() -> None:
    if not (repo_root() / GRAPHIFY_REPORT).exists():
        raise SystemExit(f"Missing graphify report: {GRAPHIFY_REPORT}")
    text = _read_text(repo_root() / GRAPHIFY_REPORT)
    print(text.splitlines()[0])
    for name in ("Corpus Check", "Summary", "Suggested Questions"):
        match = re.search(r"^## " + re.escape(name) + r"\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        if match:
            print(f"\n## {name}\n{match.group(1).strip()}")


def materialize_graph_for_mcp() -> None:
    graph_path = repo_root() / GRAPHIFY_GRAPH
    if not graph_path.exists():
        raise SystemExit(f"Missing graphify graph data: {GRAPHIFY_GRAPH}")
    if not is_lfs_pointer(graph_path):
        json.loads(_read_text(graph_path))
        return

    pull = subprocess.run(
        ["git", "lfs", "pull", "--include=graphify-out/graph.json", "--exclude="],
        cwd=repo_root(),
        text=True,
        capture_output=True,
    )
    if pull.returncode != 0:
        raise SystemExit(
            "Graphify graph data is a Git LFS pointer and `git lfs pull` failed.\n"
            f"stdout:\n{pull.stdout}\nstderr:\n{pull.stderr}"
        )
    if is_lfs_pointer(graph_path):
        raise SystemExit(
            "Graphify graph data is still a Git LFS pointer after `git lfs pull`; "
            "run `git lfs pull --include=graphify-out/graph.json` or `make graphify-rebuild`."
        )
    json.loads(_read_text(graph_path))


def mcp() -> None:
    materialize_graph_for_mcp()
    uv = os.environ.get("UV_BIN", "uv")
    os.execvp(
        uv,
        [
            uv,
            "run",
            "--preview-features",
            "extra-build-dependencies",
            "--group",
            "dev",
            "python",
            "-m",
            "graphify.serve",
            str(GRAPHIFY_GRAPH),
        ],
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="Show graphify artifact and runtime status.")
    subparsers.add_parser("report", help="Print the top of the graphify report.")
    subparsers.add_parser("mcp", help="Start the graphify MCP server after LFS preflight.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "status":
        status()
    elif args.command == "report":
        report()
    elif args.command == "mcp":
        mcp()
    else:
        raise RuntimeError(f"Unhandled command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
