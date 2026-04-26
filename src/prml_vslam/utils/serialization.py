"""Shared deterministic JSON and hashing helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from prml_vslam.utils.base_config import BaseConfig

_HASH_CHUNK_BYTES = 1024 * 1024


def stable_hash(payload: Any) -> str:
    """Compute a stable SHA-256 fingerprint for JSON-normalizable payloads."""
    normalized_payload = BaseConfig.to_jsonable(payload)
    encoded = json.dumps(normalized_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def hash_path(path: Path) -> str:
    """Return a SHA-256 digest for a file or directory tree."""
    resolved = path.expanduser().resolve()
    if resolved.is_file():
        return _hash_file(resolved)
    if resolved.is_dir():
        digest = hashlib.sha256()
        digest.update(b"dir-v1\0")
        for child in sorted(item for item in resolved.rglob("*") if item.is_file()):
            relative = child.relative_to(resolved).as_posix().encode("utf-8")
            digest.update(relative)
            digest.update(b"\0")
            digest.update(_hash_file(child).encode("ascii"))
            digest.update(b"\0")
        return digest.hexdigest()
    return stable_hash({"missing_path": resolved.as_posix()})


def write_json(path: Path, payload: Any) -> None:
    """Persist one JSON artifact with deterministic formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(BaseConfig.to_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(b"file-v1\0")
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(_HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = ["hash_path", "stable_hash", "write_json"]
