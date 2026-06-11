"""Trajectory-evaluation metric contracts and artifact manifest schema.

The trajectory evaluator writes aggregation-first metric artifacts. These DTOs
describe the persisted metric identity, long-form statistic rows, and lazy
error-series references consumed by post-run review surfaces.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from evo.core import metrics
from pydantic import Field, field_serializer, field_validator

from prml_vslam.utils import BaseData


class DiscoveredRun(BaseData):
    """Describe one normalized trajectory candidate under a run artifact root."""

    artifact_root: Path
    """Root directory for the selected run."""

    estimate_path: Path
    """Estimated trajectory path for the run."""

    point_cloud_path: Path | None = None
    """Estimated point-cloud path for optional aligned overlay materialization."""

    method: str | None = None
    """Known benchmark method id, when it can be inferred from the path."""

    label: str
    """Compact user-facing label for selection widgets."""


class SelectionSnapshot(BaseData):
    """Capture the resolved reference/candidate choice for trajectory computation."""

    sequence_slug: str
    """Selected sequence slug."""

    reference_path: Path | None = None
    """Reference TUM trajectory path when available."""

    target_frame: str | None = None
    """Target coordinate frame for alignment and metrics."""

    coordinate_status: str | None = None
    """Native coordinate status of the reference trajectory."""

    reference_source: str | None = None
    """Reference source key used for persisted alignment provenance."""

    run: DiscoveredRun
    """Selected artifact run."""


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


class SkippedMetricRecord(BaseData):
    """Record for a non-primary metric that was attempted but skipped due to a non-fatal error."""

    candidate_source: str
    """Estimate source that failed, e.g. ``vista/raw``."""

    metric_family: Literal["ape", "rpe"]
    pose_relation: metrics.PoseRelation
    reason: str
    """Exception message from evo describing why the metric could not be computed."""

    delta: float | None = None
    delta_unit: str | None = None

    @field_validator("pose_relation", mode="before")
    @classmethod
    def _validate_pose_relation(cls, value: object) -> object:
        if isinstance(value, str) and value in metrics.PoseRelation.__members__:
            return metrics.PoseRelation[value]
        return value

    @field_serializer("pose_relation", when_used="json")
    def _serialize_pose_relation(self, value: metrics.PoseRelation) -> str:
        return value.name


class TrajectoryEvaluationCase(BaseData):
    """Describe one persisted reference-vs-candidate trajectory metric case."""

    reference_path: Path
    """Reference TUM trajectory path used for this metric case."""

    candidate_path: Path
    """Candidate TUM trajectory path evaluated against the reference."""

    reference_source: str
    """Reference trajectory source key, for example ``ground_truth``."""

    candidate_source: str
    """Candidate source key, for example ``vista``, ``arcore``, or ``arkit``."""

    candidate_coordinate_status: str
    """Candidate coordinate status, for example ``raw``, ``source_native``, or ``aligned``."""

    metric_family: Literal["ape", "rpe"]
    """Metric family computed for this case."""

    pose_relation: metrics.PoseRelation
    """evo pose relation used for this metric case."""

    error_series_path: Path
    """Raw error-series artifact backing the case diagnostics."""

    matched_pairs: int
    """Number of associated pose pairs used by the metric."""

    delta: float | None = None
    """RPE delta value; ``None`` for APE cases."""

    delta_unit: str | None = None
    """RPE delta unit string, e.g. ``"meters"``; ``None`` for APE cases."""

    @field_validator("pose_relation", mode="before")
    @classmethod
    def _validate_pose_relation(cls, value: object) -> object:
        if isinstance(value, str) and value in metrics.PoseRelation.__members__:
            return metrics.PoseRelation[value]
        return value

    @field_serializer("pose_relation", when_used="json")
    def _serialize_pose_relation(self, value: metrics.PoseRelation) -> str:
        return value.name


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

    evaluation_cases: list[TrajectoryEvaluationCase] = Field(default_factory=list)
    """Structured per-candidate trajectory metric cases produced by the evaluator."""

    skipped_metrics: list[SkippedMetricRecord] = Field(default_factory=list)
    """Non-primary metrics that were attempted but skipped due to non-fatal errors."""


__all__ = [
    "DiscoveredRun",
    "SelectionSnapshot",
    "SkippedMetricRecord",
    "TrajectoryEvaluationCase",
    "TrajectoryEvaluationManifest",
    "TrajectoryMetricResultRow",
]
