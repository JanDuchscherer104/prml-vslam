"""Typed stage vocabulary owned by the pipeline registry.

This module contains the shared stage ids and availability payloads that
:mod:`prml_vslam.pipeline.stage_registry` uses to compile :class:`RunPlan`
values. It does not execute stages itself; it only names and describes the
stage vocabulary the rest of the pipeline agrees on.
"""

from __future__ import annotations

from enum import StrEnum

from .transport import TransportModel


class StageKey(StrEnum):
    """Name the canonical linear stage vocabulary for the repository pipeline."""

    INGEST = "ingest"
    SLAM = "slam"
    GROUND_ALIGNMENT = "ground.align"
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
            StageKey.GROUND_ALIGNMENT: "Detect Ground Plane",
            StageKey.TRAJECTORY_EVALUATION: "Evaluate Trajectory",
            StageKey.REFERENCE_RECONSTRUCTION: "Build Reference Reconstruction",
            StageKey.CLOUD_EVALUATION: "Evaluate Dense Cloud",
            StageKey.EFFICIENCY_EVALUATION: "Measure Efficiency",
            StageKey.SUMMARY: "Write Run Summary",
        }[self]


class StageAvailability(TransportModel):
    """Record whether one stage is executable for one request/backend pairing."""

    available: bool = True
    reason: str | None = None


class StageDefinition(TransportModel):
    """Carry the stable identity for one stage registered in the planner."""

    key: StageKey


__all__ = [
    "StageAvailability",
    "StageDefinition",
    "StageKey",
]
