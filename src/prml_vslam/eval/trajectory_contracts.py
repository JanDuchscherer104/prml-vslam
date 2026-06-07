"""Trajectory-evaluation metric contracts and artifact manifest schema.

The trajectory evaluator writes aggregation-first metric artifacts. These DTOs
describe the persisted metric identity, long-form statistic rows, and lazy
error-series references consumed by post-run review surfaces.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from evo.core import metrics
from pydantic import Field

from prml_vslam.utils import BaseData


class TrajectoryMetricResultRow(BaseData):
    """Long-form trajectory metric statistic row for cross-run aggregation."""

    run_id: str
    """Run identifier or artifact-root slug."""

    sequence_id: str
    """Source sequence identifier."""

    reference_source: str
    """Reference trajectory source, for example `ground_truth` or `arkit`."""

    estimate_source: str
    """Estimated trajectory source, for example `vslam`, `arcore`, or `arkit`."""

    metric_family: Literal["ape", "rpe"]
    """Metric family for this statistic."""

    pose_relation: metrics.PoseRelation
    """evo pose relation for this statistic."""

    statistic: str
    """Statistic key, for example `rmse`, `median`, or `sse`."""

    value: float
    """Statistic value."""

    unit: str | None = None
    """Physical unit for the error value, when known."""

    matched_pairs: int
    """Number of associated pose pairs used by the metric."""

    delta: float | None = None
    """RPE delta, when applicable."""

    delta_unit: str | None = None
    """RPE delta unit, when applicable."""

    error_series_path: Path | None = None
    """Path to the raw error series backing distribution plots."""


class TrajectoryEvaluationManifest(BaseData):
    """Canonical manifest for one run's trajectory evaluation outputs."""

    artifact_root: Path
    """Run artifact root that owns this evaluation."""

    sequence_id: str
    """Source sequence identifier."""

    run_id: str
    """Run identifier used for aggregation rows."""

    reference_trajectories: list[Path] = Field(default_factory=list)
    """Reference trajectory paths considered by the evaluation."""

    candidate_trajectories: list[Path] = Field(default_factory=list)
    """Candidate trajectory paths considered by the evaluation."""

    error_series_paths: list[Path] = Field(default_factory=list)
    """Raw error-series artifacts produced by the trajectory evaluator."""


__all__ = [
    "TrajectoryEvaluationManifest",
    "TrajectoryMetricResultRow",
]
