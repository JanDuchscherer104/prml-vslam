"""Compute Python line-of-code statistics for src/ and tests/."""

from __future__ import annotations

import ast
from pathlib import Path


def count_stats(root: str) -> dict[str, int]:
    """Count high-level line statistics for Python files under root."""

    root_path = Path(root)
    files = list(root_path.rglob("*.py"))
    total_lines = 0
    non_empty_lines = 0
    comment_lines = 0
    docstring_lines = 0

    for file in files:
        source = file.read_text(encoding="utf-8", errors="replace")
        lines = source.splitlines()
        total_lines += len(lines)
        non_empty_lines += sum(1 for line in lines if line.strip())
        comment_lines += sum(1 for line in lines if line.lstrip().startswith("#"))

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
        "code": max(0, non_empty_lines - comment_lines - docstring_lines),
    }


def main() -> None:
    """Print LOC statistics for src/ and tests/."""

    targets = ("src", "tests")
    stats = {
        target: count_stats(target)
        if Path(target).exists()
        else {
            "files": 0,
            "total": 0,
            "non_empty": 0,
            "comments": 0,
            "docstrings": 0,
            "code": 0,
        }
        for target in targets
    }
    total: dict[str, int] = {"files": 0, "total": 0, "non_empty": 0, "comments": 0, "docstrings": 0, "code": 0}

    for name, current in stats.items():
        print(f"{name}:")
        for key, value in current.items():
            print(f"  {key:10}: {value}")
        print()
        for key in total:
            total[key] += current[key]

    print("total:")
    for key, value in total.items():
        print(f"  {key:10}: {value}")


if __name__ == "__main__":
    main()
