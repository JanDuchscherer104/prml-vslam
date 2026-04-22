"""Bounded stage helpers executed under coordinator control.

These helpers implement stage bodies that do not need their own long-lived
actor. They convert normalized inputs into typed stage results and artifact
maps, leaving stage ordering and event recording to the coordinator and
:class:`RuntimeStageProgram`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import ray

from prml_vslam.alignment import GroundAlignmentService
from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.methods.descriptors import BackendDescriptor
from prml_vslam.pipeline.contracts.events import StageOutcome, StageStatus
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.provenance import RunSummary
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import stable_hash, write_json
from prml_vslam.pipeline.ingest import materialize_offline_manifest
from prml_vslam.pipeline.placement import actor_options_for_stage
from prml_vslam.pipeline.ray_runtime.common import (
    artifact_ref,
    clean_actor_options,
)
from prml_vslam.pipeline.ray_runtime.stage_actors import OfflineSlamStageActor
from prml_vslam.pipeline.stages.ground_alignment import GroundAlignmentRuntime, GroundAlignmentRuntimeInput
from prml_vslam.pipeline.stages.reconstruction import ReconstructionRuntime, ReconstructionRuntimeInput
from prml_vslam.pipeline.stages.summary import SummaryRuntime, SummaryRuntimeInput
from prml_vslam.pipeline.stages.trajectory_eval import (
    TrajectoryEvaluationRuntime,
    TrajectoryEvaluationRuntimeInput,
)
from prml_vslam.protocols.source import BenchmarkInputSource, OfflineSequenceSource
from prml_vslam.reconstruction import ReconstructionArtifacts
from prml_vslam.utils import PathConfig, RunArtifactPaths

if TYPE_CHECKING:
    from prml_vslam.pipeline.ray_runtime.stage_program import StageCompletionPayload


@dataclass(frozen=True, slots=True)
class StageExecutionContext:
    """Immutable run-scoped execution context shared by bounded stage helpers.

    Attributes:
        request: Original run request.
        plan: Compiled deterministic run plan.
        path_config: Repo path configuration used for runtime resolution.
        run_paths: Canonical artifact layout for the run.
        backend_descriptor: Capability and resource metadata for the selected
            backend.
    """

    request: RunRequest
    plan: RunPlan
    path_config: PathConfig
    run_paths: RunArtifactPaths
    backend_descriptor: BackendDescriptor


def run_ingest_stage(*, context: StageExecutionContext, source: OfflineSequenceSource) -> StageCompletionPayload:
    """Materialize the canonical ingest boundary from one offline source.

    The helper persists the normalized :class:`SequenceManifest` and any
    prepared benchmark-side inputs before returning the ingest stage outcome.
    """
    from prml_vslam.pipeline.ray_runtime.stage_program import StageCompletionPayload

    prepared_manifest = source.prepare_sequence_manifest(context.run_paths.sequence_manifest_path.parent)
    benchmark_inputs = None
    if isinstance(source, BenchmarkInputSource):
        benchmark_inputs = source.prepare_benchmark_inputs(context.run_paths.benchmark_inputs_path.parent)
        if benchmark_inputs is not None:
            write_json(context.run_paths.benchmark_inputs_path, benchmark_inputs)
    sequence_manifest = materialize_offline_manifest(
        request=context.request,
        prepared_manifest=prepared_manifest,
        run_paths=context.run_paths,
    )
    write_json(context.run_paths.sequence_manifest_path, sequence_manifest)
    artifacts = {
        "sequence_manifest": artifact_ref(context.run_paths.sequence_manifest_path, kind="json"),
    }
    if sequence_manifest.rgb_dir is not None:
        artifacts["rgb_dir"] = artifact_ref(sequence_manifest.rgb_dir, kind="dir")
    if sequence_manifest.timestamps_path is not None:
        artifacts["timestamps"] = artifact_ref(sequence_manifest.timestamps_path, kind="json")
    if sequence_manifest.intrinsics_path is not None:
        artifacts["intrinsics"] = artifact_ref(sequence_manifest.intrinsics_path, kind="yaml")
    if sequence_manifest.rotation_metadata_path is not None:
        artifacts["rotation_metadata"] = artifact_ref(sequence_manifest.rotation_metadata_path, kind="json")
    if benchmark_inputs is not None:
        artifacts["benchmark_inputs"] = artifact_ref(context.run_paths.benchmark_inputs_path, kind="json")
        for reference in benchmark_inputs.reference_trajectories:
            artifacts[f"reference_tum:{reference.source.value}"] = artifact_ref(reference.path, kind="tum")
    return StageCompletionPayload(
        outcome=StageOutcome(
            stage_key=StageKey.INGEST,
            status=StageStatus.COMPLETED,
            config_hash=stable_hash(context.request.source),
            input_fingerprint=stable_hash(context.request.source),
            artifacts=artifacts,
        ),
        sequence_manifest=sequence_manifest,
        benchmark_inputs=benchmark_inputs,
    )


def run_offline_slam_stage(
    *,
    context: StageExecutionContext,
    sequence_manifest: SequenceManifest,
    benchmark_inputs: PreparedBenchmarkInputs | None,
) -> StageCompletionPayload:
    """Execute offline SLAM through the dedicated stage actor boundary."""
    actor = OfflineSlamStageActor.options(
        **clean_actor_options(
            actor_options_for_stage(
                stage_key=StageKey.SLAM,
                request=context.request,
                backend=context.backend_descriptor,
                default_num_cpus=2.0,
                default_num_gpus=1.0,
            )
        )
    ).remote()
    return ray.get(
        actor.run.remote(
            request=context.request,
            plan=context.plan,
            sequence_manifest=sequence_manifest,
            benchmark_inputs=benchmark_inputs,
            path_config=context.path_config,
        )
    )


def run_trajectory_evaluation_stage(
    *,
    context: StageExecutionContext,
    sequence_manifest: SequenceManifest,
    benchmark_inputs: PreparedBenchmarkInputs | None,
    slam: SlamArtifacts,
) -> StageCompletionPayload:
    """Evaluate the normalized SLAM trajectory against prepared references."""
    # TODO(pipeline-refactor/WP-10): Delete this migration wrapper when
    # RuntimeStageProgram no longer consumes StageCompletionPayload.
    from prml_vslam.pipeline.ray_runtime.stage_program import StageCompletionPayload

    result = TrajectoryEvaluationRuntime().run_offline(
        TrajectoryEvaluationRuntimeInput(
            request=context.request,
            plan=context.plan,
            sequence_manifest=sequence_manifest,
            benchmark_inputs=benchmark_inputs,
            slam=slam,
        )
    )
    return StageCompletionPayload(outcome=result.outcome)


def run_ground_alignment_stage(
    *,
    context: StageExecutionContext,
    slam: SlamArtifacts,
) -> StageCompletionPayload:
    """Detect one dominant ground plane and persist derived alignment metadata."""
    # TODO(pipeline-refactor/WP-10): Delete this migration wrapper when
    # RuntimeStageProgram no longer consumes StageCompletionPayload.
    from prml_vslam.pipeline.ray_runtime.stage_program import StageCompletionPayload

    result = GroundAlignmentRuntime(service_type=GroundAlignmentService).run_offline(
        GroundAlignmentRuntimeInput(
            request=context.request,
            run_paths=context.run_paths,
            slam=slam,
        )
    )
    metadata = result.payload
    if not isinstance(metadata, GroundAlignmentMetadata):
        raise RuntimeError("GroundAlignmentRuntime returned an invalid ground-alignment payload.")
    return StageCompletionPayload(
        outcome=result.outcome,
        ground_alignment=metadata,
    )


def run_reference_reconstruction_stage(
    *,
    context: StageExecutionContext,
    benchmark_inputs: PreparedBenchmarkInputs | None,
) -> StageCompletionPayload:
    """Build a reference reconstruction from prepared RGB-D observations."""
    # TODO(pipeline-refactor/WP-10): Delete this migration wrapper when
    # RuntimeStageProgram no longer consumes StageCompletionPayload.
    from prml_vslam.pipeline.ray_runtime.stage_program import StageCompletionPayload

    result = ReconstructionRuntime().run_offline(
        ReconstructionRuntimeInput(
            request=context.request,
            run_paths=context.run_paths,
            benchmark_inputs=benchmark_inputs,
        )
    )
    if not isinstance(result.payload, ReconstructionArtifacts):
        raise RuntimeError("ReconstructionRuntime returned an invalid reconstruction payload.")
    return StageCompletionPayload(outcome=result.outcome)


def run_summary_stage(
    *,
    context: StageExecutionContext,
    stage_outcomes: list[StageOutcome],
) -> StageCompletionPayload:
    """Project durable run summary artifacts from terminal stage outcomes."""
    # TODO(pipeline-refactor/WP-10): Delete this migration wrapper when
    # RuntimeStageProgram no longer consumes StageCompletionPayload.
    from prml_vslam.pipeline.ray_runtime.stage_program import StageCompletionPayload

    runtime = SummaryRuntime()
    result = runtime.run_offline(
        SummaryRuntimeInput(
            request=context.request,
            plan=context.plan,
            run_paths=context.run_paths,
            stage_outcomes=stage_outcomes,
        )
    )
    summary = result.payload
    if not isinstance(summary, RunSummary):
        raise RuntimeError("SummaryRuntime returned an invalid summary payload.")
    return StageCompletionPayload(
        outcome=result.outcome,
        summary=summary,
        stage_manifests=runtime.stage_manifests,
    )


__all__ = [
    "StageExecutionContext",
    "run_ground_alignment_stage",
    "run_ingest_stage",
    "run_offline_slam_stage",
    "run_reference_reconstruction_stage",
    "run_summary_stage",
    "run_trajectory_evaluation_stage",
]
