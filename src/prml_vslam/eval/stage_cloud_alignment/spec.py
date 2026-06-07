"""Runtime spec for the offline point-cloud alignment stage."""

from __future__ import annotations

from prml_vslam.eval.stage_cloud_alignment.contracts import CloudAlignmentStageInput
from prml_vslam.eval.stage_cloud_alignment.runtime import CloudAlignmentRuntime
from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.pipeline.contracts.context import PipelineExecutionContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.runner import StageDependencyError
from prml_vslam.pipeline.stages.base.config import FailureFingerprint
from prml_vslam.pipeline.stages.base.spec import StageRuntimeSpec
from prml_vslam.reconstruction import ReconstructionArtifacts
from prml_vslam.sources.contracts import ReferenceCloudCoordinateStatus
from prml_vslam.sources.stage.artifacts import reference_cloud_artifact_key
from prml_vslam.utils import BaseData


class _CloudAlignmentFailureInputFingerprint(BaseData):
    """Typed cloud-alignment input fingerprint payload."""

    reference_cloud: ArtifactRef
    sim3_point_cloud: ArtifactRef | None = None
    target_frame: str = "world"


class _ResolvedReferenceCloud(BaseData):
    """Reference cloud artifact plus its benchmark target frame."""

    artifact: ArtifactRef
    target_frame: str = "world"


def _build_offline_input(context: PipelineExecutionContext) -> CloudAlignmentStageInput:
    config = context.run_config.stages.align_cloud
    reference_cloud = _resolve_reference_cloud(context)
    trajectory_alignment = context.results.require_result(StageKey.TRAJECTORY_ALIGNMENT)
    sim3_point_cloud = trajectory_alignment.outcome.artifacts.get("aligned_point_cloud_ply")
    if sim3_point_cloud is None:
        raise StageDependencyError(
            "Cloud alignment requires `align.trajectory` to produce an accepted `aligned_point_cloud_ply`; "
            "check `trajectory_alignment.json` cloud-use diagnostics when the artifact is absent."
        )
    return CloudAlignmentStageInput(
        artifact_root=context.plan.artifact_root,
        reference_cloud=reference_cloud.artifact,
        sim3_point_cloud=sim3_point_cloud,
        target_frame=reference_cloud.target_frame,
        max_correspondence_distance_m=config.max_correspondence_distance_m,
    )


def _failure_fingerprint(context: PipelineExecutionContext) -> FailureFingerprint:
    reference_cloud = _resolve_reference_cloud(context)
    trajectory_alignment = context.results.require_result(StageKey.TRAJECTORY_ALIGNMENT)
    return FailureFingerprint(
        config_payload=context.run_config.stages.align_cloud,
        input_payload=_CloudAlignmentFailureInputFingerprint(
            reference_cloud=reference_cloud.artifact,
            sim3_point_cloud=trajectory_alignment.outcome.artifacts.get("aligned_point_cloud_ply"),
            target_frame=reference_cloud.target_frame,
        ),
    )


def _resolve_reference_cloud(context: PipelineExecutionContext) -> _ResolvedReferenceCloud:
    benchmark_inputs = context.results.require_benchmark_inputs()
    source_result = context.results.require_result(StageKey.SOURCE)
    preferred_source = context.run_config.stages.align_cloud.reference_source
    if benchmark_inputs is not None:
        for reference in benchmark_inputs.reference_clouds:
            if reference.coordinate_status is not ReferenceCloudCoordinateStatus.ALIGNED:
                continue
            if preferred_source is not None and reference.source is not preferred_source:
                continue
            artifact = source_result.outcome.artifacts.get(reference_cloud_artifact_key(reference))
            if artifact is not None:
                return _ResolvedReferenceCloud(artifact=artifact, target_frame=reference.target_frame)

    try:
        reconstruction = context.results.require_payload(StageKey.RECONSTRUCTION, ReconstructionArtifacts)
    except StageDependencyError as exc:
        raise StageDependencyError(
            "Cloud alignment requires an aligned source reference cloud or a completed reconstruction reference cloud."
        ) from exc
    return _ResolvedReferenceCloud(
        artifact=ArtifactRef(path=reconstruction.reference_cloud_path, kind="ply", fingerprint="reference-cloud")
    )


CLOUD_ALIGNMENT_STAGE_SPEC = StageRuntimeSpec(
    stage_key=StageKey.CLOUD_ALIGNMENT,
    runtime_factory=lambda _context: CloudAlignmentRuntime,
    build_offline_input=_build_offline_input,
    failure_fingerprint=_failure_fingerprint,
)

__all__ = ["CLOUD_ALIGNMENT_STAGE_SPEC"]
