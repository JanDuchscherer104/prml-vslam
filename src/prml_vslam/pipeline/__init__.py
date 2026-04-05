"""Pipeline orchestration contracts re-exported for package users."""

from importlib import import_module
from typing import TYPE_CHECKING

from .contracts import (
    PipelineMode,
    RunPlan,
    RunRequest,
    RunSummary,
    SequenceManifest,
    SlamArtifacts,
)
from .protocols import SlamBackend, SlamSession

if TYPE_CHECKING:
    from .session import PipelineSessionService, PipelineSessionSnapshot, PipelineSessionState

__all__ = [
    "PipelineMode",
    "PipelineSessionService",
    "PipelineSessionSnapshot",
    "PipelineSessionState",
    "RunPlan",
    "RunRequest",
    "SequenceManifest",
    "RunSummary",
    "SlamArtifacts",
    "SlamBackend",
    "SlamSession",
]


def __getattr__(name: str) -> object:
    if name in {"PipelineSessionService", "PipelineSessionSnapshot", "PipelineSessionState"}:
        return getattr(import_module(".session", __name__), name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
