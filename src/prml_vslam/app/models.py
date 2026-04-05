"""App-owned models for Streamlit page state and view selections."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from prml_vslam.datasets.advio import AdvioDownloadPreset, AdvioModality, AdvioPoseSource
from prml_vslam.datasets.interfaces import DatasetId
from prml_vslam.eval.interfaces import EvaluationControls
from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.methods import MethodId
from prml_vslam.pipeline.contracts import PipelineMode
from prml_vslam.utils import BaseData


class AppPageId(StrEnum):
    """Top-level pages exposed by the packaged Streamlit app."""

    RECORD3D = "record3d"
    ADVIO = "advio"
    PIPELINE = "pipeline"
    METRICS = "metrics"

    @property
    def label(self) -> str:
        """Return the user-facing page label."""
        return {
            AppPageId.RECORD3D: "Record3D",
            AppPageId.ADVIO: "ADVIO",
            AppPageId.PIPELINE: "Pipeline",
            AppPageId.METRICS: "Metrics",
        }[self]


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


class MetricsPageState(BaseData):
    """Persisted selector state for the metrics page."""

    dataset: DatasetId = DatasetId.ADVIO
    """Selected dataset."""

    sequence_slug: str | None = None
    """Selected dataset sequence, for example `advio-15`."""

    run_root: Path | None = None
    """Selected artifact root for one evaluated run."""

    evaluation: EvaluationControls = Field(default_factory=EvaluationControls)
    """Reserved placeholder for future explicit evaluation options."""

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


class PipelinePageState(BaseData):
    """Persisted selector state for the interactive Pipeline demo."""

    sequence_id: int | None = None
    """Selected ADVIO sequence shown in the demo runner."""

    mode: PipelineMode = PipelineMode.OFFLINE
    """Whether the demo should run one pass or keep looping."""

    method: MethodId = MethodId.VISTA
    """Selected mock tracking backend label."""

    pose_source: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH
    """Selected pose source injected into the ADVIO replay packets."""

    respect_video_rotation: bool = False
    """Whether the replay should honor video rotation metadata when available."""

    is_running: bool = False
    """Whether the current browser session expects a pipeline demo to be active."""


class AppState(BaseData):
    """Fully typed app state persisted in Streamlit session storage."""

    record3d: Record3DPageState = Field(default_factory=Record3DPageState)
    """Record3D page selector state."""

    advio: AdvioPageState = Field(default_factory=AdvioPageState)
    """ADVIO page selector state."""

    pipeline: PipelinePageState = Field(default_factory=PipelinePageState)
    """Pipeline-page selector state."""

    metrics: MetricsPageState = Field(default_factory=MetricsPageState)
    """Metrics-page selector state."""


__all__ = [
    "AppPageId",
    "AppState",
    "AdvioPageState",
    "MetricsPageState",
    "PipelinePageState",
    "Record3DPageState",
]
