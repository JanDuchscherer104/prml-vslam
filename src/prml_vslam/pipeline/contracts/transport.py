"""Strict transport-safe model base for pipeline command and event contracts."""

from __future__ import annotations

from pydantic import ConfigDict

from prml_vslam.utils import BaseData


class TransportModel(BaseData):
    """Strict model used for portable pipeline contracts."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        arbitrary_types_allowed=False,
        validate_assignment=True,
        validate_default=True,
        protected_namespaces=(),
    )


__all__ = ["TransportModel"]
