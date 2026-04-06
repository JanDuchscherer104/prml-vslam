"""Initialize a bounded autoresearch run log for this repository."""

from __future__ import annotations

import argparse
from pathlib import Path

RESULTS_HEADER = "experiment_id\tcommit\tstatus\tprimary_metric\tsecondary_metric\tdescription\n"


def parse_args() -> argparse.Namespace:
    """Return validated CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Create .logs/autoresearch/<tag>/brief.md and results.tsv for a PRML VSLAM research loop."
    )
    parser.add_argument("--tag", required=True, help="Stable run tag, for example 2026-04-06-evo-harness.")
    parser.add_argument("--question", required=True, help="Research question for this run.")
    parser.add_argument("--primary-metric", required=True, help="Primary winner metric for keep/discard decisions.")
    parser.add_argument(
        "--secondary-metric",
        default="none",
        help="Optional secondary metric or guardrail summary.",
    )
    parser.add_argument(
        "--evaluation-cmd",
        action="append",
        default=[],
        help="Repeatable frozen evaluation command.",
    )
    parser.add_argument(
        "--mutable",
        action="append",
        default=[],
        help="Repeatable mutable file or glob surface.",
    )
    parser.add_argument(
        "--immutable",
        action="append",
        default=[],
        help="Repeatable immutable file or glob surface.",
    )
    parser.add_argument(
        "--branch",
        default="",
        help="Optional dedicated winner-branch name. Defaults to codex/autoresearch-<tag>.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repository root where the .logs directory should be created.",
    )
    return parser.parse_args()


def render_bullets(items: list[str], *, empty_text: str) -> str:
    """Render one markdown bullet list."""
    if not items:
        return f"- {empty_text}\n"
    return "".join(f"- {item}\n" for item in items)


def main() -> None:
    """Create the research brief and TSV header."""
    args = parse_args()
    repo_root = args.repo_root.expanduser().resolve()
    run_dir = repo_root / ".logs" / "autoresearch" / args.tag
    if run_dir.exists():
        raise SystemExit(f"Refusing to overwrite existing run directory: {run_dir}")

    run_dir.mkdir(parents=True, exist_ok=False)
    branch = args.branch or f"codex/autoresearch-{args.tag}"

    brief_path = run_dir / "brief.md"
    results_path = run_dir / "results.tsv"

    brief_path.write_text(
        "\n".join(
            [
                f"# Autoresearch Run: {args.tag}",
                "",
                f"- Branch: `{branch}`",
                f"- Question: {args.question}",
                f"- Primary metric: `{args.primary_metric}`",
                f"- Secondary metric: `{args.secondary_metric}`",
                "",
                "## Evaluation Commands",
                "",
                render_bullets(args.evaluation_cmd, empty_text="Fill in the frozen evaluation commands."),
                "## Mutable Surface",
                "",
                render_bullets(args.mutable, empty_text="Fill in the editable file/module surface."),
                "## Immutable Surface",
                "",
                render_bullets(args.immutable, empty_text="Fill in the frozen docs/contracts/evaluator surface."),
            ]
        ),
        encoding="utf-8",
    )
    results_path.write_text(RESULTS_HEADER, encoding="utf-8")

    print(brief_path)
    print(results_path)


if __name__ == "__main__":
    main()
