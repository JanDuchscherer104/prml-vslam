"""Generic transient payload references for stage runtime updates.

This module owns the backend-neutral metadata object used when live pipeline
observers need to refer to bulk payloads without exposing the runtime substrate
that stores them. It does not own payload resolution or backend-specific handle
APIs.
"""

from __future__ import annotations

from pydantic import Field

from prml_vslam.pipeline.contracts.transport import TransportModel
from prml_vslam.utils import JsonScalar


class TransientPayloadRef(TransportModel):
    """Reference one run-scoped live payload stored outside durable artifacts.

    The reference is transport-safe metadata only. Runtime backends own payload
    lookup, eviction, and release semantics; durable scientific outputs should
    continue to use artifact references instead of this DTO.
    """

    handle_id: str
    """Run-scoped opaque identifier assigned by the payload store."""

    payload_kind: str
    """Semantic payload family such as ``image``, ``depth``, or ``point_cloud``."""

    media_type: str = "application/octet-stream"
    """MIME-like media type for consumers that need decoding hints."""

    shape: tuple[int, ...] | None = None
    """Array shape when the payload is tensor-like."""

    dtype: str | None = None
    """Array dtype when the payload is tensor-like."""

    size_bytes: int | None = Field(default=None, ge=0)
    """Approximate payload size in bytes when known."""

    metadata: dict[str, JsonScalar] = Field(default_factory=dict)
    """Small transport-safe payload hints that do not deserve dedicated fields."""


__all__ = ["TransientPayloadRef"]
