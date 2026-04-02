"""Typed state and view models for the packaged Streamlit app."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import numpy as np
from jaxtyping import Float
from pydantic import BaseModel, ConfigDict, Field

from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.pipeline.contracts import MethodId


class AppPageId(StrEnum):
    """Top-level pages exposed by the packaged Streamlit app."""

    RECORD3D = "record3d"
    METRICS = "metrics"

    @property
    def label(self) -> str:
        """Return the user-facing page label."""
        return {
            AppPageId.RECORD3D: "Record3D",
            AppPageId.METRICS: "Metrics",
        }[self]


class DatasetId(StrEnum):
    """Datasets exposed through the metrics app."""

    ADVIO = "advio"

    @property
    def label(self) -> str:
        """Return the short user-facing dataset label."""
        return {
            DatasetId.ADVIO: "ADVIO",
        }[self]


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


class EvaluationControls(BaseModel):
    """User-controlled `evo` evaluation options."""

    model_config = ConfigDict(validate_assignment=True)

    pose_relation: PoseRelationId = PoseRelationId.TRANSLATION_PART
    """Trajectory component evaluated by `evo`."""

    align: bool = True
    """Whether rigid alignment should be applied before scoring."""

    correct_scale: bool = True
    """Whether scale correction should be enabled during alignment."""

    max_diff_s: float = 0.02
    """Maximum timestamp-association gap in seconds."""


class MetricsPageState(BaseModel):
    """Persisted selector state for the metrics page."""

    model_config = ConfigDict(validate_assignment=True)

    dataset: DatasetId = DatasetId.ADVIO
    """Selected dataset."""

    sequence_slug: str | None = None
    """Selected dataset sequence, for example `advio-15`."""

    run_root: Path | None = None
    """Selected artifact root for one evaluated run."""

    evaluation: EvaluationControls = Field(default_factory=EvaluationControls)
    """Current `evo` controls."""

    result_path: Path | None = None
    """Most recently loaded or computed persisted result path."""


class Record3DPageState(BaseModel):
    """Persisted selector state for the Record3D live-stream page."""

    model_config = ConfigDict(validate_assignment=True)

    transport: Record3DTransportId = Record3DTransportId.USB
    """Selected Record3D transport."""

    usb_device_index: int = 0
    """Zero-based USB device index selected in the app."""

    wifi_device_address: str = "192.168.159.24"
    """User-supplied Wi-Fi device address."""

    is_running: bool = False
    """Whether the current browser session expects a live stream to be active."""


class AppState(BaseModel):
    """Fully typed app state persisted in Streamlit session storage."""

    model_config = ConfigDict(validate_assignment=True)

    current_page: AppPageId = AppPageId.RECORD3D
    """Currently selected top-level page."""

    record3d: Record3DPageState = Field(default_factory=Record3DPageState)
    """Record3D page selector state."""

    metrics: MetricsPageState = Field(default_factory=MetricsPageState)
    """Metrics-page selector state."""


class DiscoveredRun(BaseModel):
    """One run discovered under the configured artifacts root."""

    artifact_root: Path
    """Root directory for the selected run."""

    estimate_path: Path
    """Estimated trajectory path for the run."""

    method: MethodId | None = None
    """Known benchmark method, when it can be inferred from the path."""

    label: str
    """Compact user-facing label for selection widgets."""


class SelectionSnapshot(BaseModel):
    """Resolved dataset-selection snapshot for one app render."""

    dataset: DatasetId
    """Selected dataset."""

    sequence_slug: str
    """Selected sequence slug."""

    dataset_root: Path
    """Root directory for the selected dataset."""

    reference_path: Path | None = None
    """Reference TUM trajectory path when available."""

    run: DiscoveredRun
    """Selected artifact run."""


class MetricStats(BaseModel):
    """Summary metrics reported by `evo`."""

    rmse: float
    """Root-mean-square error."""

    mean: float
    """Mean error."""

    median: float
    """Median error."""

    std: float
    """Standard deviation of the error."""

    min: float
    """Minimum error."""

    max: float
    """Maximum error."""

    sse: float
    """Sum of squared errors."""


class TrajectorySeries(BaseModel):
    """One trajectory rendered in the overlay figure."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    """Series name used in the legend."""

    positions_xyz: Float[np.ndarray, "num_points 3"]
    """Trajectory XYZ positions in meters."""

    timestamps_s: Float[np.ndarray, "num_points"]  # noqa: F821, UP037
    """Timestamps associated with the positions."""


class ErrorSeries(BaseModel):
    """Scalar `evo` error profile rendered as a Plotly line chart."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    timestamps_s: Float[np.ndarray, "num_points"]  # noqa: F821, UP037
    """Timestamps in seconds."""

    values: Float[np.ndarray, "num_points"]  # noqa: F821, UP037
    """Per-pair error values."""


class EvaluationArtifact(BaseModel):
    """Loaded or freshly computed persisted `evo` result."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path
    """Persisted native `evo` result path."""

    controls: EvaluationControls
    """Controls used to produce this result."""

    title: str
    """Short result title emitted by `evo`."""

    matched_pairs: int
    """Number of associated trajectory pairs used by `evo`."""

    stats: MetricStats
    """Scalar metrics reported by `evo`."""

    reference_path: Path
    """Reference TUM trajectory path."""

    estimate_path: Path
    """Estimated TUM trajectory path."""

    trajectories: list[TrajectorySeries] = Field(default_factory=list)
    """Trajectory overlays loaded from the persisted `evo` result."""

    error_series: ErrorSeries | None = None
    """Optional per-pair error profile."""


__all__ = [
    "AppPageId",
    "AppState",
    "DatasetId",
    "DiscoveredRun",
    "ErrorSeries",
    "EvaluationArtifact",
    "EvaluationControls",
    "MetricStats",
    "MetricsPageState",
    "PoseRelationId",
    "Record3DPageState",
    "SelectionSnapshot",
    "TrajectorySeries",
]
