"""Compute Python line-of-code statistics for src/ and tests/."""

from __future__ import annotations

import argparse
import ast
import difflib
import re
import subprocess
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rich.table import Table

from prml_vslam.utils import Console

STAT_KEYS = (
    "files",
    "total",
    "non_empty",
    "comments",
    "docstrings",
    "todo",
    "fixme",
    "code",
)

ZERO_STATS = dict.fromkeys(STAT_KEYS, 0)

COUNT_TARGETS = ("src", "tests")
PROJECT_MODULE_ROOT = Path("src/prml_vslam")

MARKER_PATTERNS = {
    "todo": re.compile(r"\bTODO\b[:\s-]*(?P<text>.*)", re.IGNORECASE),
    "fixme": re.compile(r"\bFIXME\b[:\s-]*(?P<text>.*)", re.IGNORECASE),
}


@dataclass(frozen=True)
class LineStats:
    """Aggregated line statistics for Python source files."""

    files: int = 0
    total: int = 0
    non_empty: int = 0
    comments: int = 0
    docstrings: int = 0
    todo: int = 0
    fixme: int = 0
    code: int = 0

    def __add__(self, other: LineStats) -> LineStats:
        """Merge two source line-stat objects."""

        return LineStats(
            files=self.files + other.files,
            total=self.total + other.total,
            non_empty=self.non_empty + other.non_empty,
            comments=self.comments + other.comments,
            docstrings=self.docstrings + other.docstrings,
            todo=self.todo + other.todo,
            fixme=self.fixme + other.fixme,
            code=self.code + other.code,
        )

    def as_dict(self) -> dict[str, int]:
        """Return the legacy dictionary shape used by older tests and callers."""

        return {key: getattr(self, key) for key in STAT_KEYS}


@dataclass(frozen=True)
class SourceFileStats:
    """Line statistics and markers for one analyzed Python source file."""

    stats: LineStats
    markers: list[MarkerEntry]


@dataclass(frozen=True)
class DiffStats:
    """Code-line delta counts for one or more Python source files."""

    files: int = 0
    added: int = 0
    changed: int = 0
    deleted: int = 0

    @property
    def net(self) -> int:
        """Return the net code-line delta."""

        return self.added - self.deleted

    def has_code_delta(self) -> bool:
        """Return whether this diff contains any code-line additions, edits, or removals."""

        return bool(self.added or self.changed or self.deleted)

    def with_file(self) -> DiffStats:
        """Count this delta as affecting one file when it has code-line changes."""

        return DiffStats(
            files=1 if self.has_code_delta() else 0,
            added=self.added,
            changed=self.changed,
            deleted=self.deleted,
        )

    def __add__(self, other: DiffStats) -> DiffStats:
        """Merge two code-line delta objects."""

        return DiffStats(
            files=self.files + other.files,
            added=self.added + other.added,
            changed=self.changed + other.changed,
            deleted=self.deleted + other.deleted,
        )


@dataclass(frozen=True)
class GitFileChange:
    """One Git worktree file change relative to HEAD."""

    old_path: Path | None
    new_path: Path | None

    @property
    def report_path(self) -> Path:
        """Return the path that should own this change in reports."""

        return self.new_path or self.old_path or Path(".")


@dataclass(frozen=True)
class MarkerEntry:
    """Single TODO/FIXME marker found in a Python source file."""

    kind: Literal["todo", "fixme"]
    path: Path
    line_number: int
    text: str


def parse_args() -> argparse.Namespace:
    """Parse CLI flags for LOC, module, and dirty-worktree reports."""

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
    parser.add_argument(
        "--modules",
        action="store_true",
        help="Show Python LOC grouped by prml_vslam module.",
    )
    parser.add_argument(
        "--module-depth",
        type=int,
        default=2,
        metavar="N",
        help="Module grouping depth counted from src/ (default: 2).",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show dirty-worktree Python code-line changes against HEAD.",
    )
    args = parser.parse_args()
    if args.module_depth < 1:
        parser.error("--module-depth must be at least 1")
    return args


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


def iter_python_files(root: Path) -> list[Path]:
    """Return Python source files below a root path."""

    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def extract_docstring_lines(source: str) -> set[int]:
    """Return line numbers occupied by module, class, and function docstrings."""

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    docstring_lines: set[int] = set()

    def add_doc_range(node: ast.AST) -> None:
        body = getattr(node, "body", None)
        if not body:
            return
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
            start = first.lineno
            end = getattr(first, "end_lineno", start)
            docstring_lines.update(range(start, end + 1))

    add_doc_range(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            add_doc_range(node)
    return docstring_lines


def analyze_source(path: Path, source: str) -> SourceFileStats:
    """Count source lines and markers for one Python file."""

    lines = source.splitlines()
    docstring_lines = extract_docstring_lines(source)
    markers = extract_markers(path, lines)
    non_empty_lines = sum(1 for line in lines if line.strip())
    comment_lines = sum(1 for line in lines if line.lstrip().startswith("#"))

    return SourceFileStats(
        stats=LineStats(
            files=1,
            total=len(lines),
            non_empty=non_empty_lines,
            comments=comment_lines,
            docstrings=len(docstring_lines),
            todo=sum(1 for marker in markers if marker.kind == "todo"),
            fixme=sum(1 for marker in markers if marker.kind == "fixme"),
            code=max(0, non_empty_lines - comment_lines - len(docstring_lines)),
        ),
        markers=markers,
    )


def analyze_file(path: Path) -> SourceFileStats:
    """Read and count source lines and markers for one Python file."""

    return analyze_source(path, path.read_text(encoding="utf-8", errors="replace"))


def code_lines_for_source(source: str) -> list[str]:
    """Return source lines counted as code by the LOC rules."""

    docstring_lines = extract_docstring_lines(source)
    return [
        line
        for line_number, line in enumerate(source.splitlines(), start=1)
        if line_number not in docstring_lines and line.strip() and not line.lstrip().startswith("#")
    ]


def count_stats(root: str | Path) -> tuple[dict[str, int], list[MarkerEntry]]:
    """Count high-level line statistics for Python files under root."""

    root_path = Path(root)
    total = LineStats()
    markers: list[MarkerEntry] = []

    for file in iter_python_files(root_path):
        current = analyze_file(file)
        total += current.stats
        markers.extend(current.markers)

    return total.as_dict(), markers


def count_grouped_stats(files: Iterable[Path], bucketer: Callable[[Path], str]) -> dict[str, LineStats]:
    """Count line statistics grouped by a caller-provided path bucket."""

    grouped: dict[str, LineStats] = {}
    for file in sorted(files):
        bucket = bucketer(file)
        grouped[bucket] = grouped.get(bucket, LineStats()) + analyze_file(file).stats
    return grouped


def module_bucket(path: Path, module_depth: int = 2, source_root: Path = Path("src")) -> str:
    """Return the dotted module bucket for a Python source path."""

    try:
        relative = path.relative_to(source_root)
    except ValueError:
        relative = path
    parts = relative.parts[:-1]
    if not parts:
        return source_root.name
    return ".".join(parts[:module_depth])


def count_module_stats(module_depth: int = 2) -> dict[str, LineStats]:
    """Count Python LOC grouped by prml_vslam module."""

    return count_grouped_stats(
        iter_python_files(PROJECT_MODULE_ROOT),
        lambda path: module_bucket(path, module_depth=module_depth),
    )


def count_code_line_delta(old_lines: Sequence[str], new_lines: Sequence[str]) -> DiffStats:
    """Count inserted, replaced, and removed code lines between two code-line sequences."""

    delta = DiffStats()
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        old_count = old_end - old_start
        new_count = new_end - new_start
        match tag:
            case "equal":
                continue
            case "insert":
                delta += DiffStats(added=new_count)
            case "delete":
                delta += DiffStats(deleted=old_count)
            case "replace":
                changed = min(old_count, new_count)
                delta += DiffStats(
                    added=max(0, new_count - changed),
                    changed=changed,
                    deleted=max(0, old_count - changed),
                )
    return delta


def count_source_code_delta(old_source: str, new_source: str) -> DiffStats:
    """Count code-line changes between two Python source revisions."""

    return count_code_line_delta(code_lines_for_source(old_source), code_lines_for_source(new_source))


def run_git(repo_root: Path, args: Sequence[str]) -> bytes:
    """Run a Git command and return stdout bytes."""

    result = subprocess.run(
        ["git", "-C", repo_root.as_posix(), *args],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
    return result.stdout


def parse_git_name_status(raw: bytes) -> list[GitFileChange]:
    """Parse `git diff --name-status -z` output into file changes."""

    fields = [field for field in raw.split(b"\0") if field]
    changes: list[GitFileChange] = []
    index = 0
    while index < len(fields):
        status = fields[index].decode("utf-8", errors="replace")
        index += 1
        if status.startswith(("R", "C")):
            old_path = Path(fields[index].decode("utf-8", errors="replace"))
            new_path = Path(fields[index + 1].decode("utf-8", errors="replace"))
            index += 2
        else:
            path = Path(fields[index].decode("utf-8", errors="replace"))
            index += 1
            old_path = None if status.startswith("A") else path
            new_path = None if status.startswith("D") else path
        if (old_path is not None and old_path.suffix == ".py") or (new_path is not None and new_path.suffix == ".py"):
            changes.append(GitFileChange(old_path=old_path, new_path=new_path))
    return changes


def tracked_python_changes(repo_root: Path, roots: Sequence[str] = COUNT_TARGETS) -> list[GitFileChange]:
    """Return tracked Python file changes between HEAD and the worktree."""

    raw = run_git(repo_root, ["diff", "--name-status", "-z", "HEAD", "--", *roots])
    return parse_git_name_status(raw)


def untracked_python_changes(repo_root: Path, roots: Sequence[str] = COUNT_TARGETS) -> list[GitFileChange]:
    """Return untracked Python files below counted roots."""

    raw = run_git(repo_root, ["ls-files", "--others", "--exclude-standard", "-z", "--", *roots])
    return [
        GitFileChange(old_path=None, new_path=Path(path.decode("utf-8", errors="replace")))
        for path in raw.split(b"\0")
        if path and Path(path.decode("utf-8", errors="replace")).suffix == ".py"
    ]


def read_head_source(repo_root: Path, path: Path | None) -> str:
    """Read a file revision from HEAD."""

    if path is None:
        return ""
    result = subprocess.run(
        ["git", "-C", repo_root.as_posix(), "show", f"HEAD:{path.as_posix()}"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.decode("utf-8", errors="replace")


def read_worktree_source(repo_root: Path, path: Path | None) -> str:
    """Read a file revision from the current worktree."""

    if path is None:
        return ""
    worktree_path = repo_root / path
    if not worktree_path.exists() or not worktree_path.is_file():
        return ""
    return worktree_path.read_text(encoding="utf-8", errors="replace")


def diff_bucket(path: Path, module_depth: int) -> str:
    """Return the dirty-diff report bucket for a repo-relative path."""

    if len(path.parts) >= 2 and path.parts[:2] == ("src", "prml_vslam"):
        return module_bucket(path, module_depth=module_depth)
    if path.parts and path.parts[0] == "tests":
        return "tests"
    return path.parts[0] if path.parts else "."


def collect_dirty_diff_stats(repo_root: Path | None = None, module_depth: int = 2) -> dict[str, DiffStats]:
    """Collect dirty-worktree Python code-line changes against HEAD."""

    repo_root = (repo_root or Path.cwd()).resolve()
    grouped: dict[str, DiffStats] = {}
    changes = [*tracked_python_changes(repo_root), *untracked_python_changes(repo_root)]
    for change in changes:
        delta = count_source_code_delta(
            read_head_source(repo_root, change.old_path),
            read_worktree_source(repo_root, change.new_path),
        ).with_file()
        if not delta.has_code_delta():
            continue
        bucket = diff_bucket(change.report_path, module_depth=module_depth)
        grouped[bucket] = grouped.get(bucket, DiffStats()) + delta
    return grouped


def stats_value(stats: dict[str, int] | LineStats, key: str) -> int:
    """Read one statistic from either the legacy dict or typed stats object."""

    return stats[key] if isinstance(stats, dict) else getattr(stats, key)


def render_loc_table(
    console: Console,
    title: str,
    first_column: str,
    rows: Iterable[tuple[str, dict[str, int] | LineStats]],
) -> None:
    """Render a Rich table for aggregate LOC statistics."""

    table = Table(title=title, header_style="bold blue")
    table.add_column(first_column, style="bold")
    table.add_column("files", justify="right")
    table.add_column("total", justify="right")
    table.add_column("non-empty", justify="right")
    table.add_column("comments", justify="right")
    table.add_column("docstrings", justify="right")
    table.add_column("todo", justify="right")
    table.add_column("fixme", justify="right")
    table.add_column("code", justify="right", style="green")

    for name, current in rows:
        table.add_row(
            name,
            str(stats_value(current, "files")),
            str(stats_value(current, "total")),
            str(stats_value(current, "non_empty")),
            str(stats_value(current, "comments")),
            str(stats_value(current, "docstrings")),
            str(stats_value(current, "todo")),
            str(stats_value(current, "fixme")),
            str(stats_value(current, "code")),
        )
    console.print(table)


def signed(value: int) -> str:
    """Return a signed integer string for delta tables."""

    return f"{value:+d}"


def render_diff_table(console: Console, diff_stats: dict[str, DiffStats]) -> None:
    """Render a Rich table for dirty-worktree code-line deltas."""

    if not diff_stats:
        console.print("[dim]Dirty Python LOC Diff vs HEAD: no code-line changes.[/dim]")
        return

    table = Table(title="Dirty Python LOC Diff vs HEAD", header_style="bold blue")
    table.add_column("scope", style="bold")
    table.add_column("files", justify="right")
    table.add_column("added", justify="right", style="green")
    table.add_column("changed", justify="right", style="yellow")
    table.add_column("deleted", justify="right", style="red")
    table.add_column("net", justify="right")

    total = DiffStats()
    for name in sorted(diff_stats):
        current = diff_stats[name]
        total += current
        table.add_row(
            name,
            str(current.files),
            str(current.added),
            str(current.changed),
            str(current.deleted),
            signed(current.net),
        )
    table.add_row(
        "total",
        str(total.files),
        str(total.added),
        str(total.changed),
        str(total.deleted),
        signed(total.net),
    )
    console.print(table)


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
    stats = {
        target: count_stats(target) if Path(target).exists() else (ZERO_STATS.copy(), []) for target in COUNT_TARGETS
    }
    total = ZERO_STATS.copy()
    all_markers: list[MarkerEntry] = []
    for current, markers in stats.values():
        for key in total:
            total[key] += current[key]
        all_markers.extend(markers)

    render_loc_table(
        console,
        "Python LOC Summary",
        "scope",
        [(name, total if name == "total" else stats[name][0]) for name in (*COUNT_TARGETS, "total")],
    )

    if args.modules:
        render_loc_table(
            console,
            f"Python Module LOC (depth {args.module_depth})",
            "module",
            sorted(count_module_stats(module_depth=args.module_depth).items()),
        )

    if args.diff:
        render_diff_table(console, collect_dirty_diff_stats(module_depth=args.module_depth))

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
