"""Compute Python line-of-code statistics for src/ and tests/."""

from __future__ import annotations

import argparse
import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

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

MARKER_PATTERNS = {
    "todo": re.compile(r"\bTODO\b[:\s-]*(?P<text>.*)", re.IGNORECASE),
    "fixme": re.compile(r"\bFIXME\b[:\s-]*(?P<text>.*)", re.IGNORECASE),
}


@dataclass(frozen=True)
class MarkerEntry:
    """Single TODO/FIXME marker found in a Python source file."""

    kind: Literal["todo", "fixme"]
    path: Path
    line_number: int
    text: str


def parse_args() -> argparse.Namespace:
    """Parse CLI flags for optional marker detail output."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--todo",
        action="store_true",
        help="Show a detailed table of TODO markers.",
    )
    parser.add_argument(
        "--fixme",
        action="store_true",
        help="Show a detailed table of FIXME markers.",
    )
    return parser.parse_args()


def extract_markers(path: Path, lines: list[str]) -> list[MarkerEntry]:
    """Extract TODO/FIXME comment markers from file lines."""

    markers: list[MarkerEntry] = []
    for line_number, line in enumerate(lines, start=1):
        comment_index = line.find("#")
        if comment_index < 0:
            continue
        comment_text = line[comment_index + 1 :].strip()
        for kind, pattern in MARKER_PATTERNS.items():
            match = pattern.search(comment_text)
            if match is None:
                continue
            markers.append(
                MarkerEntry(
                    kind=kind,
                    path=path,
                    line_number=line_number,
                    text=match.group("text").strip() or "-",
                )
            )
    return markers


def count_stats(root: str) -> tuple[dict[str, int], list[MarkerEntry]]:
    """Count high-level line statistics for Python files under root."""

    root_path = Path(root)
    files = sorted(root_path.rglob("*.py"))
    total_lines = 0
    non_empty_lines = 0
    comment_lines = 0
    docstring_lines = 0
    markers: list[MarkerEntry] = []

    for file in files:
        source = file.read_text(encoding="utf-8", errors="replace")
        lines = source.splitlines()
        total_lines += len(lines)
        non_empty_lines += sum(1 for line in lines if line.strip())
        comment_lines += sum(1 for line in lines if line.lstrip().startswith("#"))
        file_markers = extract_markers(file, lines)
        markers.extend(file_markers)

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
        "todo": sum(1 for marker in markers if marker.kind == "todo"),
        "fixme": sum(1 for marker in markers if marker.kind == "fixme"),
        "code": max(0, non_empty_lines - comment_lines - docstring_lines),
    }, markers


def render_marker_table(console: Console, title: str, markers: list[MarkerEntry]) -> None:
    """Render a detailed Rich table for one marker kind."""

    if not markers:
        console.print(f"[dim]{title}: none found.[/dim]")
        return

    table = Table(title=title, header_style="bold blue")
    table.add_column("file", style="bold")
    table.add_column("line", justify="right")
    table.add_column("text")
    for marker in markers:
        table.add_row(marker.path.as_posix(), str(marker.line_number), marker.text)
    console.print(table)


def main() -> None:
    """Print LOC statistics for src/ and tests/."""

    args = parse_args()
    console = Console("scripts.loc_stats")
    targets = ("src", "tests")
    stats = {target: count_stats(target) if Path(target).exists() else (ZERO_STATS.copy(), []) for target in targets}
    total = ZERO_STATS.copy()
    all_markers: list[MarkerEntry] = []
    for current, markers in stats.values():
        for key in total:
            total[key] += current[key]
        all_markers.extend(markers)

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
        current = total if name == "total" else stats[name][0]
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

    if args.todo:
        render_marker_table(
            console,
            "TODO Markers",
            [marker for marker in all_markers if marker.kind == "todo"],
        )
    if args.fixme:
        render_marker_table(
            console,
            "FIXME Markers",
            [marker for marker in all_markers if marker.kind == "fixme"],
        )


if __name__ == "__main__":
    main()
