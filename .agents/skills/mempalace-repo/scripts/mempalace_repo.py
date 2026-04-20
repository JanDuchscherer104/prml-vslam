#!/usr/bin/env python3
"""Repo-local MemPalace helper for docs and Codex chat histories."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

DOC_SUFFIXES = {".md", ".typ", ".bib", ".txt"}
ROOT_DOC_FILES = ("README.md", "SETUP.md", "AGENTS.md")
PACKAGE_DOC_NAMES = {"README.md", "REQUIREMENTS.md", "AGENTS.md"}
DOCS_WING = "prml-vslam-docs"
CHATS_WING = "prml-vslam-chats"
AGENT_NAME = "prml-vslam-codex"
TIMEZONE = "Europe/Berlin"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def venv_python() -> Path:
    return repo_root() / ".venv" / "bin" / "python"


def palace_path() -> Path:
    return repo_root() / ".artifacts" / "mempalace" / "palace"


def sources_root() -> Path:
    return repo_root() / ".artifacts" / "mempalace" / "sources"


def docs_source_root() -> Path:
    return sources_root() / "docs"


def chats_source_root() -> Path:
    return sources_root() / "chats"


def _load_codex_history_module():
    module_path = repo_root() / ".agents" / "scripts" / "codex_history.py"
    spec = importlib.util.spec_from_file_location("codex_history", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _mempalace_env() -> dict[str, str]:
    env = os.environ.copy()
    env["MEMPALACE_PALACE_PATH"] = str(palace_path())
    return env


def run_python_module(module: str, *args: str, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    command = [str(venv_python()), "-m", module, *args]
    return subprocess.run(
        command,
        cwd=repo_root(),
        env=_mempalace_env(),
        text=True,
        check=True,
        capture_output=capture_output,
    )


def ensure_runtime() -> None:
    if not venv_python().exists():
        raise RuntimeError(f"Missing repo venv python at {venv_python()}")
    run_python_module("mempalace", "--version", capture_output=True)


def _clear_directory(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)


def _copy_file(source: Path, dest_root: Path) -> None:
    relative_path = source.relative_to(repo_root())
    destination = dest_root / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _iter_docs_files() -> list[Path]:
    docs_files: set[Path] = set()
    for name in ROOT_DOC_FILES:
        path = repo_root() / name
        if path.exists():
            docs_files.add(path)
    docs_dir = repo_root() / "docs"
    if docs_dir.exists():
        for path in docs_dir.rglob("*"):
            if path.is_file() and path.suffix in DOC_SUFFIXES:
                docs_files.add(path)
    package_dir = repo_root() / "src" / "prml_vslam"
    if package_dir.exists():
        for path in package_dir.rglob("*"):
            if path.is_file() and path.name in PACKAGE_DOC_NAMES:
                docs_files.add(path)
    return sorted(docs_files)


def sync_docs_sources() -> list[Path]:
    target_root = docs_source_root()
    _clear_directory(target_root)
    copied: list[Path] = []
    for source in _iter_docs_files():
        _copy_file(source, target_root)
        copied.append(source)
    return copied


def refresh_history_exports() -> None:
    history = _load_codex_history_module()
    codex_home = history._resolve_codex_home(None, repo_root=repo_root())
    combined, users = history.build_repo_exports(codex_home=codex_home, repo_root=repo_root(), timezone=TIMEZONE)
    history._write_jsonl(repo_root() / "codex-messages-prml-vslam.jsonl", combined)
    history._write_jsonl(repo_root() / "codex-user-messages-prml-vslam.jsonl", users)


def sync_chat_sources() -> list[Path]:
    target_root = chats_source_root()
    _clear_directory(target_root)
    history = _load_codex_history_module()
    codex_home = history._resolve_codex_home(None, repo_root=repo_root())
    sessions = history._session_lookup(
        codex_home,
        repo_root=repo_root(),
        worktrees_root=history._worktrees_root(repo_root()),
        tz=history.ZoneInfo(TIMEZONE),
    )
    copied: list[Path] = []
    for session_id, (_meta, session_path) in sorted(sessions.items()):
        destination = target_root / f"{session_id}.jsonl"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(session_path, destination)
        copied.append(session_path)
    return copied


def initialize_docs_source() -> None:
    docs_root = docs_source_root()
    if (docs_root / "mempalace.yaml").exists():
        return
    run_python_module("mempalace", "init", str(docs_root), "--yes")


def mine_docs() -> None:
    run_python_module(
        "mempalace",
        "mine",
        str(docs_source_root()),
        "--wing",
        DOCS_WING,
        "--agent",
        AGENT_NAME,
    )


def mine_chats() -> None:
    run_python_module(
        "mempalace",
        "mine",
        str(chats_source_root()),
        "--mode",
        "convos",
        "--wing",
        CHATS_WING,
        "--agent",
        AGENT_NAME,
    )


def refresh() -> None:
    ensure_runtime()
    refresh_history_exports()
    copied_docs = sync_docs_sources()
    copied_chats = sync_chat_sources()
    initialize_docs_source()
    mine_docs()
    mine_chats()
    print(f"docs_copied={len(copied_docs)}")
    print(f"chat_sessions_copied={len(copied_chats)}")
    print(f"palace={palace_path()}")


def status() -> None:
    ensure_runtime()
    run_python_module("mempalace", "status")


def search(query: str) -> None:
    ensure_runtime()
    run_python_module("mempalace", "search", query)


def wake_up() -> None:
    ensure_runtime()
    run_python_module("mempalace", "wake-up")


def mcp() -> None:
    ensure_runtime()
    run_python_module("mempalace", "--palace", str(palace_path()), "mcp")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("refresh", help="Refresh docs/chat sources and mine them into the repo-local palace.")
    subparsers.add_parser("status", help="Show the repo-local palace status.")
    search_parser = subparsers.add_parser("search", help="Search the repo-local palace.")
    search_parser.add_argument("query")
    subparsers.add_parser("wake-up", help="Show wake-up context from the repo-local palace.")
    subparsers.add_parser("mcp", help="Show the repo-local MCP setup command.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "refresh":
        refresh()
    elif args.command == "status":
        status()
    elif args.command == "search":
        search(args.query)
    elif args.command == "wake-up":
        wake_up()
    elif args.command == "mcp":
        mcp()
    else:
        raise RuntimeError(f"Unhandled command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
