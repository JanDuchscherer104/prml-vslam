"""Pipeline request and source contracts."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import Field, model_validator

from prml_vslam.benchmark import BenchmarkConfig
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.methods.contracts import MethodId, SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.vista.config import VistaSlamBackendConfig
from prml_vslam.methods.mast3r.config import Mast3rSlamBackendConfig
from prml_vslam.utils import BaseConfig, PathConfig
from prml_vslam.visualization.contracts import VisualizationConfig

if TYPE_CHECKING:
    from .plan import RunPlan


class PipelineMode(StrEnum):
    """Supported pipeline operating modes."""

    OFFLINE = "offline"
    STREAMING = "streaming"

    @property
    def label(self) -> str:
        """Return the human-readable mode label."""
        return {
            self.OFFLINE: "Offline (batch)",
            self.STREAMING: "Streaming (incremental)",
        }[self]


class LiveTransportId(StrEnum):
    """Pipeline-owned transport selector for Record3D live sources."""

    USB = "usb"
    WIFI = "wifi"

    @property
    def label(self) -> str:
        """Return the user-facing transport label."""
        return "Wi-Fi Preview" if self is LiveTransportId.WIFI else self.value.upper()


class StageExecutionMode(StrEnum):
    """Where one pipeline execution component should run."""

    LOCAL = "local"
    PROCESS = "process"


class StreamingExecutionConfig(BaseConfig):
    """Execution placement policy for streaming mode."""

    ingest: StageExecutionMode = StageExecutionMode.LOCAL
    """Execution mode for source manifest and benchmark input preparation."""

    packet_source: StageExecutionMode = StageExecutionMode.LOCAL
    """Execution mode for packet-source consumption."""

    slam: StageExecutionMode = StageExecutionMode.LOCAL
    """Execution mode for streaming SLAM session execution."""

    trajectory_evaluation: StageExecutionMode = StageExecutionMode.LOCAL
    """Execution mode for optional trajectory evaluation."""

    summary: StageExecutionMode = StageExecutionMode.LOCAL
    """Execution mode for final summary and manifest persistence."""


class PipelineExecutionConfig(BaseConfig):
    """Run-level execution placement policy."""

    streaming: StreamingExecutionConfig = Field(default_factory=StreamingExecutionConfig)
    """Streaming-mode execution policy."""


class VideoSourceSpec(BaseConfig):
    """Video-backed source used for offline planning and execution."""

    video_path: Path
    """Path to the input video that will be processed."""

    frame_stride: int = 1
    """Frame subsampling stride applied during canonical ingest."""


class DatasetSourceSpec(BaseConfig):
    """Dataset-backed source used for offline planning and execution."""

    dataset_id: DatasetId
    """Dataset family that owns the sequence."""

    sequence_id: str
    """Dataset-specific sequence identifier."""


class Record3DLiveSourceSpec(BaseConfig):
    """Typed Record3D live source used by the pipeline app and planner."""

    source_id: Literal["record3d"] = "record3d"
    """Stable live-source identifier for Record3D-backed runs."""

    transport: LiveTransportId = LiveTransportId.USB
    """Selected Record3D transport."""

    persist_capture: bool = True
    """Whether to persist the captured session for downstream offline use."""

    device_index: int | None = None
    """Selected USB device index when using the USB transport."""

    device_address: str = ""
    """Entered Wi-Fi preview device address when using the Wi-Fi transport."""


SourceSpec = VideoSourceSpec | DatasetSourceSpec | Record3DLiveSourceSpec
BackendConfig = SlamBackendConfig | VistaSlamBackendConfig | Mast3rSlamBackendConfig


class SlamStageConfig(BaseConfig):
    """Pipeline-owned SLAM stage request."""

    method: MethodId
    """External monocular VSLAM backend to use for the run."""

    outputs: SlamOutputPolicy = Field(default_factory=SlamOutputPolicy)
    """Output materialization wishes for the selected backend."""

    backend: BackendConfig = Field(default_factory=SlamBackendConfig)
    """Backend-private runtime or wrapper controls."""

    @model_validator(mode="before")
    @classmethod
    def _coerce_backend_by_method(cls, raw_data: object) -> object:
        if not isinstance(raw_data, dict):
            return raw_data
        method = raw_data.get("method")
        if method is None:
            return raw_data
        backend = raw_data.get("backend")
        if backend is None:
            return raw_data
        method_id = method if isinstance(method, MethodId) else MethodId(method)
        payload = dict(raw_data)
        backend_payload = backend.model_dump(mode="python") if isinstance(backend, SlamBackendConfig) else backend
        if method_id is MethodId.VISTA:
            payload["backend"] = VistaSlamBackendConfig.model_validate(backend_payload)
        elif method_id is MethodId.MAST3R:
            payload["backend"] = Mast3rSlamBackendConfig.model_validate(backend_payload)
        elif isinstance(backend, VistaSlamBackendConfig):
            payload["backend"] = SlamBackendConfig.model_validate({"max_frames": backend.max_frames})
        else:
            payload["backend"] = SlamBackendConfig.model_validate(backend_payload)
        return payload

    @model_validator(mode="after")
    def _normalize_backend_default(self) -> SlamStageConfig:
        if self.method is MethodId.VISTA and not isinstance(self.backend, VistaSlamBackendConfig):
            self.backend = VistaSlamBackendConfig.model_validate(self.backend.model_dump(mode="python"))
        if self.method is MethodId.MAST3R and not isinstance(self.backend, Mast3rSlamBackendConfig):
            self.backend = Mast3rSlamBackendConfig.model_validate(self.backend.model_dump(mode="python"))
        if self.method not in {MethodId.VISTA, MethodId.MAST3R} and isinstance(
            self.backend, VistaSlamBackendConfig | Mast3rSlamBackendConfig
        ):
            self.backend = SlamBackendConfig.model_validate({"max_frames": self.backend.max_frames})
        return self


class RunRequest(BaseConfig):
    """Config-defined entry contract for one pipeline run."""

    experiment_name: str
    """Human-readable name for the benchmark run."""

    mode: PipelineMode = PipelineMode.OFFLINE
    """Whether the run is offline-only or live-backed."""

    output_dir: Path
    """Root directory where planned artifacts should be written."""

    source: SourceSpec
    """Source specification normalized before the main benchmark stages run."""

    slam: SlamStageConfig
    """SLAM-stage configuration."""

    benchmark: BenchmarkConfig = Field(default_factory=BenchmarkConfig)
    """Benchmark-policy configuration kept outside the pipeline core."""

    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)
    """Viewer-export policy kept outside pipeline execution semantics."""

    execution: PipelineExecutionConfig = Field(default_factory=PipelineExecutionConfig)
    """Execution placement policy for local or process-backed run components."""

    def build(self, path_config: PathConfig | None = None) -> RunPlan:
        """Materialize the canonical run plan for this request."""
        from prml_vslam.pipeline.services import RunPlannerService

        return RunPlannerService().build_run_plan(request=self, path_config=path_config)


__all__ = [
    "DatasetSourceSpec",
    "BackendConfig",
    "LiveTransportId",
    "PipelineMode",
    "Record3DLiveSourceSpec",
    "RunRequest",
    "SlamStageConfig",
    "SourceSpec",
    "StageExecutionMode",
    "StreamingExecutionConfig",
    "PipelineExecutionConfig",
    "VideoSourceSpec",
]
