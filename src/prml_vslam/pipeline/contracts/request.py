"""Pipeline request and source contracts."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import Field, model_validator

from prml_vslam.benchmark import BenchmarkConfig
from prml_vslam.datasets.contracts import DatasetId, FrameSelectionConfig
from prml_vslam.methods.contracts import MethodId, SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.vista.config import VistaSlamBackendConfig
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
        return "Wi-Fi Preview" if self is LiveTransportId.WIFI else self.value.upper()


class StageExecutionMode(StrEnum):
    """Where one pipeline execution component should run."""

    LOCAL = "local"
    PROCESS = "process"


class StreamingExecutionConfig(BaseConfig):
    """Execution placement policy for streaming mode."""

    ingest: StageExecutionMode = StageExecutionMode.LOCAL
    packet_source: StageExecutionMode = StageExecutionMode.LOCAL
    slam: StageExecutionMode = StageExecutionMode.LOCAL
    trajectory_evaluation: StageExecutionMode = StageExecutionMode.LOCAL
    summary: StageExecutionMode = StageExecutionMode.LOCAL


class PipelineExecutionConfig(BaseConfig):
    """Run-level execution placement policy."""

    streaming: StreamingExecutionConfig = Field(default_factory=StreamingExecutionConfig)


class VideoSourceSpec(FrameSelectionConfig):
    """Video-backed source used for offline planning and execution."""

    video_path: Path


class DatasetSourceSpec(FrameSelectionConfig):
    """Dataset-backed source used for offline planning and execution."""

    dataset_id: DatasetId
    sequence_id: str


class Record3DLiveSourceSpec(BaseConfig):
    """Typed Record3D live source used by the pipeline app and planner."""

    source_id: Literal["record3d"] = "record3d"
    transport: LiveTransportId = LiveTransportId.USB
    persist_capture: bool = True
    device_index: int | None = None
    device_address: str = ""


SourceSpec = VideoSourceSpec | DatasetSourceSpec | Record3DLiveSourceSpec
BackendConfig = SlamBackendConfig | VistaSlamBackendConfig


class SlamStageConfig(BaseConfig):
    """Pipeline-owned SLAM stage request."""

    method: MethodId
    outputs: SlamOutputPolicy = Field(default_factory=SlamOutputPolicy)
    backend: BackendConfig = Field(default_factory=SlamBackendConfig)

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
        elif isinstance(backend, VistaSlamBackendConfig):
            payload["backend"] = SlamBackendConfig.model_validate({"max_frames": backend.max_frames})
        else:
            payload["backend"] = SlamBackendConfig.model_validate(backend_payload)
        return payload

    @model_validator(mode="after")
    def _normalize_backend_default(self) -> SlamStageConfig:
        if self.method is MethodId.VISTA and not isinstance(self.backend, VistaSlamBackendConfig):
            self.backend = VistaSlamBackendConfig.model_validate(self.backend.model_dump(mode="python"))
        if self.method is not MethodId.VISTA and isinstance(self.backend, VistaSlamBackendConfig):
            self.backend = SlamBackendConfig.model_validate({"max_frames": self.backend.max_frames})
        return self


class RunRequest(BaseConfig):
    """Config-defined entry contract for one pipeline run."""

    experiment_name: str
    mode: PipelineMode = PipelineMode.OFFLINE
    output_dir: Path
    source: SourceSpec
    slam: SlamStageConfig
    benchmark: BenchmarkConfig = Field(default_factory=BenchmarkConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)
    execution: PipelineExecutionConfig = Field(default_factory=PipelineExecutionConfig)

    def build(self, path_config: PathConfig | None = None) -> RunPlan:
        from prml_vslam.pipeline.services import RunPlannerService

        return RunPlannerService().build_run_plan(request=self, path_config=path_config)


__all__ = [
    "BackendConfig",
    "DatasetSourceSpec",
    "LiveTransportId",
    "PipelineExecutionConfig",
    "PipelineMode",
    "Record3DLiveSourceSpec",
    "RunRequest",
    "SlamStageConfig",
    "SourceSpec",
    "StageExecutionMode",
    "StreamingExecutionConfig",
    "VideoSourceSpec",
]
