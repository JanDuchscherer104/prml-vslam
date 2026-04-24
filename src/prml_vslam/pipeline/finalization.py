"""Shared stable artifact serialization helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from prml_vslam.utils import BaseConfig


def stable_hash(payload: Any) -> str:
    """Compute a stable SHA-256 fingerprint for JSON-normalizable payloads."""
    normalized_payload = BaseConfig.to_jsonable(payload)
    encoded = json.dumps(normalized_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    """Persist one JSON artifact with deterministic formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(BaseConfig.to_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


__all__ = [
    "stable_hash",
    "write_json",
]
