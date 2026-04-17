"""Typed stage vocabulary owned by the pipeline registry."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .transport import TransportModel


class StageKey(StrEnum):
    """Central stage-key set for the pipeline."""

    INGEST = "ingest"
    SLAM = "slam"
    TRAJECTORY_EVALUATION = "trajectory.evaluate"
    REFERENCE_RECONSTRUCTION = "reference.reconstruct"
    CLOUD_EVALUATION = "cloud.evaluate"
    EFFICIENCY_EVALUATION = "efficiency.evaluate"
    SUMMARY = "summary"


class StageExecutorKind(StrEnum):
    """Execution strategy used to run one stage."""

    BATCH = "batch"
    STREAMING = "streaming"
    PROJECTION = "projection"


class StageAvailability(TransportModel):
    """Availability decision for one stage under one request/backend pair."""

    available: bool = True
    reason: str | None = None


class StageDefinition(TransportModel):
    """Registry entry for one supported pipeline stage."""

    key: StageKey
    title: str
    depends_on: list[StageKey] = Field(default_factory=list)
    output_keys: list[str] = Field(default_factory=list)
    executor_kind: StageExecutorKind
    description: str
    failure_modes: list[str] = Field(default_factory=list)


__all__ = [
    "StageAvailability",
    "StageDefinition",
    "StageExecutorKind",
    "StageKey",
]
