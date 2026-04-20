"""Bounded stage helpers executed under coordinator control.

These helpers implement stage bodies that do not need their own long-lived
actor. They convert normalized inputs into typed stage results and artifact
maps, leaving stage ordering and event recording to the coordinator and
:class:`RuntimeStageProgram`.
"""

from __future__ import annotations

from dataclasses import dataclass

import ray

from prml_vslam.alignment import GroundAlignmentService
from prml_vslam.benchmark import PreparedBenchmarkInputs
from prml_vslam.eval.services import TrajectoryEvaluationService
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.contracts.events import StageOutcome, StageStatus
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import project_summary, stable_hash, write_json
from prml_vslam.pipeline.ingest import materialize_offline_manifest
from prml_vslam.pipeline.placement import actor_options_for_stage
from prml_vslam.pipeline.ray_runtime.common import (
    GroundAlignmentStageResult,
    IngestStageResult,
    SlamStageResult,
    SummaryStageResult,
    TrajectoryEvaluationStageResult,
    artifact_ref,
    clean_actor_options,
)
from prml_vslam.pipeline.ray_runtime.stage_actors import OfflineSlamStageActor
from prml_vslam.protocols.source import BenchmarkInputSource, OfflineSequenceSource
from prml_vslam.utils import PathConfig, RunArtifactPaths


@dataclass(frozen=True, slots=True)
class StageExecutionContext:
    """Immutable per-run execution envelope shared by bounded stage helpers.

    The context carries the stable inputs that do not change while a run is
    executing: the original request, the compiled plan, path-resolution
    helpers, the canonical artifact layout, and backend metadata. Stage
    implementations read these fields when they need run-scoped configuration
    or filesystem locations, while mutable cross-stage outputs live separately
    in :class:`RuntimeExecutionState`.

    Attributes:
        request: Original run request and policy surface for the run.
        plan: Compiled deterministic run plan that owns stage order and the
            artifact root.
        path_config: Repo path configuration used for runtime resolution.
        run_paths: Canonical artifact layout for the run.
    """

    request: RunRequest
    plan: RunPlan
    path_config: PathConfig
    run_paths: RunArtifactPaths


#  TODO: I feel like this kind of multiplexing should be handeled similar
def run_ingest_stage(*, context: StageExecutionContext, source: OfflineSequenceSource) -> IngestStageResult:
    """Materialize the canonical ingest boundary from one offline source.

    The helper persists the normalized :class:`SequenceManifest` and any
    prepared benchmark-side inputs before returning the ingest stage outcome.
    """
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
    return IngestStageResult(
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
) -> SlamStageResult:
    """Execute offline SLAM through the dedicated stage actor boundary."""
    actor = OfflineSlamStageActor.options(
        **clean_actor_options(
            actor_options_for_stage(
                stage_key=StageKey.SLAM,
                request=context.request,
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
) -> TrajectoryEvaluationStageResult:
    """Evaluate the normalized SLAM trajectory against prepared references."""
    artifact = TrajectoryEvaluationService(
        PathConfig(artifacts_dir=context.request.output_dir)
    ).compute_pipeline_evaluation(
        request=context.request,
        plan=context.plan,
        sequence_manifest=sequence_manifest,
        benchmark_inputs=benchmark_inputs,
        slam=slam,
    )
    artifacts: dict[str, ArtifactRef] = {}
    if artifact is not None:
        artifacts = {
            "trajectory_metrics": artifact_ref(artifact.path, kind="json"),
            "reference_tum": artifact_ref(artifact.reference_path, kind="tum"),
            "estimate_tum": artifact_ref(artifact.estimate_path, kind="tum"),
        }
    return TrajectoryEvaluationStageResult(
        outcome=StageOutcome(
            stage_key=StageKey.TRAJECTORY_EVALUATION,
            status=StageStatus.COMPLETED,
            config_hash=stable_hash(context.request.benchmark.trajectory),
            input_fingerprint=stable_hash(
                {
                    "benchmark_inputs": benchmark_inputs,
                    "slam_trajectory": slam.trajectory_tum,
                }
            ),
            artifacts=artifacts,
        )
    )


def run_ground_alignment_stage(
    *,
    context: StageExecutionContext,
    slam: SlamArtifacts,
) -> GroundAlignmentStageResult:
    """Detect one dominant ground plane and persist derived alignment metadata."""
    metadata = GroundAlignmentService(config=context.request.alignment.ground).estimate_from_slam_artifacts(slam=slam)
    write_json(context.run_paths.ground_alignment_path, metadata)
    return GroundAlignmentStageResult(
        outcome=StageOutcome(
            stage_key=StageKey.GROUND_ALIGNMENT,
            status=StageStatus.COMPLETED if metadata.applied else StageStatus.SKIPPED,
            config_hash=stable_hash(context.request.alignment.ground),
            input_fingerprint=stable_hash(
                {
                    "trajectory_tum": slam.trajectory_tum,
                    "dense_points_ply": slam.dense_points_ply,
                    "sparse_points_ply": slam.sparse_points_ply,
                }
            ),
            artifacts={"ground_alignment": artifact_ref(context.run_paths.ground_alignment_path, kind="json")},
            metrics={
                "confidence": metadata.confidence,
                "candidate_count": metadata.candidate_count,
            },
        ),
        ground_alignment=metadata,
    )


def run_summary_stage(
    *,
    context: StageExecutionContext,
    stage_outcomes: list[StageOutcome],
) -> SummaryStageResult:
    """Project durable run summary artifacts from terminal stage outcomes."""
    summary, stage_manifests, outcome = project_summary(
        request=context.request,
        plan=context.plan,
        run_paths=context.run_paths,
        stage_outcomes=stage_outcomes,
    )
    return SummaryStageResult(
        outcome=outcome,
        summary=summary,
        stage_manifests=stage_manifests,
    )


__all__ = [
    "StageExecutionContext",
    "run_ground_alignment_stage",
    "run_ingest_stage",
    "run_offline_slam_stage",
    "run_summary_stage",
    "run_trajectory_evaluation_stage",
]
