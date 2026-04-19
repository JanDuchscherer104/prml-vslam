"""Typed stage vocabulary owned by the pipeline registry."""

from __future__ import annotations

from enum import StrEnum

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

    @property
    def label(self) -> str:
        """Return the human-readable label shown in plan previews."""
        return {
            StageKey.INGEST: "Normalize Input Sequence",
            StageKey.SLAM: "Run SLAM Backend",
            StageKey.TRAJECTORY_EVALUATION: "Evaluate Trajectory",
            StageKey.REFERENCE_RECONSTRUCTION: "Build Reference Reconstruction",
            StageKey.CLOUD_EVALUATION: "Evaluate Dense Cloud",
            StageKey.EFFICIENCY_EVALUATION: "Measure Efficiency",
            StageKey.SUMMARY: "Write Run Summary",
        }[self]


class StageAvailability(TransportModel):
    """Availability decision for one stage under one request/backend pair."""

    available: bool = True
    reason: str | None = None


class StageDefinition(TransportModel):
    """Registry entry for one supported pipeline stage."""

    key: StageKey


__all__ = [
    "StageAvailability",
    "StageDefinition",
    "StageKey",
]
