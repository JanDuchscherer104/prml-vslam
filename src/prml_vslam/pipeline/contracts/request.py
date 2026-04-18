"""Pipeline request, source, backend, and placement contracts."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal, TypeAlias

from pydantic import Field

from prml_vslam.benchmark import BenchmarkConfig
from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.interfaces import Record3DTransportId
from prml_vslam.methods.contracts import MethodId, SlamOutputPolicy
from prml_vslam.utils import BaseConfig, PathConfig
from prml_vslam.visualization.contracts import VisualizationConfig

if TYPE_CHECKING:
    from .plan import RunPlan
from .stages import StageKey
from .transport import TransportModel


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

    pose_source: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH
    """Replay pose source used when this dataset source is executed in streaming mode."""

    respect_video_rotation: bool = False
    """Whether ADVIO replay should honor video rotation metadata when available."""


class Record3DLiveSourceSpec(BaseConfig):
    """Typed Record3D live source used by the pipeline app and planner."""

    source_id: Literal["record3d"] = "record3d"
    """Stable live-source identifier for Record3D-backed runs."""

    transport: Record3DTransportId = Record3DTransportId.USB
    """Selected Record3D transport."""

    persist_capture: bool = True
    """Whether to persist the captured session for downstream offline use."""

    device_index: int | None = None
    """Selected USB device index when using the USB transport."""

    device_address: str = ""
    """Entered Wi-Fi preview device address when using the Wi-Fi transport."""


SourceSpec = VideoSourceSpec | DatasetSourceSpec | Record3DLiveSourceSpec


class MockBackendSpec(TransportModel):
    """Executable mock backend configuration."""

    kind: Literal["mock"] = "mock"
    max_frames: int | None = None


class Mast3rBackendSpec(TransportModel):
    """Placeholder MASt3R backend configuration."""

    kind: Literal["mast3r"] = "mast3r"
    max_frames: int | None = None


class VistaBackendSpec(TransportModel):
    """Executable ViSTA backend configuration."""

    kind: Literal["vista"] = "vista"
    max_frames: int | None = None
    vista_slam_dir: Path = Path("external/vista-slam")
    checkpoint_path: Path = Path("external/vista-slam/pretrains/frontend_sta_weights.pth")
    vocab_path: Path = Path("external/vista-slam/pretrains/ORBvoc.txt")
    device: str = "cuda"
    max_view_num: int = 400
    stride: int = 25
    flow_thres: float = 5.0
    keyframe_detection: str = "flow_stride"
    neighbor_edge_num: int = 3
    loop_edge_num: int = 3
    loop_dist_min: int = 40
    loop_nms: int = 40
    loop_cand_thresh_neighbor: int = 5
    point_conf_thres: float = 4.2
    rel_pose_thres: float = 0.75
    pgo_every: int = 500
    random_seed: int = 43


BackendSpec = Annotated[
    MockBackendSpec | Mast3rBackendSpec | VistaBackendSpec,
    Field(discriminator="kind"),
]

BackendConfigValue: TypeAlias = Path | str | int | float | bool | None
BackendConfigPayload: TypeAlias = dict[str, BackendConfigValue]


class StagePlacement(BaseConfig):
    """Repo-owned placement preference for one stage."""

    resources: dict[str, float] = Field(default_factory=dict)


class PlacementPolicy(BaseConfig):
    """Repo-owned placement policy translated by the backend layer only."""

    by_stage: dict[StageKey, StagePlacement] = Field(default_factory=dict)


class SlamStageConfig(BaseConfig):
    """Pipeline-owned SLAM stage request."""

    outputs: SlamOutputPolicy = Field(default_factory=SlamOutputPolicy)
    """Output materialization wishes for the selected backend."""

    backend: BackendSpec
    """Executable backend spec and source of truth for backend selection."""


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

    placement: PlacementPolicy = Field(default_factory=PlacementPolicy)
    """Placement policy translated into backend-specific scheduling controls."""

    def build(self, path_config: PathConfig | None = None) -> RunPlan:
        """Materialize the canonical run plan for this request."""
        from prml_vslam.pipeline.services import RunPlannerService

        return RunPlannerService().build_run_plan(request=self, path_config=path_config)


def build_backend_spec(
    *,
    method: MethodId,
    max_frames: int | None = None,
    overrides: BackendConfigPayload | None = None,
) -> BackendSpec:
    """Build one explicit backend spec from a user-selected method and overrides."""
    payload = {"max_frames": max_frames}
    if overrides is not None:
        payload.update(overrides)
    match method:
        case MethodId.MOCK:
            return MockBackendSpec.model_validate({"kind": "mock", **payload})
        case MethodId.VISTA:
            return VistaBackendSpec.model_validate(
                _normalize_backend_payload(VistaBackendSpec, {"kind": "vista", **payload})
            )
        case MethodId.MAST3R:
            return Mast3rBackendSpec.model_validate({"kind": "mast3r", **payload})


def _normalize_backend_payload(model_type: type[TransportModel], payload: BackendConfigPayload) -> BackendConfigPayload:
    """Coerce strict config payloads back into their declared scalar field types."""
    normalized = dict(payload)
    for field_name, field in model_type.model_fields.items():
        if field_name not in normalized:
            continue
        value = normalized[field_name]
        if isinstance(value, str) and field.annotation is Path:
            normalized[field_name] = Path(value)
    return normalized


__all__ = [
    "BackendSpec",
    "BackendConfigPayload",
    "build_backend_spec",
    "DatasetSourceSpec",
    "Mast3rBackendSpec",
    "MockBackendSpec",
    "PipelineMode",
    "PlacementPolicy",
    "Record3DLiveSourceSpec",
    "RunRequest",
    "SlamStageConfig",
    "SourceSpec",
    "StagePlacement",
    "VideoSourceSpec",
    "VistaBackendSpec",
]
