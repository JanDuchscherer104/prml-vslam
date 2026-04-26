#!/usr/bin/env python3
"""Print a fast entity/component inventory for one Rerun recording."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import rerun.dataframe as rdf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording", type=Path, help="Path to a .rrd recording")
    parser.add_argument(
        "--prefix",
        action="append",
        default=[],
        help="Only include entity paths that start with this prefix. Repeatable.",
    )
    parser.add_argument(
        "--show-components",
        action="store_true",
        help="Print component names under each matching entity path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    recording = rdf.load_recording(args.recording)
    grouped: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for column in recording.schema().component_columns():
        entity_path = str(column.entity_path)
        if args.prefix and not any(entity_path.startswith(prefix) for prefix in args.prefix):
            continue
        grouped[entity_path].append((str(column.component), str(column.archetype)))

    for entity_path in sorted(grouped):
        columns = sorted(set(grouped[entity_path]))
        print(f"{entity_path} ({len(columns)} components)")
        if args.show_components:
            for component, archetype in columns:
                print(f"  - {component} [{archetype}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
