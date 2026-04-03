"""Typed evaluation contracts for persisted artifacts and plotting, not a middleware layer."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import numpy as np
from jaxtyping import Float
from pydantic import Field

from prml_vslam.methods.interfaces import MethodId
from prml_vslam.utils import BaseConfig, BaseData


class PoseRelationId(StrEnum):
    """Stable `evo` pose-relation options exposed in the app."""

    TRANSLATION_PART = "translation_part"
    FULL_TRANSFORMATION = "full_transformation"
    ROTATION_ANGLE_DEG = "rotation_angle_deg"
    ROTATION_ANGLE_RAD = "rotation_angle_rad"

    @property
    def label(self) -> str:
        """Return the user-facing label."""
        return {
            PoseRelationId.TRANSLATION_PART: "Translation Part",
            PoseRelationId.FULL_TRANSFORMATION: "Full Transformation",
            PoseRelationId.ROTATION_ANGLE_DEG: "Rotation Angle (deg)",
            PoseRelationId.ROTATION_ANGLE_RAD: "Rotation Angle (rad)",
        }[self]


class EvaluationControls(BaseConfig):
    """User-controlled `evo` evaluation options."""

    pose_relation: PoseRelationId = PoseRelationId.TRANSLATION_PART
    align: bool = True
    correct_scale: bool = True
    max_diff_s: float = 0.02


class MetricStats(BaseData):
    """Summary metrics reported by `evo`."""

    rmse: float
    mean: float
    median: float
    std: float
    min: float
    max: float
    sse: float

    @classmethod
    def from_error_values(cls, error_values: np.ndarray) -> MetricStats:
        """Build scalar summary metrics from one error series."""
        squared = np.square(error_values)
        return cls(
            rmse=float(np.sqrt(np.mean(squared))),
            mean=float(np.mean(error_values)),
            median=float(np.median(error_values)),
            std=float(np.std(error_values)),
            min=float(np.min(error_values)),
            max=float(np.max(error_values)),
            sse=float(np.sum(squared)),
        )


class TrajectorySeries(BaseData):
    """One trajectory rendered in the overlay figure."""

    name: str
    positions_xyz: Float[np.ndarray, "num_points 3"]  # noqa: F722
    timestamps_s: Float[np.ndarray, "num_points"]  # noqa: F821, UP037


class ErrorSeries(BaseData):
    """Scalar `evo` error profile rendered as a Plotly line chart."""

    timestamps_s: Float[np.ndarray, "num_points"]  # noqa: F821, UP037
    values: Float[np.ndarray, "num_points"]  # noqa: F821, UP037


class EvaluationArtifact(BaseData):
    """Loaded or freshly computed persisted `evo` result."""

    path: Path
    controls: EvaluationControls
    title: str
    matched_pairs: int
    stats: MetricStats
    reference_path: Path
    estimate_path: Path
    trajectories: list[TrajectorySeries] = Field(default_factory=list)
    error_series: ErrorSeries | None = None

    @classmethod
    def from_payload(
        cls,
        *,
        path: Path,
        controls: EvaluationControls,
        payload: dict[str, object],
        reference_path: Path,
        estimate_path: Path,
        trajectories: tuple[TrajectorySeries, TrajectorySeries],
    ) -> EvaluationArtifact:
        """Build an evaluation artifact from one persisted mock payload."""
        reference_trajectory, estimate_trajectory = trajectories
        return cls(
            path=path,
            controls=controls,
            title=str(payload["title"]),
            matched_pairs=int(payload["matched_pairs"]),
            stats=MetricStats.model_validate(payload["stats"]),
            reference_path=reference_path,
            estimate_path=estimate_path,
            trajectories=[reference_trajectory, estimate_trajectory],
            error_series=ErrorSeries(
                timestamps_s=np.asarray(payload["error_timestamps_s"], dtype=np.float64),
                values=np.asarray(payload["error_values"], dtype=np.float64),
            ),
        )


class DiscoveredRun(BaseData):
    """One benchmark run discovered under the configured artifacts root."""

    artifact_root: Path
    """Root directory for the selected run."""

    estimate_path: Path
    """Estimated trajectory path for the run."""

    method: MethodId | None = None
    """Known benchmark method, when it can be inferred from the path."""

    label: str
    """Compact user-facing label for selection widgets."""


class SelectionSnapshot(BaseData):
    """Resolved dataset-selection snapshot for one metrics render."""

    sequence_slug: str
    """Selected sequence slug."""

    reference_path: Path | None = None
    """Reference TUM trajectory path when available."""

    run: DiscoveredRun
    """Selected artifact run."""


__all__ = [
    "DiscoveredRun",
    "ErrorSeries",
    "EvaluationArtifact",
    "EvaluationControls",
    "MetricStats",
    "PoseRelationId",
    "SelectionSnapshot",
    "TrajectorySeries",
]
