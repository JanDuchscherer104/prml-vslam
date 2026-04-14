"""Legacy compatibility re-exports for the canonical pipeline contracts package."""

from .contracts.artifacts import ArtifactRef, SlamArtifacts
from .contracts.plan import RunPlan, RunPlanStage, RunPlanStageId
from .contracts.request import (
    DatasetSourceSpec,
    LiveTransportId,
    PipelineMode,
    Record3DLiveSourceSpec,
    RunRequest,
    SlamStageConfig,
    SourceSpec,
    VideoSourceSpec,
)
from .contracts.sequence import SequenceManifest

__all__ = [
    "ArtifactRef",
    "DatasetSourceSpec",
    "LiveTransportId",
    "PipelineMode",
    "Record3DLiveSourceSpec",
    "RunPlan",
    "RunPlanStage",
    "RunPlanStageId",
    "RunRequest",
    "SequenceManifest",
    "SlamArtifacts",
    "SlamStageConfig",
    "SourceSpec",
    "VideoSourceSpec",
]
