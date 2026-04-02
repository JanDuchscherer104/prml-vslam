"""App-owned models for Streamlit page state and view selections."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from prml_vslam.datasets.advio import AdvioDownloadPreset, AdvioModality
from prml_vslam.datasets.interfaces import DatasetId
from prml_vslam.eval.interfaces import EvaluationControls
from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.utils import BaseConfig


class AppPageId(StrEnum):
    """Top-level pages exposed by the packaged Streamlit app."""

    RECORD3D = "record3d"
    ADVIO = "advio"
    METRICS = "metrics"

    @property
    def label(self) -> str:
        """Return the user-facing page label."""
        return {
            AppPageId.RECORD3D: "Record3D",
            AppPageId.ADVIO: "ADVIO",
            AppPageId.METRICS: "Metrics",
        }[self]


class AdvioPageState(BaseConfig):
    """Persisted selector state for the ADVIO dataset-management page."""

    selected_sequence_ids: list[int] = Field(default_factory=list)
    """Explicit scene selection for download actions."""

    download_preset: AdvioDownloadPreset = AdvioDownloadPreset.OFFLINE
    """Selected curated download bundle."""

    selected_modalities: list[AdvioModality] = Field(default_factory=list)
    """Optional explicit modality override."""

    overwrite_existing: bool = False
    """Whether download actions should overwrite local archives and extracted files."""


class MetricsPageState(BaseConfig):
    """Persisted selector state for the metrics page."""

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


class Record3DPageState(BaseConfig):
    """Persisted selector state for the Record3D live-stream page."""

    transport: Record3DTransportId = Record3DTransportId.USB
    """Selected Record3D transport."""

    usb_device_index: int = 0
    """Zero-based USB device index selected in the app."""

    wifi_device_address: str = "192.168.159.24"
    """User-supplied Wi-Fi device address."""

    is_running: bool = False
    """Whether the current browser session expects a live stream to be active."""


class AppState(BaseConfig):
    """Fully typed app state persisted in Streamlit session storage."""

    record3d: Record3DPageState = Field(default_factory=Record3DPageState)
    """Record3D page selector state."""

    advio: AdvioPageState = Field(default_factory=AdvioPageState)
    """ADVIO page selector state."""

    metrics: MetricsPageState = Field(default_factory=MetricsPageState)
    """Metrics-page selector state."""


__all__ = [
    "AppPageId",
    "AppState",
    "AdvioPageState",
    "MetricsPageState",
    "Record3DPageState",
]
