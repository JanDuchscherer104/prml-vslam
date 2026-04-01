"""Typed state and discovery models for the PRML VSLAM Streamlit app."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from prml_vslam.eval import PoseRelationId, TrajectoryEvaluationResult
from prml_vslam.pipeline.contracts import MethodId, PipelineMode


class DatasetId(StrEnum):
    """Datasets exposed through the metrics-first Streamlit app."""

    ADVIO = "advio"

    @property
    def label(self) -> str:
        """Return a short user-facing dataset label."""
        return {
            DatasetId.ADVIO: "ADVIO",
        }[self]


class EvaluationControls(BaseModel):
    """User-controlled `evo` evaluation options."""

    model_config = ConfigDict(validate_assignment=True)

    pose_relation: PoseRelationId = PoseRelationId.TRANSLATION_PART
    """Pose relation reported by `evo`."""

    align: bool = True
    """Whether rigid alignment should be applied before evaluation."""

    correct_scale: bool = True
    """Whether Sim(3)-style scale correction should be enabled."""

    max_diff_s: float = 0.02
    """Maximum timestamp association difference in seconds."""


class MetricsPageState(BaseModel):
    """Persistent selection state for the metrics page."""

    model_config = ConfigDict(validate_assignment=True)

    dataset: DatasetId = DatasetId.ADVIO
    """Currently selected dataset."""

    sequence_id: int | None = None
    """Currently selected sequence identifier."""

    run_path: Path | None = None
    """Selected artifact root for one evaluated run."""

    evaluation: EvaluationControls = Field(default_factory=EvaluationControls)
    """Current `evo` control settings."""

    last_result_path: Path | None = None
    """Most recently computed or viewed evaluation JSON path."""


class DatasetPageState(BaseModel):
    """Persistent selection state for the dataset explorer page."""

    model_config = ConfigDict(validate_assignment=True)

    dataset: DatasetId = DatasetId.ADVIO
    """Currently selected dataset."""

    sequence_id: int | None = None
    """Currently selected sequence identifier."""


class StreamingPageState(BaseModel):
    """Persistent selection state for the Record3D streaming page."""

    model_config = ConfigDict(validate_assignment=True)

    device_address: str = ""
    """Most recently targeted Record3D Wi-Fi device address."""

    connection_state: str = "idle"
    """Most recent Record3D Wi-Fi connection state."""

    error_message: str = ""
    """Last surfaced Record3D Wi-Fi error message."""

    metadata: dict[str, object] = Field(default_factory=dict)
    """Latest metadata payload emitted by the browser-side Wi-Fi viewer."""

    show_inv_dist_std: bool = True
    """Whether the Wi-Fi viewer should show the optional placeholder pane."""

    equalize_depth_histogram: bool = False
    """Whether the Wi-Fi viewer should equalize the depth preview histogram."""


class AppState(BaseModel):
    """Fully typed app state persisted in Streamlit session storage."""

    model_config = ConfigDict(validate_assignment=True)

    metrics: MetricsPageState = Field(default_factory=MetricsPageState)
    """Metrics-page selection and evaluation state."""

    dataset: DatasetPageState = Field(default_factory=DatasetPageState)
    """Dataset-page selection state."""

    streaming: StreamingPageState = Field(default_factory=StreamingPageState)
    """Record3D streaming-page state."""


class StoredTrajectoryEvaluation(BaseModel):
    """Persisted trajectory evaluation discovered under one run root."""

    path: Path
    """JSON file path that stores the evaluation result."""

    result: TrajectoryEvaluationResult
    """Parsed repo-owned evaluation payload."""


class DiscoveredRun(BaseModel):
    """One run discovered under the configured artifacts root."""

    artifact_root: Path
    """Root directory for the selected run."""

    sequence_id: int
    """Associated dataset sequence identifier."""

    mode: PipelineMode
    """Execution mode inferred from the artifact layout."""

    method: MethodId
    """Method inferred from the artifact layout."""

    estimate_path: Path
    """Estimated trajectory path for this run."""

    trajectory_metadata_path: Path | None = None
    """Optional trajectory metadata sidecar."""

    evaluations: list[StoredTrajectoryEvaluation] = Field(default_factory=list)
    """Persisted evaluations discovered under the run's evaluation directory."""

    @property
    def display_label(self) -> str:
        """Return a compact run label for selection widgets."""
        method_label = self.method.value.replace("_", " ").upper()
        return f"{method_label} · {self.mode.value} · {self.artifact_root.name}"


class MetricsSelection(BaseModel):
    """Resolved dataset-sequence-run selection for the metrics page."""

    dataset: DatasetId
    """Resolved dataset identifier."""

    sequence_id: int
    """Resolved sequence identifier."""

    sequence_name: str
    """Resolved human-readable sequence name."""

    run: DiscoveredRun
    """Resolved artifact run."""

    reference_path: Path | None = None
    """Existing reference trajectory path if already available."""

    reference_csv_path: Path | None = None
    """Reference pose CSV used to create a TUM trajectory on explicit evaluation."""


class TrajectoryPoint(BaseModel):
    """One point parsed from a TUM trajectory for plotting."""

    timestamp_s: float
    """Point timestamp in seconds."""

    x: float
    """X translation in meters."""

    y: float
    """Y translation in meters."""

    z: float
    """Z translation in meters."""


__all__ = [
    "AppState",
    "DatasetId",
    "DatasetPageState",
    "DiscoveredRun",
    "EvaluationControls",
    "MetricsPageState",
    "MetricsSelection",
    "StreamingPageState",
    "StoredTrajectoryEvaluation",
    "TrajectoryPoint",
]
