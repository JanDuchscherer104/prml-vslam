"""Portable opaque handles for transient bulk runtime payloads.

This module contains the handle DTOs used when the pipeline keeps large arrays
and previews out of persisted contracts. They let runtime code refer to
substrate-owned payloads from events and snapshots without pretending those
arrays are durable scientific artifacts.
"""

from __future__ import annotations

from typing import Literal

from .transport import TransportModel


# TODO(pipeline-refactor/WP-01): Collapse into TransientPayloadRef after the
# payload resolver replaces Ray-specific live array handles.
class ArrayHandle(TransportModel):
    """Refer to one transient array stored in the execution substrate."""

    kind: Literal["array"] = "array"
    handle_id: str
    shape: tuple[int, ...]
    dtype: str
    backend: Literal["ray-object-store"] = "ray-object-store"


# TODO(pipeline-refactor/WP-01): Collapse into TransientPayloadRef after preview
# payloads use the target live payload resolver.
class PreviewHandle(TransportModel):
    """Refer to one transient preview image stored in the execution substrate."""

    kind: Literal["preview"] = "preview"
    handle_id: str
    width: int
    height: int
    channels: int
    dtype: str
    backend: Literal["ray-object-store"] = "ray-object-store"


__all__ = ["ArrayHandle", "PreviewHandle"]
