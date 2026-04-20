"""Portable opaque handles for transient bulk runtime payloads.

This module contains the handle DTOs used when the pipeline keeps large arrays
and previews out of persisted contracts. They let runtime code refer to
substrate-owned payloads from events and snapshots without pretending those
arrays are durable scientific artifacts.
"""

from __future__ import annotations

from typing import Literal

from .transport import TransportModel


# TODO: add module level doc string explaining the motivation for handle contracts!
class ArrayHandle(TransportModel):
    """Refer to one transient array stored in the execution substrate."""

    kind: Literal["array"] = "array"
    handle_id: str
    shape: tuple[int, ...]
    dtype: str
    backend: Literal["ray-object-store"] = "ray-object-store"


class PreviewHandle(TransportModel):
    """Refer to one transient preview image stored in the execution substrate."""

    kind: Literal["preview"] = "preview"
    handle_id: str
    width: int
    height: int
    channels: int
    dtype: str
    backend: Literal["ray-object-store"] = "ray-object-store"


class BlobHandle(TransportModel):
    """Refer to one transient non-array binary payload."""

    kind: Literal["blob"] = "blob"
    handle_id: str
    media_type: str = "application/octet-stream"
    size_bytes: int | None = None
    backend: Literal["ray-object-store"] = "ray-object-store"


__all__ = ["ArrayHandle", "BlobHandle", "PreviewHandle"]
