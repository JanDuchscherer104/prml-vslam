#!/usr/bin/env python3
"""Export and inspect repo-local Codex session history."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

Speaker = Literal["user", "agent"]

_PATCH_FILE_RE = re.compile(r"^\*\*\* (?:Update|Add|Delete) File: (.+)$", re.MULTILINE)
_VALIDATION_PREFIXES = (
    "uv run pytest",
    "make lint",
    "make ci",
    "make graphify-rebuild",
    "uv run ruff check",
    "uv run ruff format",
    "ruff format",
    "ruff check",
)


@dataclass(frozen=True)
class SessionMeta:
    """Repo-scoped Codex session metadata."""

    session_id: str
    session_started_at_utc: str | None
    session_started_at_local: str | None
    session_started_at_unix: float | None
    cwd: str | None
    cwd_scope: str
    worktree_name: str | None
    originator: str | None
    source: str | None
    cli_version: str | None
    model_provider: str | None
    git_branch: str | None
    git_commit_hash: str | None
    git_repository_url: str | None
    session_file: str
    thread_name: str | None
    thread_updated_at_utc: str | None
    thread_updated_at_local: str | None
    thread_updated_at_unix: float | None


@dataclass(frozen=True)
class MessageRecord:
    """One repo-scoped user or agent-visible message."""

    speaker: Speaker
    phase: str
    session_id: str
    timestamp_utc: str | None
    timestamp_local: str | None
    timestamp_unix: float | None
    message: str
    images: list[Any]
    local_images: list[Any]
    text_elements: list[Any]
    memory_citation: Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _worktrees_root(repo_root: Path) -> Path:
    return repo_root.parent / f"{repo_root.name}.worktrees"


def _candidate_codex_homes() -> list[Path]:
    candidates: list[Path] = []
    home_default = Path.home() / ".codex"
    candidates.append(home_default)
    raw = os.environ.get("CODEX_HOME")
    if raw:
        env_home = Path(raw).expanduser()
        if env_home not in candidates:
            candidates.append(env_home)
    return candidates


def _iso_local(value: str | None, *, tz: ZoneInfo) -> str | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(tz).isoformat()


def _iso_unix(value: str | None) -> float | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def _classify_cwd(repo_root: Path, worktrees_root: Path, cwd: str | None) -> tuple[str | None, str | None]:
    if not cwd:
        return None, None
    repo_root_str = str(repo_root)
    if cwd == repo_root_str:
        return "repo_root", None
    worktree_prefix = f"{worktrees_root}/"
    if cwd.startswith(worktree_prefix):
        return "worktree", cwd[len(worktree_prefix) :].split("/", 1)[0]
    return None, None


def _thread_index(codex_home: Path, *, tz: ZoneInfo) -> dict[str, dict[str, Any]]:
    index_path = codex_home / "session_index.jsonl"
    result: dict[str, dict[str, Any]] = {}
    if not index_path.exists():
        return result
    with index_path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            session_id = payload.get("id")
            if not session_id:
                continue
            updated_at = payload.get("updated_at")
            result[session_id] = {
                "thread_name": payload.get("thread_name"),
                "thread_updated_at_utc": updated_at,
                "thread_updated_at_local": _iso_local(updated_at, tz=tz),
                "thread_updated_at_unix": _iso_unix(updated_at),
            }
    return result


def _candidate_session_paths(codex_home: Path) -> Iterator[Path]:
    for root_name in ("sessions", "archived_sessions"):
        root = codex_home / root_name
        if not root.exists():
            continue
        yield from sorted(root.rglob("*.jsonl"))


def _has_repo_scoped_sessions(codex_home: Path, *, repo_root: Path) -> bool:
    worktrees_root = _worktrees_root(repo_root)
    for path in _candidate_session_paths(codex_home):
        first = _load_first_json(path)
        if not first or first.get("type") != "session_meta":
            continue
        payload = first.get("payload", {})
        cwd_scope, _ = _classify_cwd(repo_root, worktrees_root, payload.get("cwd"))
        if cwd_scope is not None:
            return True
    return False


def _resolve_codex_home(explicit: Path | None, *, repo_root: Path) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    for candidate in _candidate_codex_homes():
        if candidate.exists() and _has_repo_scoped_sessions(candidate, repo_root=repo_root):
            return candidate.resolve()
    for candidate in _candidate_codex_homes():
        if candidate.exists():
            return candidate.resolve()
    return (Path.home() / ".codex").resolve()


def _load_first_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open() as handle:
            first = handle.readline().strip()
    except OSError:
        return None
    if not first:
        return None
    try:
        return json.loads(first)
    except json.JSONDecodeError:
        return None


def _session_meta_for_path(
    path: Path,
    *,
    repo_root: Path,
    worktrees_root: Path,
    thread_index: dict[str, dict[str, Any]],
    tz: ZoneInfo,
) -> SessionMeta | None:
    first = _load_first_json(path)
    if not first or first.get("type") != "session_meta":
        return None
    payload = first.get("payload", {})
    session_id = payload.get("id")
    if not session_id:
        return None
    cwd = payload.get("cwd")
    cwd_scope, worktree_name = _classify_cwd(repo_root, worktrees_root, cwd)
    if cwd_scope is None:
        return None
    started_at = payload.get("timestamp")
    thread_payload = thread_index.get(session_id, {})
    git_payload = payload.get("git") or {}
    return SessionMeta(
        session_id=session_id,
        session_started_at_utc=started_at,
        session_started_at_local=_iso_local(started_at, tz=tz),
        session_started_at_unix=_iso_unix(started_at),
        cwd=cwd,
        cwd_scope=cwd_scope,
        worktree_name=worktree_name,
        originator=payload.get("originator"),
        source=payload.get("source"),
        cli_version=payload.get("cli_version"),
        model_provider=payload.get("model_provider"),
        git_branch=git_payload.get("branch"),
        git_commit_hash=git_payload.get("commit_hash"),
        git_repository_url=git_payload.get("repository_url"),
        session_file=str(path),
        thread_name=thread_payload.get("thread_name"),
        thread_updated_at_utc=thread_payload.get("thread_updated_at_utc"),
        thread_updated_at_local=thread_payload.get("thread_updated_at_local"),
        thread_updated_at_unix=thread_payload.get("thread_updated_at_unix"),
    )


def _iter_session_json(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for raw_line in handle:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                yield json.loads(raw_line)
            except json.JSONDecodeError:
                continue


def _message_from_event(event: dict[str, Any], *, tz: ZoneInfo) -> MessageRecord | None:
    if event.get("type") != "event_msg":
        return None
    payload = event.get("payload") or {}
    payload_type = payload.get("type")
    timestamp = event.get("timestamp")
    if payload_type == "user_message":
        return MessageRecord(
            speaker="user",
            phase="user_message",
            session_id="",
            timestamp_utc=timestamp,
            timestamp_local=_iso_local(timestamp, tz=tz),
            timestamp_unix=_iso_unix(timestamp),
            message=payload.get("message") or "",
            images=payload.get("images", []),
            local_images=payload.get("local_images", []),
            text_elements=payload.get("text_elements", []),
            memory_citation=None,
        )
    if payload_type == "agent_message":
        return MessageRecord(
            speaker="agent",
            phase=payload.get("phase") or "agent_message",
            session_id="",
            timestamp_utc=timestamp,
            timestamp_local=_iso_local(timestamp, tz=tz),
            timestamp_unix=_iso_unix(timestamp),
            message=payload.get("message") or "",
            images=[],
            local_images=[],
            text_elements=[],
            memory_citation=payload.get("memory_citation"),
        )
    return None


def _iter_session_messages(path: Path, *, session_id: str, tz: ZoneInfo) -> Iterator[MessageRecord]:
    seen: set[tuple[Any, ...]] = set()
    for event in _iter_session_json(path):
        record = _message_from_event(event, tz=tz)
        if record is None:
            continue
        dedupe_key = (
            record.speaker,
            record.phase,
            record.timestamp_utc,
            record.message,
            json.dumps(record.images, sort_keys=True),
            json.dumps(record.local_images, sort_keys=True),
            json.dumps(record.text_elements, sort_keys=True),
            json.dumps(record.memory_citation, sort_keys=True),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        yield MessageRecord(
            speaker=record.speaker,
            phase=record.phase,
            session_id=session_id,
            timestamp_utc=record.timestamp_utc,
            timestamp_local=record.timestamp_local,
            timestamp_unix=record.timestamp_unix,
            message=record.message,
            images=record.images,
            local_images=record.local_images,
            text_elements=record.text_elements,
            memory_citation=record.memory_citation,
        )


def _message_dicts(meta: SessionMeta, messages: Sequence[MessageRecord]) -> list[dict[str, Any]]:
    per_session_index = 0
    per_speaker_index: dict[Speaker, int] = defaultdict(int)
    records: list[dict[str, Any]] = []
    for message in sorted(
        messages, key=lambda item: (item.timestamp_utc or "", item.speaker, item.phase, item.message)
    ):
        per_session_index += 1
        per_speaker_index[message.speaker] += 1
        records.append(
            {
                "speaker": message.speaker,
                "phase": message.phase,
                "session_id": meta.session_id,
                "session_started_at_utc": meta.session_started_at_utc,
                "session_started_at_local": meta.session_started_at_local,
                "session_started_at_unix": meta.session_started_at_unix,
                "cwd": meta.cwd,
                "cwd_scope": meta.cwd_scope,
                "worktree_name": meta.worktree_name,
                "originator": meta.originator,
                "source": meta.source,
                "cli_version": meta.cli_version,
                "model_provider": meta.model_provider,
                "git_branch": meta.git_branch,
                "git_commit_hash": meta.git_commit_hash,
                "git_repository_url": meta.git_repository_url,
                "session_file": meta.session_file,
                "thread_name": meta.thread_name,
                "thread_updated_at_utc": meta.thread_updated_at_utc,
                "thread_updated_at_local": meta.thread_updated_at_local,
                "thread_updated_at_unix": meta.thread_updated_at_unix,
                "timestamp_utc": message.timestamp_utc,
                "timestamp_local": message.timestamp_local,
                "timestamp_unix": message.timestamp_unix,
                "message": message.message,
                "images": message.images,
                "local_images": message.local_images,
                "text_elements": message.text_elements,
                "memory_citation": message.memory_citation,
                "message_index_in_session": per_session_index,
                "message_index_in_session_for_speaker": per_speaker_index[message.speaker],
                "repo_project": _repo_root().name,
            }
        )
    return records


def _session_lookup(
    codex_home: Path,
    *,
    repo_root: Path,
    worktrees_root: Path,
    tz: ZoneInfo,
) -> dict[str, tuple[SessionMeta, Path]]:
    thread_idx = _thread_index(codex_home, tz=tz)
    sessions: dict[str, tuple[SessionMeta, Path]] = {}
    for path in _candidate_session_paths(codex_home):
        meta = _session_meta_for_path(
            path, repo_root=repo_root, worktrees_root=worktrees_root, thread_index=thread_idx, tz=tz
        )
        if meta is not None:
            sessions[meta.session_id] = (meta, path)
    return sessions


def build_repo_exports(
    *,
    codex_home: Path,
    repo_root: Path,
    timezone: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tz = ZoneInfo(timezone)
    sessions = _session_lookup(codex_home, repo_root=repo_root, worktrees_root=_worktrees_root(repo_root), tz=tz)
    combined: list[dict[str, Any]] = []
    users: list[dict[str, Any]] = []
    for meta, path in sessions.values():
        session_messages = list(_iter_session_messages(path, session_id=meta.session_id, tz=tz))
        records = _message_dicts(meta, session_messages)
        combined.extend(records)
        users.extend(record for record in records if record["speaker"] == "user")
    combined.sort(
        key=lambda record: (record["timestamp_utc"] or "", record["session_id"], record["message_index_in_session"])
    )
    users.sort(
        key=lambda record: (record["timestamp_utc"] or "", record["session_id"], record["message_index_in_session"])
    )
    return combined, users


def _find_session_or_die(
    session_id: str, *, codex_home: Path, repo_root: Path, timezone: str
) -> tuple[SessionMeta, Path]:
    sessions = _session_lookup(
        codex_home, repo_root=repo_root, worktrees_root=_worktrees_root(repo_root), tz=ZoneInfo(timezone)
    )
    try:
        return sessions[session_id]
    except KeyError as exc:
        raise SystemExit(f"Session '{session_id}' was not found under repo-scoped Codex history.") from exc


def session_records(
    session_id: str,
    *,
    codex_home: Path,
    repo_root: Path,
    timezone: str,
) -> tuple[SessionMeta, list[dict[str, Any]]]:
    tz = ZoneInfo(timezone)
    meta, path = _find_session_or_die(session_id, codex_home=codex_home, repo_root=repo_root, timezone=timezone)
    messages = list(_iter_session_messages(path, session_id=meta.session_id, tz=tz))
    return meta, _message_dicts(meta, messages)


def _speaker_filter(records: Sequence[dict[str, Any]], speaker: str) -> list[dict[str, Any]]:
    if speaker == "both":
        return list(records)
    return [record for record in records if record["speaker"] == speaker]


def _render_conversation_markdown(meta: SessionMeta, records: Sequence[dict[str, Any]], *, speaker: str) -> str:
    label = "Conversation" if speaker == "both" else f"{speaker.capitalize()} Message History"
    parts = [
        f"# {label}\n\n",
        "Session:\n",
        f"- `{meta.session_id}`\n",
        f"- thread: `{meta.thread_name}`\n",
        f"- session file: `{meta.session_file}`\n",
        f"- speaker filter: `{speaker}`\n",
        f"- messages: `{len(records)}`\n\n",
    ]
    for record in records:
        parts.append(f"## {record['timestamp_utc']} ({record['speaker']}, {record['phase']})\n\n")
        parts.append(record["message"].rstrip() + "\n\n")
        parts.append("---\n\n")
    return "".join(parts)


def _extract_apply_patch_files(path: Path) -> list[str]:
    changed_files: list[str] = []
    seen: set[str] = set()
    for event in _iter_session_json(path):
        if event.get("type") != "response_item":
            continue
        payload = event.get("payload") or {}
        if payload.get("type") != "custom_tool_call":
            continue
        if payload.get("name") != "apply_patch" or payload.get("status") != "completed":
            continue
        patch_text = payload.get("input") or ""
        for match in _PATCH_FILE_RE.findall(patch_text):
            if match not in seen:
                seen.add(match)
                changed_files.append(match)
    return changed_files


def _extract_validation_commands(path: Path) -> list[str]:
    commands: list[str] = []
    seen: set[str] = set()
    for event in _iter_session_json(path):
        if event.get("type") != "event_msg":
            continue
        payload = event.get("payload") or {}
        if payload.get("type") != "exec_command_end" or payload.get("exit_code") != 0:
            continue
        command_text = ""
        parsed_cmd = payload.get("parsed_cmd") or []
        if parsed_cmd and isinstance(parsed_cmd, list) and parsed_cmd[0].get("cmd"):
            command_text = parsed_cmd[0]["cmd"]
        else:
            command = payload.get("command") or []
            if isinstance(command, list):
                command_text = " ".join(command[2:]) if len(command) >= 3 else " ".join(command)
        if any(command_text.startswith(prefix) for prefix in _VALIDATION_PREFIXES) and command_text not in seen:
            seen.add(command_text)
            commands.append(command_text)
    return commands


def _last_final_answer(records: Sequence[dict[str, Any]]) -> str | None:
    final_answers = [
        record["message"] for record in records if record["speaker"] == "agent" and record["phase"] == "final_answer"
    ]
    if not final_answers:
        return None
    last_answer = final_answers[-1].strip()
    if not last_answer:
        return None
    return last_answer.split("\n\n", 1)[0].strip()


def session_overview(
    session_id: str,
    *,
    codex_home: Path,
    repo_root: Path,
    timezone: str,
) -> str:
    meta, path = _find_session_or_die(session_id, codex_home=codex_home, repo_root=repo_root, timezone=timezone)
    _, records = session_records(session_id, codex_home=codex_home, repo_root=repo_root, timezone=timezone)
    changed_files = _extract_apply_patch_files(path)
    validation_commands = _extract_validation_commands(path)
    counts = defaultdict(int)
    for record in records:
        counts[record["speaker"]] += 1
        counts[(record["speaker"], record["phase"])] += 1
    summary = _last_final_answer(records)
    parts = [
        "# Session Overview\n\n",
        f"- session id: `{meta.session_id}`\n",
        f"- thread: `{meta.thread_name}`\n",
        f"- started: `{meta.session_started_at_utc}`\n",
        f"- cwd: `{meta.cwd}`\n",
        f"- branch at start: `{meta.git_branch}`\n",
        f"- commit at start: `{meta.git_commit_hash}`\n",
        f"- session file: `{meta.session_file}`\n",
        f"- messages: `{len(records)}` total, `{counts['user']}` user, `{counts['agent']}` agent\n",
        f"- agent commentary: `{counts[('agent', 'commentary')]}`\n",
        f"- agent final answers: `{counts[('agent', 'final_answer')]}`\n\n",
    ]
    if summary:
        parts.append("## Last Final Summary\n\n")
        parts.append(summary + "\n\n")
    parts.append("## Changed Files\n\n")
    if changed_files:
        for changed_file in changed_files:
            parts.append(f"- `{changed_file}`\n")
    else:
        parts.append("- No successful `apply_patch` edits were recorded in this session.\n")
    parts.append("\n## Successful Verification Commands\n\n")
    if validation_commands:
        for command in validation_commands:
            parts.append(f"- `{command}`\n")
    else:
        parts.append("- No matching successful verification commands were found.\n")
    return "".join(parts)


def _write_jsonl(path: Path, records: Sequence[dict[str, Any]]) -> None:
    with path.open("w") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _print_or_write(text: str, *, output_path: Path | None) -> None:
    if output_path is None:
        print(text, end="")
        return
    output_path.write_text(text)
    print(output_path)


def _default_export_path(repo_root: Path, *, speaker: str, session_id: str | None = None, fmt: str = "md") -> Path:
    if session_id is None:
        if speaker == "user":
            return repo_root / f"codex-user-messages-{repo_root.name}.jsonl"
        return repo_root / f"codex-messages-{repo_root.name}.jsonl"
    if speaker == "both":
        return repo_root / f"codex-session-{session_id}-messages.{fmt}"
    return repo_root / f"codex-session-{session_id}-{speaker}-messages.{fmt}"


def _update_command(args: argparse.Namespace) -> None:
    repo_root = args.repo_root.resolve()
    combined, users = build_repo_exports(codex_home=args.codex_home, repo_root=repo_root, timezone=args.timezone)
    combined_path = _default_export_path(repo_root, speaker="both", fmt="jsonl")
    user_path = _default_export_path(repo_root, speaker="user", fmt="jsonl")
    _write_jsonl(combined_path, combined)
    _write_jsonl(user_path, users)
    print(f"wrote {combined_path} ({len(combined)} messages)")
    print(f"wrote {user_path} ({len(users)} messages)")


def _conversation_command(args: argparse.Namespace) -> None:
    repo_root = args.repo_root.resolve()
    meta, records = session_records(
        args.session_id,
        codex_home=args.codex_home,
        repo_root=repo_root,
        timezone=args.timezone,
    )
    filtered = _speaker_filter(records, args.speaker)
    if args.format == "jsonl":
        text = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in filtered)
    else:
        text = _render_conversation_markdown(meta, filtered, speaker=args.speaker)
    output_path = args.output
    if output_path is None and args.write_default:
        output_path = _default_export_path(repo_root, speaker=args.speaker, session_id=args.session_id, fmt=args.format)
    _print_or_write(text, output_path=output_path)


def _overview_command(args: argparse.Namespace) -> None:
    text = session_overview(
        args.session_id,
        codex_home=args.codex_home,
        repo_root=args.repo_root.resolve(),
        timezone=args.timezone,
    )
    _print_or_write(text, output_path=args.output)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--repo-root", type=Path, default=_repo_root())
    parser.add_argument("--timezone", default="Europe/Berlin")
    subparsers = parser.add_subparsers(dest="command", required=True)

    update_parser = subparsers.add_parser("update", help="Refresh repo-scoped Codex history exports.")
    update_parser.set_defaults(func=_update_command)

    conversation_parser = subparsers.add_parser("conversation", help="Fetch one session conversation.")
    conversation_parser.add_argument("session_id")
    conversation_parser.add_argument("--speaker", choices=("user", "agent", "both"), default="both")
    conversation_parser.add_argument("--format", choices=("md", "jsonl"), default="md")
    conversation_parser.add_argument("--output", type=Path)
    conversation_parser.add_argument(
        "--write-default",
        action="store_true",
        help="Write to the default repo-root path instead of printing to stdout.",
    )
    conversation_parser.set_defaults(func=_conversation_command)

    overview_parser = subparsers.add_parser(
        "overview",
        help="Fetch one session conversation summary plus minimal change overview.",
    )
    overview_parser.add_argument("session_id")
    overview_parser.add_argument("--output", type=Path)
    overview_parser.set_defaults(func=_overview_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.repo_root = args.repo_root.resolve()
    args.codex_home = _resolve_codex_home(args.codex_home, repo_root=args.repo_root)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
