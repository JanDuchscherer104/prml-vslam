"""Portable opaque handles for bulk pipeline payloads."""

from __future__ import annotations

from typing import Literal

from .transport import TransportModel


class ArrayHandle(TransportModel):
    """Opaque handle for one array stored in the execution substrate."""

    kind: Literal["array"] = "array"
    handle_id: str
    shape: tuple[int, ...]
    dtype: str
    backend: Literal["ray-object-store"] = "ray-object-store"


class PreviewHandle(TransportModel):
    """Opaque handle for one preview image stored in the execution substrate."""

    kind: Literal["preview"] = "preview"
    handle_id: str
    width: int
    height: int
    channels: int
    dtype: str
    backend: Literal["ray-object-store"] = "ray-object-store"


class BlobHandle(TransportModel):
    """Opaque handle for one non-array binary payload."""

    kind: Literal["blob"] = "blob"
    handle_id: str
    media_type: str = "application/octet-stream"
    size_bytes: int | None = None
    backend: Literal["ray-object-store"] = "ray-object-store"


__all__ = ["ArrayHandle", "BlobHandle", "PreviewHandle"]
