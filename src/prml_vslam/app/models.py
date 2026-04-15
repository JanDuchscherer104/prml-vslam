"""App-owned models for Streamlit page state, snapshots, and view selections."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from prml_vslam.datasets.advio import AdvioDownloadPreset, AdvioModality, AdvioPoseSource
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.datasets.tum_rgbd import TumRgbdDownloadPreset, TumRgbdModality, TumRgbdPoseSource
from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.contracts.request import BackendSpec
from prml_vslam.utils import BaseData

from .preview_runtime import PacketSessionSnapshot


class AppPageId(StrEnum):
    """Top-level pages exposed by the packaged Streamlit app."""

    RECORD3D = "record3d"
    DATASETS = "datasets"
    PIPELINE = "pipeline"
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

    preview_respect_video_rotation: bool = False
    """Whether the preview should honor video rotation metadata when available."""

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


class PipelineSourceId(StrEnum):
    """Input-source families supported by the bounded pipeline app surface."""

    ADVIO = "advio"
    RECORD3D = "record3d"

    @property
    def label(self) -> str:
        """Return the user-facing source label."""
        return "Record3D" if self is PipelineSourceId.RECORD3D else "ADVIO"


class PipelinePageState(BaseData):
    """Persisted selector state for the interactive Pipeline demo."""

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

    reference_enabled: bool = False
    """Whether the reference-reconstruction stage should be planned."""

    trajectory_eval_enabled: bool = False
    """Whether trajectory evaluation should be planned."""

    evaluate_cloud: bool = False
    """Whether dense-cloud evaluation should be planned."""

    evaluate_efficiency: bool = False
    """Whether efficiency evaluation should be planned."""

    connect_live_viewer: bool = False
    """Whether to connect the Rerun live viewer via gRPC."""

    export_viewer_rrd: bool = False
    """Whether to export the Rerun `.rrd` viewer artifact."""

    record3d_usb_device_index: int = 0
    """Zero-based USB device index used by the bounded pipeline page."""

    record3d_transport: Record3DTransportId = Record3DTransportId.USB
    """Selected Record3D transport used by the bounded pipeline page."""

    record3d_wifi_device_address: str = "192.168.159.24"
    """User-supplied Record3D Wi-Fi preview device address for the pipeline page."""

    record3d_persist_capture: bool = True
    """Whether live Record3D capture should be marked for persistence."""

    pose_source: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH
    """Selected pose source injected into the ADVIO replay packets."""

    respect_video_rotation: bool = False
    """Whether the replay should honor video rotation metadata when available."""


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

    metrics: MetricsPageState = Field(default_factory=MetricsPageState)
    """Metrics-page selector state."""


__all__ = [
    "AppPageId",
    "AppState",
    "AdvioPageState",
    "AdvioPreviewSnapshot",
    "MetricsPageState",
    "PipelinePageState",
    "PipelineSourceId",
    "PreviewStreamState",
    "Record3DPageState",
    "Record3DStreamSnapshot",
    "TumRgbdPageState",
]
