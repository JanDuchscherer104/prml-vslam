"""Portable path serialization for repo-owned JSON sidecars."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from prml_vslam.utils.base_config import BaseConfig

TModel = TypeVar("TModel", bound=BaseModel)


def write_portable_json(path: Path, payload: Any, *, root: Path) -> None:
    """Persist JSON with paths under ``root`` stored relative to ``root``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_portable_jsonable(payload, root=root), indent=2, sort_keys=True), encoding="utf-8")


def to_portable_jsonable(payload: Any, *, root: Path) -> Any:
    """Return a JSON-ready payload with root-owned paths made relative."""
    return _portable_value(payload, root=root.expanduser().resolve())


def rebase_model_paths(model: TModel, *, root: Path, stale_root: Path | None = None) -> TModel:
    """Resolve relative model paths against ``root`` and optionally rebase stale absolutes."""
    return type(model).model_validate(
        _rebase_value(
            model.model_dump(mode="python"),
            root=root.expanduser().resolve(),
            stale_root=None if stale_root is None else stale_root.expanduser().resolve(),
        )
    )


def _portable_value(value: Any, *, root: Path) -> Any:
    if isinstance(value, BaseModel):
        return _portable_value(value.model_dump(mode="python"), root=root)
    if isinstance(value, dict):
        return {str(key): _portable_value(item, root=root) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_portable_value(item, root=root) for item in value]
    if isinstance(value, Path):
        return _portable_path(value, root=root).as_posix()
    return BaseConfig.to_jsonable(value)


def _portable_path(path: Path, *, root: Path) -> Path:
    expanded = path.expanduser()
    resolved = (root / expanded).resolve() if not expanded.is_absolute() else expanded.resolve()
    try:
        return resolved.relative_to(root)
    except ValueError:
        return resolved


def _rebase_value(value: object, *, root: Path, stale_root: Path | None) -> object:
    if isinstance(value, Path):
        return _rebase_path(value, root=root, stale_root=stale_root)
    if isinstance(value, BaseModel):
        return rebase_model_paths(value, root=root, stale_root=stale_root)
    if isinstance(value, list):
        return [_rebase_value(item, root=root, stale_root=stale_root) for item in value]
    if isinstance(value, tuple):
        return tuple(_rebase_value(item, root=root, stale_root=stale_root) for item in value)
    if isinstance(value, dict):
        return {key: _rebase_value(item, root=root, stale_root=stale_root) for key, item in value.items()}
    return value


def _rebase_path(path: Path, *, root: Path, stale_root: Path | None) -> Path:
    expanded = path.expanduser()
    if not expanded.is_absolute():
        return (root / expanded).resolve()
    resolved = expanded.resolve()
    if stale_root is None:
        return resolved
    try:
        return (root / resolved.relative_to(stale_root)).resolve()
    except ValueError:
        return resolved


__all__ = ["rebase_model_paths", "to_portable_jsonable", "write_portable_json"]
