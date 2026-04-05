"""Compute Python line-of-code statistics for src/ and tests/."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from rich.table import Table

from prml_vslam.utils import Console

ZERO_STATS = {
    "files": 0,
    "total": 0,
    "non_empty": 0,
    "comments": 0,
    "docstrings": 0,
    "todo": 0,
    "fixme": 0,
    "code": 0,
}

TODO_PATTERN = re.compile(r"#\s*TODO\b")
FIXME_PATTERN = re.compile(r"#\s*FIXME\b")


def count_stats(root: str) -> dict[str, int]:
    """Count high-level line statistics for Python files under root."""

    root_path = Path(root)
    files = list(root_path.rglob("*.py"))
    total_lines = 0
    non_empty_lines = 0
    comment_lines = 0
    docstring_lines = 0
    todo_lines = 0
    fixme_lines = 0

    for file in files:
        source = file.read_text(encoding="utf-8", errors="replace")
        lines = source.splitlines()
        total_lines += len(lines)
        non_empty_lines += sum(1 for line in lines if line.strip())
        comment_lines += sum(1 for line in lines if line.lstrip().startswith("#"))
        todo_lines += sum(1 for line in lines if TODO_PATTERN.search(line))
        fixme_lines += sum(1 for line in lines if FIXME_PATTERN.search(line))

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        def add_doc_range(node: ast.AST) -> None:
            nonlocal docstring_lines
            body = getattr(node, "body", None)
            if not body:
                return
            first = body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                start = first.lineno
                end = getattr(first, "end_lineno", start)
                docstring_lines += max(0, end - start + 1)

        add_doc_range(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                add_doc_range(node)

    return {
        "files": len(files),
        "total": total_lines,
        "non_empty": non_empty_lines,
        "comments": comment_lines,
        "docstrings": docstring_lines,
        "todo": todo_lines,
        "fixme": fixme_lines,
        "code": max(0, non_empty_lines - comment_lines - docstring_lines),
    }


def main() -> None:
    """Print LOC statistics for src/ and tests/."""

    console = Console("scripts.loc_stats")
    targets = ("src", "tests")
    stats = {target: count_stats(target) if Path(target).exists() else ZERO_STATS.copy() for target in targets}
    total = ZERO_STATS.copy()
    for current in stats.values():
        for key in total:
            total[key] += current[key]

    table = Table(title="Python LOC Summary", header_style="bold blue")
    table.add_column("scope", style="bold")
    table.add_column("files", justify="right")
    table.add_column("total", justify="right")
    table.add_column("non-empty", justify="right")
    table.add_column("comments", justify="right")
    table.add_column("docstrings", justify="right")
    table.add_column("todo", justify="right")
    table.add_column("fixme", justify="right")
    table.add_column("code", justify="right", style="green")

    for name in (*targets, "total"):
        current = total if name == "total" else stats[name]
        table.add_row(
            name,
            str(current["files"]),
            str(current["total"]),
            str(current["non_empty"]),
            str(current["comments"]),
            str(current["docstrings"]),
            str(current["todo"]),
            str(current["fixme"]),
            str(current["code"]),
        )

    console.print(table)


if __name__ == "__main__":
    main()
