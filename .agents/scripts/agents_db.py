from __future__ import annotations

import argparse
import json
import tomllib
from datetime import date
from pathlib import Path
from typing import Any, Literal

import tomli_w

Kind = Literal["issue", "todo"]
Format = Literal["text", "json"]

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / ".agents"
ISSUES_PATH = AGENTS_DIR / "issues.toml"
TODOS_PATH = AGENTS_DIR / "todos.toml"
RESOLVED_PATH = AGENTS_DIR / "resolved.toml"

PRIORITY_ORDER = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}
ISSUE_STATUS_ORDER = {
    "open": 3,
    "in_progress": 2,
    "blocked": 1,
    "closed": 0,
}
TODO_STATUS_ORDER = {
    "pending": 3,
    "in_progress": 2,
    "blocked": 1,
    "done": 0,
}


def load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML document from disk."""
    with path.open("rb") as handle:
        return tomllib.load(handle)


def dump_toml(path: Path, data: dict[str, Any]) -> None:
    """Write a TOML document to disk."""
    with path.open("wb") as handle:
        tomli_w.dump(data, handle)


def _priority_value(priority: str) -> int:
    return PRIORITY_ORDER.get(priority, 0)


def _issue_status_value(status: str) -> int:
    return ISSUE_STATUS_ORDER.get(status, 0)


def _todo_status_value(status: str) -> int:
    return TODO_STATUS_ORDER.get(status, 0)


def validate_todo_record(todo: dict[str, Any]) -> None:
    """Validate required LOC estimates on a todo record."""
    required_fields = ("loc_min", "loc_expected", "loc_max")
    missing_fields = [field for field in required_fields if field not in todo]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Todo {todo.get('id', '<unknown>')} is missing required LOC fields: {missing}")

    loc_min = todo["loc_min"]
    loc_expected = todo["loc_expected"]
    loc_max = todo["loc_max"]
    if not all(isinstance(value, int) for value in (loc_min, loc_expected, loc_max)):
        raise ValueError(f"Todo {todo.get('id', '<unknown>')} must use integer LOC estimates.")
    if not (0 <= loc_min <= loc_expected <= loc_max):
        raise ValueError(f"Todo {todo.get('id', '<unknown>')} must satisfy 0 <= loc_min <= loc_expected <= loc_max.")


def rank_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return active issues ordered by priority and status."""
    return sorted(
        issues,
        key=lambda issue: (
            -_priority_value(str(issue.get("priority", ""))),
            -_issue_status_value(str(issue.get("status", ""))),
            str(issue.get("id", "")),
        ),
    )


def rank_todos(todos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return active todos ordered by priority, status, and expected LOC."""
    for todo in todos:
        validate_todo_record(todo)
    return sorted(
        todos,
        key=lambda todo: (
            -_priority_value(str(todo.get("priority", ""))),
            -_todo_status_value(str(todo.get("status", ""))),
            int(todo["loc_expected"]),
            int(todo["loc_min"]),
            str(todo.get("id", "")),
        ),
    )


def build_ranked_view(
    *,
    issues_path: Path = ISSUES_PATH,
    todos_path: Path = TODOS_PATH,
) -> dict[str, list[dict[str, Any]]]:
    """Build the ranked active backlog view."""
    issues_data = load_toml(issues_path)
    todos_data = load_toml(todos_path)
    issues = rank_issues(list(issues_data.get("issues", [])))
    todos = rank_todos(list(todos_data.get("todos", [])))
    return {"issues": issues, "todos": todos}


def render_ranked_text(kind: str, ranked: dict[str, list[dict[str, Any]]], limit: int | None) -> str:
    """Render ranked backlog data in a compact text format."""
    lines: list[str] = []
    if kind in {"issues", "all"}:
        lines.append("Issues")
        issue_items = ranked["issues"][:limit] if limit is not None else ranked["issues"]
        for index, issue in enumerate(issue_items, start=1):
            lines.append(f"{index}. {issue['id']} [{issue['priority']}/{issue['status']}] {issue['title']}")
            lines.append(f"   {issue['summary']}")

    if kind in {"todos", "all"}:
        if lines:
            lines.append("")
        lines.append("Todos")
        todo_items = ranked["todos"][:limit] if limit is not None else ranked["todos"]
        for index, todo in enumerate(todo_items, start=1):
            loc_triplet = f"{todo['loc_min']}/{todo['loc_expected']}/{todo['loc_max']}"
            lines.append(
                f"{index}. {todo['id']} [{todo['priority']}/{todo['status']}] loc={loc_triplet} {todo['title']}"
            )
            linked_issues = ", ".join(todo.get("issue_ids", []))
            lines.append(f"   issues={linked_issues}")
    return "\n".join(lines)


def _active_collection_key(kind: Kind) -> str:
    return "issues" if kind == "issue" else "todos"


def _resolved_collection_key(kind: Kind) -> str:
    return "resolved_issues" if kind == "issue" else "resolved_todos"


def _active_path(kind: Kind, *, issues_path: Path, todos_path: Path) -> Path:
    return issues_path if kind == "issue" else todos_path


def resolve_record(
    *,
    kind: Kind,
    record_id: str,
    note: str,
    resolved_on: str | None = None,
    issues_path: Path = ISSUES_PATH,
    todos_path: Path = TODOS_PATH,
    resolved_path: Path = RESOLVED_PATH,
) -> dict[str, Any]:
    """Move an active issue or todo into the resolved collection."""
    resolved_stamp = resolved_on or date.today().isoformat()

    active_path = _active_path(kind, issues_path=issues_path, todos_path=todos_path)
    active_data = load_toml(active_path)
    resolved_data = load_toml(resolved_path)

    active_key = _active_collection_key(kind)
    resolved_key = _resolved_collection_key(kind)
    active_records = list(active_data.get(active_key, []))
    resolved_records = list(resolved_data.get(resolved_key, []))

    record_index = next((index for index, record in enumerate(active_records) if record.get("id") == record_id), None)
    if record_index is None:
        raise ValueError(f"Could not find {kind} {record_id} in {active_path}.")

    record = dict(active_records.pop(record_index))
    previous_status = str(record.get("status", ""))
    record["previous_status"] = previous_status
    record["status"] = "resolved"
    record["resolved_on"] = resolved_stamp
    record["resolution_note"] = note
    record["source_collection"] = active_key
    resolved_records.append(record)

    active_data[active_key] = active_records
    active_data.setdefault("meta", {})["updated_on"] = resolved_stamp
    resolved_data[resolved_key] = resolved_records
    resolved_data.setdefault("meta", {})["updated_on"] = resolved_stamp

    dump_toml(active_path, active_data)
    dump_toml(resolved_path, resolved_data)
    return record


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage the local .agents issue and todo databases.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rank_parser = subparsers.add_parser("rank", help="Show ranked active issues and todos.")
    rank_parser.add_argument("--kind", choices=("issues", "todos", "all"), default="all")
    rank_parser.add_argument("--format", choices=("text", "json"), default="text")
    rank_parser.add_argument("--limit", type=int, default=None)

    resolve_parser = subparsers.add_parser("resolve", help="Move an issue or todo into the resolved collection.")
    resolve_parser.add_argument("kind", choices=("issue", "todo"))
    resolve_parser.add_argument("record_id")
    resolve_parser.add_argument("--note", required=True, help="Short resolution note.")
    resolve_parser.add_argument(
        "--resolved-on",
        default=None,
        help="Resolution date in YYYY-MM-DD format. Defaults to today.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the backlog CLI."""
    args = _parse_args(argv)

    if args.command == "rank":
        ranked = build_ranked_view()
        output_format: Format = args.format
        if output_format == "json":
            payload = ranked if args.kind == "all" else {args.kind: ranked[args.kind]}
            print(json.dumps(payload, indent=2))
        else:
            print(render_ranked_text(args.kind, ranked, args.limit))
        return 0

    if args.command == "resolve":
        kind: Kind = args.kind
        record = resolve_record(
            kind=kind,
            record_id=args.record_id,
            note=args.note,
            resolved_on=args.resolved_on,
        )
        print(f"Moved {kind} {record['id']} to {RESOLVED_PATH}.")
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
