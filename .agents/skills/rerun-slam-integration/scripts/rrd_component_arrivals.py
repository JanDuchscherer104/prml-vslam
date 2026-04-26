#!/usr/bin/env python3
"""Report first/last presence for selected Rerun component columns."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rerun.dataframe as rdf


@dataclass(slots=True)
class ColumnSummary:
    column_name: str
    first_index: int | float | None = None
    last_index: int | float | None = None
    presence_count: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording", type=Path, help="Path to a .rrd recording")
    parser.add_argument("--index", default="frame", help="Timeline/index name to query")
    parser.add_argument(
        "--contents",
        default="/**",
        help="Entity-path query for the dataframe view, e.g. /world/live/model/camera/image",
    )
    parser.add_argument("--from-seq", type=int, default=None, help="Inclusive lower bound for sequence filtering")
    parser.add_argument("--to-seq", type=int, default=None, help="Inclusive upper bound for sequence filtering")
    parser.add_argument(
        "--component-substring",
        action="append",
        default=[],
        help="Only inspect component columns whose fully-qualified names contain this substring. Repeatable.",
    )
    return parser.parse_args()


def component_column_name(column: Any) -> str:
    return f"{column.entity_path}:{column.component}"


def value_present(value: object | None) -> bool:
    if value is None:
        return False
    array = np.asarray(value)
    return array.size > 0


def main() -> int:
    args = parse_args()
    recording = rdf.load_recording(args.recording)
    view = recording.view(index=args.index, contents=args.contents)
    if args.from_seq is not None or args.to_seq is not None:
        start = args.from_seq if args.from_seq is not None else -(2**63)
        stop = args.to_seq if args.to_seq is not None else 2**63 - 1
        view = view.filter_range_sequence(start, stop)

    selected_columns = [
        component_column_name(column)
        for column in view.schema().component_columns()
        if not args.component_substring
        or any(substring in component_column_name(column) for substring in args.component_substring)
    ]
    selected_columns = sorted(set(selected_columns))
    if not selected_columns:
        raise SystemExit("No matching component columns found for the requested view.")

    summaries = {name: ColumnSummary(column_name=name) for name in selected_columns}
    selected_output_columns = [args.index, *selected_columns]
    for batch in view.select(columns=selected_output_columns):
        payload = batch.to_pydict()
        if not payload:
            continue
        row_count = len(next(iter(payload.values())))
        for row_index in range(row_count):
            index_value = payload.get(args.index, [None] * row_count)[row_index]
            for column_name in selected_columns:
                column_values = payload.get(column_name)
                if column_values is None or not value_present(column_values[row_index]):
                    continue
                summary = summaries[column_name]
                if summary.first_index is None:
                    summary.first_index = index_value
                summary.last_index = index_value
                summary.presence_count += 1

    for summary in summaries.values():
        print(
            f"{summary.column_name}\n"
            f"  first_{args.index}: {summary.first_index}\n"
            f"  last_{args.index}: {summary.last_index}\n"
            f"  populated_rows: {summary.presence_count}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
