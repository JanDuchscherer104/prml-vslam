from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest
import tomli_w


def _load_agents_db_module() -> Any:
    module_path = Path(__file__).resolve().parents[1] / ".agents" / "scripts" / "agents_db.py"
    spec = importlib.util.spec_from_file_location("agents_db", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {module_path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AGENTS_DB = _load_agents_db_module()


def _write_toml(path: Path, data: dict[str, Any]) -> None:
    with path.open("wb") as handle:
        tomli_w.dump(data, handle)


def test_rank_todos_uses_priority_then_expected_loc() -> None:
    todos = [
        {
            "id": "TODO-0003",
            "title": "Medium priority quick task",
            "status": "pending",
            "priority": "medium",
            "loc_min": 1,
            "loc_expected": 5,
            "loc_max": 10,
        },
        {
            "id": "TODO-0001",
            "title": "High priority larger task",
            "status": "pending",
            "priority": "high",
            "loc_min": 20,
            "loc_expected": 50,
            "loc_max": 80,
        },
        {
            "id": "TODO-0002",
            "title": "High priority smaller task",
            "status": "pending",
            "priority": "high",
            "loc_min": 5,
            "loc_expected": 10,
            "loc_max": 20,
        },
    ]

    ranked = AGENTS_DB.rank_todos(todos)

    assert [todo["id"] for todo in ranked] == ["TODO-0002", "TODO-0001", "TODO-0003"]


def test_rank_todos_requires_loc_triplet() -> None:
    todos = [
        {
            "id": "TODO-0001",
            "title": "Missing expected loc",
            "status": "pending",
            "priority": "high",
            "loc_min": 1,
            "loc_max": 2,
        }
    ]

    with pytest.raises(ValueError, match="missing required LOC fields"):
        AGENTS_DB.rank_todos(todos)


def test_resolve_todo_moves_record_to_resolved_collection(tmp_path: Path) -> None:
    issues_path = tmp_path / "issues.toml"
    todos_path = tmp_path / "todos.toml"
    resolved_path = tmp_path / "resolved.toml"

    _write_toml(
        issues_path,
        {
            "meta": {"schema_version": 2, "updated_on": "2026-04-05"},
            "issues": [],
        },
    )
    _write_toml(
        todos_path,
        {
            "meta": {"schema_version": 2, "updated_on": "2026-04-05"},
            "todos": [
                {
                    "id": "TODO-0002",
                    "title": "Declare PyYAML explicitly",
                    "status": "pending",
                    "priority": "high",
                    "issue_ids": ["ISSUE-0002"],
                    "loc_min": 1,
                    "loc_expected": 4,
                    "loc_max": 12,
                }
            ],
        },
    )
    _write_toml(
        resolved_path,
        {
            "meta": {"schema_version": 1, "updated_on": "2026-04-05"},
        },
    )

    moved = AGENTS_DB.resolve_record(
        kind="todo",
        record_id="TODO-0002",
        note="Closed by explicit dependency declaration.",
        resolved_on="2026-04-06",
        issues_path=issues_path,
        todos_path=todos_path,
        resolved_path=resolved_path,
    )

    updated_todos = AGENTS_DB.load_toml(todos_path)
    updated_resolved = AGENTS_DB.load_toml(resolved_path)

    assert moved["id"] == "TODO-0002"
    assert updated_todos["todos"] == []
    assert updated_todos["meta"]["updated_on"] == "2026-04-06"
    assert updated_resolved["meta"]["updated_on"] == "2026-04-06"
    assert updated_resolved["resolved_todos"][0]["id"] == "TODO-0002"
    assert updated_resolved["resolved_todos"][0]["status"] == "resolved"
    assert updated_resolved["resolved_todos"][0]["previous_status"] == "pending"
    assert updated_resolved["resolved_todos"][0]["resolved_on"] == "2026-04-06"


def test_resolve_issue_moves_record_to_resolved_collection(tmp_path: Path) -> None:
    issues_path = tmp_path / "issues.toml"
    todos_path = tmp_path / "todos.toml"
    resolved_path = tmp_path / "resolved.toml"

    _write_toml(
        issues_path,
        {
            "meta": {"schema_version": 2, "updated_on": "2026-04-05"},
            "issues": [
                {
                    "id": "ISSUE-0004",
                    "title": "Page-state persistence helpers are duplicated",
                    "status": "open",
                    "priority": "medium",
                    "summary": "Duplicate save-if-changed helpers should be consolidated.",
                }
            ],
        },
    )
    _write_toml(
        todos_path,
        {
            "meta": {"schema_version": 2, "updated_on": "2026-04-05"},
            "todos": [],
        },
    )
    _write_toml(
        resolved_path,
        {
            "meta": {"schema_version": 1, "updated_on": "2026-04-05"},
        },
    )

    moved = AGENTS_DB.resolve_record(
        kind="issue",
        record_id="ISSUE-0004",
        note="Closed after consolidating the shared helper.",
        resolved_on="2026-04-07",
        issues_path=issues_path,
        todos_path=todos_path,
        resolved_path=resolved_path,
    )

    updated_issues = AGENTS_DB.load_toml(issues_path)
    updated_resolved = AGENTS_DB.load_toml(resolved_path)

    assert moved["id"] == "ISSUE-0004"
    assert updated_issues["issues"] == []
    assert updated_issues["meta"]["updated_on"] == "2026-04-07"
    assert updated_resolved["resolved_issues"][0]["id"] == "ISSUE-0004"
    assert updated_resolved["resolved_issues"][0]["status"] == "resolved"
    assert updated_resolved["resolved_issues"][0]["previous_status"] == "open"
    assert updated_resolved["resolved_issues"][0]["resolved_on"] == "2026-04-07"
