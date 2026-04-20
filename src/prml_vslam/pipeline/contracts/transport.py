"""Strict transport-safe model base for pipeline-owned runtime contracts.

This module contains the strict base model used when pipeline commands, events,
snapshots, and small runtime payloads travel between processes or actors.
:class:`TransportModel` tightens validation so those DTOs stay portable and
predictable across the execution substrate.
"""

from __future__ import annotations

from pydantic import ConfigDict

from prml_vslam.utils import BaseData


class TransportModel(BaseData):
    """Provide the strict validation baseline for transport-safe pipeline DTOs."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        arbitrary_types_allowed=False,
        validate_assignment=True,
        validate_default=True,
        protected_namespaces=(),
    )


__all__ = ["TransportModel"]
