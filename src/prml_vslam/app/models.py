"""App-owned models for Streamlit page state, snapshots, and view selections."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field

from prml_vslam.methods.stage.config import MethodId
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.config import BackendSpec
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageRuntimeStatus
from prml_vslam.sources.datasets.advio import (
    AdvioDatasetSummary,
    AdvioDownloadPreset,
    AdvioDownloadRequest,
    AdvioLocalSceneStatus,
    AdvioModality,
    AdvioPoseFrameMode,
    AdvioPoseSource,
)
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.datasets.tum_rgbd import TumRgbdDownloadPreset, TumRgbdModality, TumRgbdPoseSource
from prml_vslam.sources.record3d.record3d import Record3DDevice, Record3DTransportId
from prml_vslam.utils import BaseData

from .preview_runtime import PacketSessionSnapshot


class AppPageId(StrEnum):
    """Top-level pages exposed by the packaged Streamlit app."""

    RECORD3D = "record3d"
    DATASETS = "datasets"
    PIPELINE = "pipeline"
    ARTIFACTS = "artifacts"
    METRICS = "metrics"

    @property
    def label(self) -> str:
        """Return the user-facing page label."""
        return {AppPageId.RECORD3D: "Record3D", AppPageId.DATASETS: "Datasets"}.get(self, self.value.capitalize())


class PreviewStreamState(StrEnum):
    """Lifecycle states shared by app-owned preview surfaces."""

    IDLE = "idle"
    CONNECTING = "connecting"
    STREAMING = "streaming"
    DISCONNECTED = "disconnected"
    FAILED = "failed"


ACTIVE_PREVIEW_STREAM_STATES = frozenset({PreviewStreamState.CONNECTING, PreviewStreamState.STREAMING})


class PreviewSessionSnapshot(PacketSessionSnapshot):
    """Common snapshot state shared by app-owned preview runtimes."""

    state: PreviewStreamState = PreviewStreamState.IDLE
    """Current lifecycle state of the preview."""


class Record3DStreamSnapshot(PreviewSessionSnapshot):
    """Latest Record3D preview snapshot shared inside the app layer."""

    transport: Record3DTransportId | None = None
    """Transport currently backing the snapshot, when active."""

    source_label: str = ""
    """Human-readable source descriptor such as a UDID or Wi-Fi address."""


class AdvioPreviewSnapshot(PreviewSessionSnapshot):
    """Latest dataset loop-preview snapshot shared inside the app layer."""

    sequence_id: int | str | None = None
    """Active dataset sequence identifier when a preview is selected."""

    sequence_label: str = ""
    """Human-readable label for the selected dataset sequence."""

    pose_source: AdvioPoseSource | TumRgbdPoseSource | None = None
    """Pose source currently used for the preview stream."""


class AdvioDownloadFormData(BaseData):
    """Typed ADVIO dataset-download form payload."""

    request: AdvioDownloadRequest
    submitted: bool = False


class AdvioPreviewFormData(BaseData):
    """Typed ADVIO preview action payload."""

    sequence_id: int
    pose_source: AdvioPoseSource
    normalize_video_orientation: bool = True
    start_requested: bool = False
    stop_requested: bool = False


class AdvioPageData(BaseData):
    """Computed ADVIO page render payload."""

    summary: AdvioDatasetSummary
    statuses: list[AdvioLocalSceneStatus]
    rows: list[dict[str, object]]
    notice_level: Literal["error", "warning", "success"] | None = None
    notice_message: str = ""


class AdvioPageState(BaseData):
    """Persisted selector state for the ADVIO dataset-management page."""

    selected_sequence_ids: list[int] = Field(default_factory=list)
    """Explicit scene selection for download actions."""

    download_preset: AdvioDownloadPreset = AdvioDownloadPreset.OFFLINE
    """Selected curated download bundle."""

    selected_modalities: list[AdvioModality] = Field(default_factory=list)
    """Optional explicit modality override."""

    overwrite_existing: bool = False
    """Whether download actions should overwrite local archives and extracted files."""

    explorer_sequence_id: int | None = None
    """Selected local sequence shown in the explorer section."""

    preview_sequence_id: int | None = None
    """Selected local sequence shown in the loop-preview section."""

    preview_pose_source: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH
    """Selected camera-pose source for the loop-preview stream."""

    preview_normalize_video_orientation: bool = True
    """Whether the preview should normalize video display orientation when available."""

    preview_is_running: bool = False
    """Whether the current browser session expects an ADVIO preview stream to be active."""


class TumRgbdPageState(BaseData):
    """Persisted selector state for the TUM RGB-D dataset-management tab."""

    selected_sequence_ids: list[str] = Field(default_factory=list)
    """Explicit scene selection for download actions."""

    download_preset: TumRgbdDownloadPreset = TumRgbdDownloadPreset.OFFLINE
    """Selected curated download bundle."""

    selected_modalities: list[TumRgbdModality] = Field(default_factory=list)
    """Optional explicit modality override."""

    overwrite_existing: bool = False
    """Whether download actions should overwrite local archives and extracted files."""

    explorer_sequence_id: str | None = None
    """Selected local sequence shown in the explorer section."""

    preview_sequence_id: str | None = None
    """Selected local sequence shown in the loop-preview section."""

    preview_pose_source: TumRgbdPoseSource = TumRgbdPoseSource.GROUND_TRUTH
    """Selected camera-pose source for the loop-preview stream."""

    preview_include_depth: bool = True
    """Whether the preview should include depth frames when available."""

    preview_is_running: bool = False
    """Whether the current browser session expects a TUM RGB-D preview stream to be active."""


class MetricsPageState(BaseData):
    """Persisted selector state for the metrics page."""

    dataset: DatasetId = DatasetId.ADVIO
    """Selected dataset."""

    sequence_slug: str | None = None
    """Selected dataset sequence, for example `advio-15`."""

    run_root: Path | None = None
    """Selected artifact root for one evaluated run."""

    result_path: Path | None = None
    """Most recently loaded or computed persisted result path."""


class ArtifactInspectorPageState(BaseData):
    """Persisted selector state for the artifact inspector page."""

    selected_run_root: Path | None = None
    """Selected discovered artifact root."""

    manual_run_root: str = ""
    """User-entered artifact root path."""

    use_manual_path: bool = False
    """Whether the manual path should override discovered run selection."""

    show_reconstruction_point_cloud: bool = True
    """Whether the reconstruction view should render the reference point cloud."""

    show_reconstruction_mesh: bool = True
    """Whether the reconstruction view should render the reference mesh."""

    reconstruction_max_points: int = 80_000
    """Maximum number of reference-cloud points rendered in Plotly."""

    reconstruction_target_triangles: int = 120_000
    """Target number of reference-mesh triangles rendered in Plotly."""

    reconstruction_mesh_opacity: float = 0.72
    """Mesh opacity used for the reconstruction Plotly trace."""

    reconstruction_mesh_color: str = "#2f6fed"
    """Mesh color used for the reconstruction Plotly trace."""

    comparison_show_slam_cloud: bool = True
    """Whether the SLAM-vs-reference comparison should render the SLAM cloud."""

    comparison_show_reference_cloud: bool = True
    """Whether the SLAM-vs-reference comparison should render the reference cloud."""

    comparison_show_reference_mesh: bool = True
    """Whether the SLAM-vs-reference comparison should render the reference mesh."""

    comparison_show_trajectories: bool = True
    """Whether the SLAM-vs-reference comparison should render available trajectories."""

    comparison_slam_max_points: int = 80_000
    """Maximum sampled SLAM cloud points rendered in comparison plots."""

    comparison_reference_max_points: int = 80_000
    """Maximum sampled reference cloud points rendered in comparison plots."""

    comparison_target_triangles: int = 120_000
    """Target reference mesh triangles rendered in comparison plots."""

    rerun_validation_max_keyed_clouds: int = 20
    """Maximum keyed clouds included in generated Rerun validation bundles."""

    rerun_validation_max_render_points: int = 30_000
    """Maximum points rendered per cloud in generated Rerun validation plots."""


class Record3DPageState(BaseData):
    """Persisted selector state for the Record3D live-stream page."""

    transport: Record3DTransportId = Record3DTransportId.USB
    """Selected Record3D transport."""

    usb_device_index: int = 0
    """Zero-based USB device index selected in the app."""

    wifi_device_address: str = "192.168.159.24"
    """User-supplied Wi-Fi device address."""

    is_running: bool = False
    """Whether the current browser session expects a live stream to be active."""


class Record3DPageAction(BaseData):
    """Typed Record3D page action payload."""

    transport: Record3DTransportId
    usb_device_index: int | None = None
    wifi_device_address: str | None = None
    start_requested: bool = False
    stop_requested: bool = False


class Record3DTransportSelection(BaseData):
    """Resolved Record3D transport inputs for one page render."""

    transport: Record3DTransportId
    usb_device_index: int = 0
    wifi_device_address: str = ""
    usb_devices: list[Record3DDevice] = Field(default_factory=list)
    usb_error_message: str = ""
    input_error: str | None = None


class PipelineSourceId(StrEnum):
    """Input-source families supported by the bounded pipeline app surface."""

    ADVIO = "advio"
    RECORD3D = "record3d"

    @property
    def label(self) -> str:
        """Return the user-facing source label."""
        return "Record3D" if self is PipelineSourceId.RECORD3D else "ADVIO"


class PipelineTelemetryViewMode(StrEnum):
    """Telemetry presentation modes for the Pipeline run console."""

    LATEST = "latest"
    ROLLING = "rolling"

    @property
    def label(self) -> str:
        """Return the user-facing mode label."""
        return "Rolling Live" if self is PipelineTelemetryViewMode.ROLLING else "Latest"


class PipelineTelemetryMetricId(StrEnum):
    """Stage runtime metrics that can be plotted from live telemetry samples."""

    FPS = "fps"
    THROUGHPUT = "throughput"
    LATENCY_MS = "latency_ms"
    QUEUE_DEPTH = "queue_depth"
    BACKLOG_COUNT = "backlog_count"
    PROCESSED_ITEMS = "processed_items"
    IN_FLIGHT_COUNT = "in_flight_count"

    @property
    def label(self) -> str:
        """Return the user-facing metric label."""
        return {
            PipelineTelemetryMetricId.FPS: "FPS",
            PipelineTelemetryMetricId.THROUGHPUT: "Throughput",
            PipelineTelemetryMetricId.LATENCY_MS: "Latency",
            PipelineTelemetryMetricId.QUEUE_DEPTH: "Queue Depth",
            PipelineTelemetryMetricId.BACKLOG_COUNT: "Backlog",
            PipelineTelemetryMetricId.PROCESSED_ITEMS: "Processed Items",
            PipelineTelemetryMetricId.IN_FLIGHT_COUNT: "In Flight",
        }[self]

    @property
    def unit_label(self) -> str:
        """Return the default y-axis unit label."""
        return {
            PipelineTelemetryMetricId.FPS: "fps",
            PipelineTelemetryMetricId.THROUGHPUT: "items/s",
            PipelineTelemetryMetricId.LATENCY_MS: "ms",
            PipelineTelemetryMetricId.QUEUE_DEPTH: "items",
            PipelineTelemetryMetricId.BACKLOG_COUNT: "items",
            PipelineTelemetryMetricId.PROCESSED_ITEMS: "items",
            PipelineTelemetryMetricId.IN_FLIGHT_COUNT: "items",
        }[self]


class PipelinePageState(BaseData):
    """Persisted selector state for the Pipeline run console."""

    config_path: Path | None = None
    """Selected pipeline request TOML used to instantiate the demo run."""

    experiment_name: str = ""
    """Editable experiment name for the in-app request preview."""

    source_kind: PipelineSourceId = PipelineSourceId.ADVIO
    """Selected source family for the bounded pipeline surface."""

    advio_sequence_id: int | None = None
    """Selected ADVIO sequence id when the source family is `ADVIO`."""

    dataset_frame_stride: int = 1
    """Dataset frame stride used by the bounded pipeline source."""

    dataset_target_fps: float | None = None
    """Optional target FPS used instead of dataset frame stride."""

    mode: PipelineMode = PipelineMode.OFFLINE
    """Selected pipeline mode."""

    method: MethodId = MethodId.VISTA
    """Selected SLAM backend label."""

    slam_max_frames: int | None = None
    """Optional frame cap for the current request."""

    slam_backend_spec: BackendSpec | None = None
    """Typed backend spec preserved from the selected request template."""

    emit_dense_points: bool = True
    """Whether dense geometry artifacts should be emitted."""

    emit_sparse_points: bool = True
    """Whether sparse geometry artifacts should be emitted."""

    trajectory_eval_enabled: bool = False
    """Whether trajectory evaluation should be planned."""

    evaluate_cloud: bool = False
    """Whether dense-cloud evaluation should be planned."""

    ground_alignment_enabled: bool = False
    """Whether ground-plane alignment should be planned."""

    reconstruction_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("reconstruction_enabled", "reference_enabled"),
    )
    """Whether reference reconstruction should be planned."""

    connect_live_viewer: bool = False
    """Whether to connect the Rerun live viewer via gRPC."""

    export_viewer_rrd: bool = False
    """Whether to export the Rerun `.rrd` viewer artifact."""

    grpc_url: str = "rerun+http://127.0.0.1:9876/proxy"
    """Rerun gRPC endpoint used when the live viewer is enabled."""

    viewer_blueprint_path: Path | None = None
    """Optional Rerun blueprint path."""

    preserve_native_rerun: bool = True
    """Whether native upstream `.rrd` files should be preserved."""

    frusta_history_window_streaming: int = 20
    """Bounded frusta history window for streaming viewer output."""

    frusta_history_window_offline: int | None = None
    """Optional frusta history window for offline viewer output."""

    show_tracking_trajectory: bool = True
    """Whether the viewer should show the tracking trajectory."""

    log_source_rgb: bool = False
    """Whether source RGB frames should be logged to the repo-owned viewer sink."""

    log_diagnostic_preview: bool = False
    """Whether method diagnostic previews should be logged to the viewer sink."""

    log_camera_image_rgb: bool = False
    """Whether camera RGB image planes should be logged in the 3D viewer branch."""

    record3d_usb_device_index: int = 0
    """Zero-based USB device index used by the bounded pipeline page."""

    record3d_transport: Record3DTransportId = Record3DTransportId.USB
    """Selected Record3D transport used by the bounded pipeline page."""

    record3d_wifi_device_address: str = "192.168.159.24"
    """User-supplied Record3D Wi-Fi preview device address for the pipeline page."""

    record3d_frame_timeout_seconds: float = 5.0
    """Maximum Record3D frame wait time used by the pipeline source."""

    pose_source: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH
    """Selected pose source injected into the ADVIO replay packets."""

    pose_frame_mode: AdvioPoseFrameMode = AdvioPoseFrameMode.PROVIDER_WORLD
    """Selected ADVIO pose-frame mode injected into the pipeline request."""

    normalize_video_orientation: bool = True
    """Whether the replay should normalize video display orientation when available."""

    telemetry_visible: bool = True
    """Whether stage telemetry should be rendered in the run console."""

    telemetry_view_mode: PipelineTelemetryViewMode = PipelineTelemetryViewMode.LATEST
    """Current stage telemetry presentation mode."""

    telemetry_selected_stage_key: StageKey | None = None
    """Selected stage for rolling telemetry charts."""

    telemetry_selected_metric: PipelineTelemetryMetricId = PipelineTelemetryMetricId.FPS
    """Selected rolling telemetry metric."""

    telemetry_history_run_id: str | None = None
    """Run id that owns the current bounded telemetry history."""

    telemetry_history: list[StageRuntimeStatus] = Field(default_factory=list)
    """Bounded per-session live stage status history."""

    telemetry_max_samples: int = 240
    """Maximum number of live telemetry samples kept in session state."""


class AppState(BaseData):
    """Fully typed app state persisted in Streamlit session storage."""

    record3d: Record3DPageState = Field(default_factory=Record3DPageState)
    """Record3D page selector state."""

    advio: AdvioPageState = Field(default_factory=AdvioPageState)
    """ADVIO page selector state."""

    tum_rgbd: TumRgbdPageState = Field(default_factory=TumRgbdPageState)
    """TUM RGB-D tab selector state."""

    pipeline: PipelinePageState = Field(default_factory=PipelinePageState)
    """Pipeline-page selector state."""

    artifacts: ArtifactInspectorPageState = Field(default_factory=ArtifactInspectorPageState)
    """Artifact inspector page selector state."""

    metrics: MetricsPageState = Field(default_factory=MetricsPageState)
    """Metrics-page selector state."""


__all__ = [
    "AppPageId",
    "AppState",
    "ArtifactInspectorPageState",
    "AdvioPageState",
    "AdvioPreviewSnapshot",
    "MetricsPageState",
    "PipelinePageState",
    "PipelineSourceId",
    "PipelineTelemetryMetricId",
    "PipelineTelemetryViewMode",
    "PreviewStreamState",
    "Record3DPageState",
    "Record3DStreamSnapshot",
    "TumRgbdPageState",
]
