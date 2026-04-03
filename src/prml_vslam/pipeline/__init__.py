"""Pipeline orchestration."""

from __future__ import annotations

from importlib import import_module

_CONTRACT_EXPORTS = """
ArtifactRef BenchmarkEvaluationConfig CloudEvaluationConfig CloudMetrics DatasetSourceSpec DenseArtifacts
DenseConfig EfficiencyEvaluationConfig EfficiencyMetrics FramePacket LiveSourceSpec PipelineMode
ReferenceArtifacts ReferenceConfig RunPlan RunPlanStage RunPlanStageId RunRequest RunSummary
SequenceManifest StageExecutionStatus StageManifest TrackingArtifacts TrackingConfig TrajectoryEvaluationConfig
TrajectoryMetrics VideoSourceSpec
""".split()
_INTERFACE_EXPORTS = """
CloudEvaluator DenseBackend OfflineTrackerBackend ReferenceBuilder StreamingTrackerBackend TrackingUpdate
TrajectoryEvaluator
""".split()
_WORKSPACE_EXPORTS = "CaptureManifest FrameSample PreparedInput".split()
_EXPORT_MODULES = (
    {name: "contracts" for name in _CONTRACT_EXPORTS}
    | {name: "interfaces" for name in _INTERFACE_EXPORTS}
    | {name: "workspace" for name in _WORKSPACE_EXPORTS}
)

__all__ = [*_CONTRACT_EXPORTS, *_INTERFACE_EXPORTS, *_WORKSPACE_EXPORTS]


def __getattr__(name: str) -> object:
    """Load exported pipeline symbols lazily to avoid package import cycles."""
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(f".{module_name}", __name__), name)
