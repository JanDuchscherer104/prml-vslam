"""Shared pure helpers for dataset download managers."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from pathlib import PurePosixPath
from typing import TypeVar

ModalityT = TypeVar("ModalityT", bound=StrEnum)


def modalities_present(local_modalities: Iterable[ModalityT], required_modalities: tuple[ModalityT, ...]) -> bool:
    """Return whether every required modality is available locally."""
    available = set(local_modalities)
    return all(modality in available for modality in required_modalities)


def normalize_archive_member(
    member_name: str,
    *,
    invalid_path_label: str | None = None,
) -> tuple[str, ...] | None:
    """Normalize one archive member path and reject unsafe traversal parts."""
    parts = tuple(part for part in PurePosixPath(member_name).parts if part not in {"", "."})
    if parts and all(part != ".." for part in parts):
        return parts
    if invalid_path_label is None:
        return None
    raise ValueError(f"Unsafe {invalid_path_label} archive member path: {member_name}")


def relative_sequence_path(normalized_parts: tuple[str, ...], sequence_root: str) -> PurePosixPath | None:
    """Return the member path relative to one dataset sequence root."""
    root_parts = (
        normalized_parts[1:] if len(normalized_parts) >= 2 and normalized_parts[0] == "data" else normalized_parts
    )
    if not root_parts or root_parts[0] != sequence_root:
        return None
    return PurePosixPath(*root_parts[1:])
