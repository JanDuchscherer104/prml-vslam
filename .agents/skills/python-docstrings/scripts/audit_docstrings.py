#!/usr/bin/env python3
"""Audit Python files for missing or suspiciously short public docstrings.

This script is intentionally lightweight. It is useful for quick gap detection
before or after a docstring refactor, but it is not a full style checker.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

MODULE_OVERVIEW_KEYWORDS = (
    "contains",
    "provides",
    "owns",
    "responsib",
    "exports",
    "helpers",
    "wrappers",
    "adapters",
    "protocols",
)


@dataclass(frozen=True)
class Finding:
    """One docstring audit finding."""

    path: Path
    line: int
    kind: str
    name: str
    message: str

    def render(self, *, root: Path) -> str:
        """Format the finding relative to one reporting root."""

        rel = self.path.relative_to(root)
        return f"{rel}:{self.line}: {self.kind} {self.name}: {self.message}"


def _is_public_name(name: str) -> bool:
    return not name.startswith("_")


def _doc_length(text: str | None) -> int:
    if not text:
        return 0
    normalized = " ".join(line.strip() for line in text.splitlines() if line.strip())
    return len(normalized)


def _has_module_overview(text: str | None) -> bool:
    if not text:
        return False
    non_empty = [line.strip() for line in text.splitlines() if line.strip()]
    lower = text.lower()
    return len(non_empty) >= 2 and any(keyword in lower for keyword in MODULE_OVERVIEW_KEYWORDS)


def _iter_python_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files.append(path.resolve())
            continue
        if path.is_dir():
            files.extend(
                candidate.resolve() for candidate in path.rglob("*.py") if "__pycache__" not in candidate.parts
            )
    return sorted(set(files))


def _symbol_doc_findings(
    *,
    path: Path,
    tree: ast.Module,
    min_symbol_chars: int,
) -> list[Finding]:
    findings: list[Finding] = []

    def check(node: ast.AST, *, kind: str, name: str) -> None:
        doc = ast.get_docstring(node, clean=False)
        length = _doc_length(doc)
        if length == 0:
            findings.append(Finding(path, getattr(node, "lineno", 1), kind, name, "missing docstring"))
        elif length < min_symbol_chars:
            findings.append(
                Finding(
                    path,
                    getattr(node, "lineno", 1),
                    kind,
                    name,
                    f"docstring is short ({length} chars < {min_symbol_chars})",
                )
            )

    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and _is_public_name(node.name):
            check(node, kind="function", name=node.name)
        if isinstance(node, ast.ClassDef) and _is_public_name(node.name):
            check(node, kind="class", name=node.name)
            for child in node.body:
                if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef) and _is_public_name(child.name):
                    check(child, kind="method", name=f"{node.name}.{child.name}")

    return findings


def audit_file(
    *,
    path: Path,
    min_module_chars: int,
    min_symbol_chars: int,
    check_module_overview: bool,
) -> list[Finding]:
    """Return docstring findings for one Python file."""

    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError) as exc:
        return [Finding(path, 1, "file", path.name, f"could not parse file: {exc}")]

    findings: list[Finding] = []
    module_doc = ast.get_docstring(tree, clean=False)
    module_length = _doc_length(module_doc)
    if module_length == 0:
        findings.append(Finding(path, 1, "module", path.stem, "missing module docstring"))
    elif module_length < min_module_chars:
        findings.append(
            Finding(
                path,
                1,
                "module",
                path.stem,
                f"module docstring is short ({module_length} chars < {min_module_chars})",
            )
        )
    if check_module_overview and module_doc is not None and not _has_module_overview(module_doc):
        findings.append(
            Finding(
                path,
                1,
                "module",
                path.stem,
                "module docstring may be missing a high-level overview of contents and responsibilities",
            )
        )

    findings.extend(_symbol_doc_findings(path=path, tree=tree, min_symbol_chars=min_symbol_chars))
    return findings


def main() -> int:
    """Parse arguments, audit the selected paths, and return a process status."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Python file or directory to audit")
    parser.add_argument(
        "--min-module-chars",
        type=int,
        default=80,
        help="Minimum normalized character length for module docstrings",
    )
    parser.add_argument(
        "--min-symbol-chars",
        type=int,
        default=40,
        help="Minimum normalized character length for class/function/method docstrings",
    )
    parser.add_argument(
        "--check-module-overview",
        action="store_true",
        help="Flag module docstrings that look too terse to describe contents and responsibilities",
    )
    args = parser.parse_args()

    targets = [Path(value).resolve() for value in args.paths]
    files = _iter_python_files(targets)
    if not files:
        print("No Python files found.", file=sys.stderr)
        return 2

    root = Path.cwd()
    findings: list[Finding] = []
    for path in files:
        findings.extend(
            audit_file(
                path=path,
                min_module_chars=args.min_module_chars,
                min_symbol_chars=args.min_symbol_chars,
                check_module_overview=args.check_module_overview,
            )
        )

    if not findings:
        print(f"No findings in {len(files)} file(s).")
        return 0

    for finding in findings:
        print(finding.render(root=root))
    print(f"\n{len(findings)} finding(s) across {len(files)} file(s).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
