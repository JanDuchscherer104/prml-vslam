"""Durable JSONL event sink."""

from __future__ import annotations

import json
from pathlib import Path

from prml_vslam.pipeline.contracts.events import EventTier, RunEvent
from prml_vslam.utils import BaseConfig


class JsonlEventSink:
    """Append-only JSONL sink for durable semantic events."""

    def __init__(self, path: Path) -> None:
        self._path = path.resolve()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def observe(self, event: RunEvent) -> None:
        if event.tier is not EventTier.DURABLE:
            return
        payload = BaseConfig.to_jsonable(event)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True))
            handle.write("\n")


__all__ = ["JsonlEventSink"]
