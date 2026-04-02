"""Pipeline orchestration."""

from __future__ import annotations

_CONTRACT_EXPORTS = {
    "ArtifactRef",
    "BenchmarkEvaluationConfig",
    "CloudMetrics",
    "DatasetSourceSpec",
    "DenseArtifacts",
    "DenseConfig",
    "EfficiencyMetrics",
    "FramePacket",
    "LiveSourceSpec",
    "PipelineMode",
    "ReferenceArtifacts",
    "ReferenceConfig",
    "RunPlan",
    "RunPlanStage",
    "RunPlanStageId",
    "RunRequest",
    "RunSummary",
    "SequenceManifest",
    "StageExecutionStatus",
    "StageManifest",
    "TrackingArtifacts",
    "TrackingConfig",
    "TrajectoryMetrics",
    "VideoSourceSpec",
}

_INTERFACE_EXPORTS = {
    "CloudEvaluator",
    "DenseBackend",
    "OfflineTrackerBackend",
    "ReferenceBuilder",
    "StreamingTrackerBackend",
    "TrackingUpdate",
    "TrajectoryEvaluator",
}

_WORKSPACE_EXPORTS = {
    "CaptureManifest",
    "FrameSample",
    "PreparedInput",
}

__all__ = [
    "ArtifactRef",
    "BenchmarkEvaluationConfig",
    "CaptureManifest",
    "CloudEvaluator",
    "CloudMetrics",
    "DatasetSourceSpec",
    "DenseArtifacts",
    "DenseBackend",
    "DenseConfig",
    "EfficiencyMetrics",
    "FramePacket",
    "FrameSample",
    "LiveSourceSpec",
    "OfflineTrackerBackend",
    "PipelineMode",
    "PipelinePlannerService",
    "PreparedInput",
    "ReferenceArtifacts",
    "ReferenceBuilder",
    "ReferenceConfig",
    "RunPlan",
    "RunPlanStage",
    "RunPlanStageId",
    "RunRequest",
    "RunSummary",
    "SequenceManifest",
    "StageExecutionStatus",
    "StageManifest",
    "StreamingTrackerBackend",
    "TrackingArtifacts",
    "TrackingConfig",
    "TrackingUpdate",
    "TrajectoryEvaluator",
    "TrajectoryMetrics",
    "VideoSourceSpec",
]


def __getattr__(name: str) -> object:
    """Lazily re-export pipeline symbols without introducing import cycles."""
    if name in _CONTRACT_EXPORTS:
        from . import contracts

        return getattr(contracts, name)
    if name in _INTERFACE_EXPORTS:
        from . import interfaces

        return getattr(interfaces, name)
    if name in _WORKSPACE_EXPORTS:
        from . import workspace

        return getattr(workspace, name)
    if name == "PipelinePlannerService":
        from .services import PipelinePlannerService

        return PipelinePlannerService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
