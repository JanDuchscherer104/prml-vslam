"""Derived alignment contracts and services."""

from typing import Any

from .contracts import AlignmentConfig, GroundAlignmentConfig


def __getattr__(name: str) -> Any:
    if name == "GroundAlignmentService":
        from .services import GroundAlignmentService

        return GroundAlignmentService
    raise AttributeError(name)


__all__ = [
    "AlignmentConfig",
    "GroundAlignmentConfig",
    "GroundAlignmentService",
]
