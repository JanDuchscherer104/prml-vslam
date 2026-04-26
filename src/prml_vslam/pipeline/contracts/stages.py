"""Typed stage vocabulary shared across planning, runtime, and provenance."""

from __future__ import annotations

from enum import StrEnum


class StageKey(StrEnum):
    """Name the canonical target stage vocabulary."""

    SOURCE = "source"
    SLAM = "slam"
    GRAVITY_ALIGNMENT = "gravity.align"
    TRAJECTORY_EVALUATION = "evaluate.trajectory"
    RECONSTRUCTION = "reconstruction"
    CLOUD_EVALUATION = "evaluate.cloud"
    SUMMARY = "summary"

    @property
    def label(self) -> str:
        """Return the human-readable label shown in plan previews."""
        return {
            StageKey.SOURCE: "Normalize Input Sequence",
            StageKey.SLAM: "Run SLAM Backend",
            StageKey.GRAVITY_ALIGNMENT: "Detect Ground Plane",
            StageKey.TRAJECTORY_EVALUATION: "Evaluate Trajectory",
            StageKey.RECONSTRUCTION: "Build Reconstruction",
            StageKey.CLOUD_EVALUATION: "Evaluate Dense Cloud",
            StageKey.SUMMARY: "Write Run Summary",
        }[self]


__all__ = [
    "StageKey",
]
