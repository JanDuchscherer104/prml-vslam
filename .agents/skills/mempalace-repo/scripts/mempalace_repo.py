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
AGENT_MEMORY_FILES = (
    ".agents/AGENTS_INTERNAL_DB.md",
    ".agents/issues.toml",
    ".agents/todos.toml",
    ".agents/refactors.toml",
    ".agents/resolved.toml",
    ".codex/config.toml",
    ".codex/hooks.json",
)
DOCS_WING = "prml-vslam-docs"
CHATS_WING = "prml-vslam-chats"
AGENT_NAME = "prml-vslam-codex"
TIMEZONE = "Europe/Berlin"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def shared_repo_root() -> Path:
    try:
        common_dir = subprocess.check_output(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=repo_root(),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return repo_root()
    if not common_dir:
        return repo_root()
    return Path(common_dir).resolve().parent


def mempalace_root() -> Path:
    local_root = repo_root() / ".artifacts" / "mempalace"
    if (local_root / "palace").exists():
        return local_root
    shared_root = shared_repo_root() / ".artifacts" / "mempalace"
    if (shared_root / "palace").exists():
        return shared_root
    return local_root


def palace_path() -> Path:
    return mempalace_root() / "palace"


def sources_root() -> Path:
    return mempalace_root() / "sources"


def docs_source_root() -> Path:
    return sources_root() / "docs"


def chats_source_root() -> Path:
    return sources_root() / "chats"


def exports_source_root() -> Path:
    return sources_root() / "exports"


def _load_codex_history_module():
    module_path = repo_root() / ".agents" / "scripts" / "codex_history.py"
    spec = importlib.util.spec_from_file_location("codex_history", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _candidate_codex_homes(history) -> list[Path]:
    candidates = list(history._candidate_codex_homes())
    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def _repo_codex_homes(history) -> list[Path]:
    root = repo_root()
    scoped = [
        candidate
        for candidate in _candidate_codex_homes(history)
        if history._has_repo_scoped_sessions(candidate, repo_root=root)
    ]
    if scoped:
        return scoped
    return [history._resolve_codex_home(None, repo_root=root)]


def _dedupe_records(records: list[dict]) -> list[dict]:
    unique: dict[tuple, dict] = {}
    for record in records:
        key = (
            record.get("session_id"),
            record.get("speaker"),
            record.get("phase"),
            record.get("timestamp_utc"),
            record.get("message_index_in_session"),
            record.get("message"),
        )
        unique.setdefault(key, record)
    return sorted(
        unique.values(),
        key=lambda record: (
            record.get("timestamp_utc") or "",
            record.get("session_id") or "",
            record.get("message_index_in_session") or 0,
        ),
    )


def _mempalace_env() -> dict[str, str]:
    env = os.environ.copy()
    env["MEMPALACE_PALACE_PATH"] = str(palace_path())
    return env


def _require_executable(env_name: str, default_name: str) -> str:
    configured = os.environ.get(env_name)
    if configured:
        return configured
    executable = shutil.which(default_name)
    if executable is None:
        raise RuntimeError(f"Missing `{default_name}` executable on PATH; install it or set {env_name}.")
    return executable


def mempalace_executable() -> str:
    return _require_executable("MEMPALACE_BIN", "mempalace")


def mempalace_mcp_executable() -> str:
    return _require_executable("MEMPALACE_MCP_BIN", "mempalace-mcp")


def run_mempalace(*args: str, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    command = [mempalace_executable(), "--palace", str(palace_path()), *args]
    return subprocess.run(
        command,
        cwd=repo_root(),
        env=_mempalace_env(),
        text=True,
        check=True,
        capture_output=capture_output,
    )


def _init_llm_args() -> list[str]:
    if os.environ.get("MEMPALACE_INIT_LLM") != "1":
        return ["--no-llm"]

    args: list[str] = []
    provider = os.environ.get("MEMPALACE_INIT_LLM_PROVIDER")
    model = os.environ.get("MEMPALACE_INIT_LLM_MODEL")
    endpoint = os.environ.get("MEMPALACE_INIT_LLM_ENDPOINT")
    api_key = os.environ.get("MEMPALACE_INIT_LLM_API_KEY")
    if provider:
        args.extend(["--llm-provider", provider])
    if model:
        args.extend(["--llm-model", model])
    if endpoint:
        args.extend(["--llm-endpoint", endpoint])
    if api_key:
        args.extend(["--llm-api-key", api_key])
    if os.environ.get("MEMPALACE_ACCEPT_EXTERNAL_LLM") == "1":
        args.append("--accept-external-llm")
    return args


def ensure_runtime() -> None:
    subprocess.run(
        [mempalace_executable(), "--version"],
        cwd=repo_root(),
        env=_mempalace_env(),
        text=True,
        check=True,
        stdout=subprocess.DEVNULL,
    )


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
    agents_dir = repo_root() / ".agents"
    if agents_dir.exists():
        for path in agents_dir.rglob("*"):
            if path.is_file() and (path.name == "SKILL.md" or path.suffix in DOC_SUFFIXES):
                docs_files.add(path)
    for name in AGENT_MEMORY_FILES:
        path = repo_root() / name
        if path.exists():
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
    combined = []
    users = []
    for codex_home in _repo_codex_homes(history):
        home_combined, home_users = history.build_repo_exports(
            codex_home=codex_home, repo_root=repo_root(), timezone=TIMEZONE
        )
        combined.extend(home_combined)
        users.extend(home_users)
    combined = _dedupe_records(combined)
    users = _dedupe_records(users)
    export_root = exports_source_root()
    export_root.mkdir(parents=True, exist_ok=True)
    history._write_jsonl(export_root / "codex-messages-prml-vslam.jsonl", combined)
    history._write_jsonl(export_root / "codex-user-messages-prml-vslam.jsonl", users)


def sync_chat_sources() -> list[Path]:
    target_root = chats_source_root()
    _clear_directory(target_root)
    history = _load_codex_history_module()
    sessions = {}
    for codex_home in _repo_codex_homes(history):
        sessions.update(
            history._session_lookup(
                codex_home,
                repo_root=repo_root(),
                worktrees_root=history._worktrees_root(repo_root()),
                tz=history.ZoneInfo(TIMEZONE),
            )
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
    run_mempalace("init", str(docs_root), "--yes", *_init_llm_args())


def mine_docs() -> None:
    run_mempalace(
        "mine",
        str(docs_source_root()),
        "--wing",
        DOCS_WING,
        "--agent",
        AGENT_NAME,
    )


def mine_chats() -> None:
    run_mempalace(
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
    run_mempalace("status")


def search(query: str) -> None:
    ensure_runtime()
    run_mempalace("search", query)


def wake_up() -> None:
    ensure_runtime()
    run_mempalace("wake-up")


def mcp() -> None:
    ensure_runtime()
    env = _mempalace_env()
    executable = mempalace_mcp_executable()
    os.execve(executable, [executable, "--palace", str(palace_path())], env)


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
