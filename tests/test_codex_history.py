"""Tests for the repo-local Codex history utility."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_history_module():
    module_path = Path(__file__).resolve().parents[1] / ".agents" / "scripts" / "codex_history.py"
    spec = importlib.util.spec_from_file_location("codex_history", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_build_repo_exports_collects_repo_scoped_user_and_agent_messages(tmp_path: Path) -> None:
    history = _load_history_module()
    repo_root = tmp_path / "prml-vslam"
    codex_home = tmp_path / ".codex"
    session_id = "session-1"

    _write_jsonl(
        codex_home / "session_index.jsonl",
        [{"id": session_id, "thread_name": "Example", "updated_at": "2026-04-18T12:00:00Z"}],
    )
    _write_jsonl(
        codex_home / "sessions" / "2026" / "04" / "18" / "rollout-example.jsonl",
        [
            {
                "type": "session_meta",
                "payload": {
                    "id": session_id,
                    "timestamp": "2026-04-18T11:00:00Z",
                    "cwd": str(repo_root),
                    "originator": "codex_vscode",
                    "source": "vscode",
                    "cli_version": "0.1.0",
                    "model_provider": "openai",
                    "git": {
                        "branch": "main",
                        "commit_hash": "abc123",
                        "repository_url": "git@example.com:repo.git",
                    },
                },
            },
            {
                "type": "event_msg",
                "timestamp": "2026-04-18T11:01:00Z",
                "payload": {
                    "type": "user_message",
                    "message": "hello",
                    "images": [],
                    "local_images": [],
                    "text_elements": [],
                },
            },
            {
                "type": "event_msg",
                "timestamp": "2026-04-18T11:02:00Z",
                "payload": {
                    "type": "agent_message",
                    "message": "world",
                    "phase": "final_answer",
                    "memory_citation": None,
                },
            },
        ],
    )

    combined, users = history.build_repo_exports(codex_home=codex_home, repo_root=repo_root, timezone="Europe/Berlin")

    assert len(combined) == 2
    assert len(users) == 1
    assert combined[0]["speaker"] == "user"
    assert combined[1]["speaker"] == "agent"
    assert combined[1]["phase"] == "final_answer"
    assert combined[1]["thread_name"] == "Example"


def test_session_overview_extracts_patch_touched_files_and_verification_commands(tmp_path: Path) -> None:
    history = _load_history_module()
    repo_root = tmp_path / "prml-vslam"
    codex_home = tmp_path / ".codex"
    session_id = "session-2"
    session_path = codex_home / "sessions" / "2026" / "04" / "18" / "rollout-example-2.jsonl"

    _write_jsonl(
        codex_home / "session_index.jsonl",
        [{"id": session_id, "thread_name": "Patch Session", "updated_at": "2026-04-18T12:00:00Z"}],
    )
    _write_jsonl(
        session_path,
        [
            {
                "type": "session_meta",
                "payload": {
                    "id": session_id,
                    "timestamp": "2026-04-18T11:00:00Z",
                    "cwd": str(repo_root),
                    "git": {"branch": "codex/test", "commit_hash": "def456"},
                },
            },
            {
                "type": "event_msg",
                "timestamp": "2026-04-18T11:01:00Z",
                "payload": {
                    "type": "user_message",
                    "message": "do work",
                    "images": [],
                    "local_images": [],
                    "text_elements": [],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "custom_tool_call",
                    "name": "apply_patch",
                    "status": "completed",
                    "input": (
                        "*** Begin Patch\n"
                        "*** Update File: /repo/src/example.py\n"
                        "@@\n"
                        "-old\n"
                        "+new\n"
                        "*** Add File: /repo/tests/test_example.py\n"
                        "+value\n"
                        "*** End Patch\n"
                    ),
                },
            },
            {
                "type": "event_msg",
                "payload": {
                    "type": "exec_command_end",
                    "exit_code": 0,
                    "parsed_cmd": [{"cmd": "uv run pytest tests/test_example.py -q"}],
                },
            },
            {
                "type": "event_msg",
                "timestamp": "2026-04-18T11:03:00Z",
                "payload": {
                    "type": "agent_message",
                    "message": "Implemented the example change.\n\nVerification passed.",
                    "phase": "final_answer",
                },
            },
        ],
    )

    overview = history.session_overview(
        session_id, codex_home=codex_home, repo_root=repo_root, timezone="Europe/Berlin"
    )

    assert "`/repo/src/example.py`" in overview
    assert "`/repo/tests/test_example.py`" in overview
    assert "`uv run pytest tests/test_example.py -q`" in overview
    assert "Implemented the example change." in overview


def test_render_conversation_markdown_respects_speaker_filter(tmp_path: Path) -> None:
    history = _load_history_module()
    repo_root = tmp_path / "prml-vslam"
    codex_home = tmp_path / ".codex"
    session_id = "session-3"

    _write_jsonl(
        codex_home / "session_index.jsonl",
        [{"id": session_id, "thread_name": "Conversation", "updated_at": "2026-04-18T12:00:00Z"}],
    )
    _write_jsonl(
        codex_home / "sessions" / "2026" / "04" / "18" / "rollout-example-3.jsonl",
        [
            {
                "type": "session_meta",
                "payload": {"id": session_id, "timestamp": "2026-04-18T11:00:00Z", "cwd": str(repo_root)},
            },
            {
                "type": "event_msg",
                "timestamp": "2026-04-18T11:01:00Z",
                "payload": {
                    "type": "user_message",
                    "message": "hello",
                    "images": [],
                    "local_images": [],
                    "text_elements": [],
                },
            },
            {
                "type": "event_msg",
                "timestamp": "2026-04-18T11:02:00Z",
                "payload": {"type": "agent_message", "message": "answer", "phase": "commentary"},
            },
        ],
    )

    meta, records = history.session_records(
        session_id, codex_home=codex_home, repo_root=repo_root, timezone="Europe/Berlin"
    )
    filtered = history._speaker_filter(records, "agent")
    markdown = history._render_conversation_markdown(meta, filtered, speaker="agent")

    assert "speaker filter: `agent`" in markdown
    assert "(agent, commentary)" in markdown
    assert "answer" in markdown
    assert "hello" not in markdown
