#!/usr/bin/env python3
"""Summarize key timing events from one run-events.jsonl file."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events_jsonl", type=Path, help="Path to summary/run-events.jsonl")
    parser.add_argument("--limit", type=int, default=40, help="Maximum number of interesting rows to print")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    counts: Counter[str] = Counter()
    printed = 0
    with args.events_jsonl.open(encoding="utf-8") as handle:
        for raw_line in handle:
            event = json.loads(raw_line)
            kind = event.get("kind")
            if kind == "packet.observed":
                packet_seq = event["packet"]["seq"]
                print(f"packet.observed seq={packet_seq}")
                counts[kind] += 1
                printed += 1
            elif kind == "backend.notice.received":
                notice = event["notice"]
                notice_kind = notice["kind"]
                counts[notice_kind] += 1
                match notice_kind:
                    case "pose.estimated":
                        print(
                            "pose.estimated "
                            f"seq={notice['seq']} source_seq={notice.get('source_seq')} "
                            f"pose_updated={notice.get('pose_updated')}"
                        )
                        printed += 1
                    case "keyframe.accepted":
                        print(
                            "keyframe.accepted "
                            f"seq={notice['seq']} keyframe_index={notice.get('keyframe_index')} "
                            f"accepted_keyframes={notice.get('accepted_keyframes')}"
                        )
                        printed += 1
                    case "keyframe.visualization_ready":
                        print(
                            "keyframe.visualization_ready "
                            f"seq={notice['seq']} source_seq={notice.get('source_seq')} "
                            f"keyframe_index={notice.get('keyframe_index')} "
                            f"image={notice.get('image') is not None} "
                            f"depth={notice.get('depth') is not None} "
                            f"preview={notice.get('preview') is not None} "
                            f"pointmap={notice.get('pointmap') is not None} "
                            f"intrinsics={notice.get('camera_intrinsics') is not None}"
                        )
                        printed += 1
            if printed >= args.limit:
                break

    if not counts:
        print(
            "No packet/backend timing events found. "
            "This run-events file appears to contain only durable stage-summary events."
        )

    print("\ncounts:")
    for name in sorted(counts):
        print(f"  {name}: {counts[name]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
