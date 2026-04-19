#!/usr/bin/env python3
"""Filter `rerun rrd print` chunk summaries by entity substring."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording", type=Path, help="Path to a .rrd or .rbl file")
    parser.add_argument(
        "--match",
        action="append",
        default=[],
        help="Only print chunk-summary lines containing this substring. Repeatable.",
    )
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of matching lines to print")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rerun_bin = shutil.which("rerun")
    if rerun_bin is None:
        raise SystemExit("The `rerun` CLI must be available on PATH. Run via `uv run --extra vista ...`.")

    process = subprocess.Popen(
        [rerun_bin, "rrd", "print", str(args.recording)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    seen = 0
    try:
        for line in process.stdout:
            if "Chunk(" not in line:
                continue
            if args.match and not any(substring in line for substring in args.match):
                continue
            sys.stdout.write(line)
            seen += 1
            if seen >= args.limit:
                process.terminate()
                break
    finally:
        process.wait(timeout=30)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
