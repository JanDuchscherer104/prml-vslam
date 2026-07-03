"""Runtime spec for dense-cloud evaluation."""

from __future__ import annotations

from prml_vslam.eval.contracts import CloudEstimateKind
from prml_vslam.eval.stage_cloud.contracts import CloudEvaluationEstimateInput, CloudEvaluationStageInput
from prml_vslam.eval.stage_cloud.runtime import CloudEvaluationRuntime
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


class _CloudEvaluationFailureInputFingerprint(BaseData):
    """Typed dense-cloud evaluation input fingerprint payload."""

    reference_cloud: ArtifactRef
    estimates: list[CloudEvaluationEstimateInput]
    cloud_alignment: ArtifactRef | None = None


class _ResolvedReferenceCloud(BaseData):
    """Reference cloud artifact plus target-frame ownership."""

    artifact: ArtifactRef
    target_frame: str = "world"


def _build_offline_input(context: PipelineExecutionContext) -> CloudEvaluationStageInput:
    config = context.run_config.stages.evaluate_cloud
    reference_cloud = _resolve_reference_cloud(context)
    cloud_alignment_result = context.results.require_result(StageKey.CLOUD_ALIGNMENT)
    estimates = _cloud_alignment_estimates(cloud_alignment_result.outcome.artifacts)
    estimates.extend(_optional_reconstruction_estimates(context))
    if not estimates:
        raise StageDependencyError("Cloud evaluation requires at least one Sim3, ICP, or reconstruction point cloud.")
    return CloudEvaluationStageInput(
        artifact_root=context.plan.artifact_root,
        reference_cloud=reference_cloud.artifact,
        estimates=estimates,
        f1_threshold_m=config.f1_threshold_m,
        cloud_alignment=cloud_alignment_result.outcome.artifacts.get("cloud_alignment"),
    )


def _failure_fingerprint(context: PipelineExecutionContext) -> FailureFingerprint:
    input_payload = _build_offline_input(context)
    return FailureFingerprint(
        config_payload=context.run_config.stages.evaluate_cloud,
        input_payload=_CloudEvaluationFailureInputFingerprint(
            reference_cloud=input_payload.reference_cloud,
            estimates=input_payload.estimates,
            cloud_alignment=input_payload.cloud_alignment,
        ),
    )


def _cloud_alignment_estimates(artifacts: dict[str, ArtifactRef]) -> list[CloudEvaluationEstimateInput]:
    estimates: list[CloudEvaluationEstimateInput] = []
    sim3_cloud = artifacts.get("sim3_aligned_point_cloud_ply")
    if sim3_cloud is not None:
        estimates.append(CloudEvaluationEstimateInput(estimate_kind=CloudEstimateKind.SIM3, cloud=sim3_cloud))
    icp_cloud = artifacts.get("icp_aligned_point_cloud_ply")
    if icp_cloud is not None:
        estimates.append(CloudEvaluationEstimateInput(estimate_kind=CloudEstimateKind.SIM3_ICP, cloud=icp_cloud))
    return estimates


def _optional_reconstruction_estimates(context: PipelineExecutionContext) -> list[CloudEvaluationEstimateInput]:
    try:
        reconstruction = context.results.require_payload(StageKey.RECONSTRUCTION, ReconstructionArtifacts)
    except StageDependencyError:
        return []
    return [
        CloudEvaluationEstimateInput(
            estimate_kind=CloudEstimateKind.RECONSTRUCTION,
            cloud=ArtifactRef(path=reconstruction.reference_cloud_path, kind="ply", fingerprint="reconstruction-cloud"),
        )
    ]


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
            "Cloud evaluation requires an aligned source reference cloud or a completed reconstruction reference cloud."
        ) from exc
    return _ResolvedReferenceCloud(
        artifact=ArtifactRef(path=reconstruction.reference_cloud_path, kind="ply", fingerprint="reference-cloud")
    )


CLOUD_EVALUATION_STAGE_SPEC = StageRuntimeSpec(
    stage_key=StageKey.CLOUD_EVALUATION,
    runtime_factory=lambda _context: CloudEvaluationRuntime,
    build_offline_input=_build_offline_input,
    failure_fingerprint=_failure_fingerprint,
)

__all__ = ["CLOUD_EVALUATION_STAGE_SPEC"]
