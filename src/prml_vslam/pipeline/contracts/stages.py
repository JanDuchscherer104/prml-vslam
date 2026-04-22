"""Typed stage vocabulary and planning helper contracts.

This module names the canonical stage keys shared across planning, runtime
state, and artifact provenance. It does not execute stages itself.
"""

from __future__ import annotations

from enum import StrEnum

from .transport import TransportModel


class StageKey(StrEnum):
    """Name the current executable linear stage vocabulary.

    These values are persisted in existing run events, summaries, and manifests.
    The target public vocabulary uses names such as ``source``,
    ``gravity.align``, and ``evaluate.trajectory``; aliases are handled by
    :mod:`prml_vslam.pipeline.config` until the migration-removal work package
    retires the current spellings.
    """

    INGEST = "ingest"
    SLAM = "slam"
    GRAVITY_ALIGNMENT = "gravity.align"
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
            StageKey.GRAVITY_ALIGNMENT: "Detect Ground Plane",
            StageKey.TRAJECTORY_EVALUATION: "Evaluate Trajectory",
            StageKey.REFERENCE_RECONSTRUCTION: "Build Reference Reconstruction",
            StageKey.CLOUD_EVALUATION: "Evaluate Dense Cloud",
            StageKey.EFFICIENCY_EVALUATION: "Measure Efficiency",
            StageKey.SUMMARY: "Write Run Summary",
        }[self]


# TODO(pipeline-refactor/WP-10): Remove after stage config helpers stop using
# this transitional availability DTO.
class StageAvailability(TransportModel):
    """Record whether one stage is executable for one request/backend pairing."""

    available: bool = True
    reason: str | None = None


__all__ = [
    "StageAvailability",
    "StageKey",
]
