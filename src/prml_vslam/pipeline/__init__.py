"""Pipeline orchestration contracts re-exported for package users."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "PipelineMode",
    "RunPlan",
    "RunRequest",
    "SequenceManifest",
    "RunSummary",
    "SlamArtifacts",
]


def __getattr__(name: str) -> object:
    if name in {"PipelineMode", "RunRequest"}:
        module = import_module(".contracts.request", __name__)
        return getattr(module, name)
    if name == "RunPlan":
        return import_module(".contracts.plan", __name__).RunPlan
    if name == "SequenceManifest":
        return import_module(".contracts.sequence", __name__).SequenceManifest
    if name == "RunSummary":
        return import_module(".contracts.provenance", __name__).RunSummary
    if name == "SlamArtifacts":
        return import_module(".contracts.artifacts", __name__).SlamArtifacts
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
