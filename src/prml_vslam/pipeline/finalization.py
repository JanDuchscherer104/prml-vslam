"""Pure helpers for evaluation, hashing, and summary projection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from prml_vslam.benchmark import PreparedBenchmarkInputs
from prml_vslam.eval.contracts import DiscoveredRun, EvaluationArtifact, SelectionSnapshot
from prml_vslam.eval.services import TrajectoryEvaluationService
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.contracts.events import StageOutcome, StageStatus
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.provenance import RunSummary, StageManifest
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.utils import BaseConfig, PathConfig, RunArtifactPaths


def stage_manifest_from_outcome(outcome: StageOutcome) -> StageManifest:
    """Convert one stage outcome into its persisted manifest."""
    return StageManifest(
        stage_id=outcome.stage_key,
        config_hash=outcome.config_hash,
        input_fingerprint=outcome.input_fingerprint,
        output_paths={name: artifact.path for name, artifact in outcome.artifacts.items()},
        status=outcome.status,
    )


def project_summary(
    *,
    request: RunRequest,
    plan: RunPlan,
    run_paths: RunArtifactPaths,
    stage_outcomes: list[StageOutcome],
) -> tuple[RunSummary, list[StageManifest], StageOutcome]:
    """Project run summary and stage manifests from executed stage outcomes."""
    stage_manifests = [stage_manifest_from_outcome(outcome) for outcome in stage_outcomes]
    summary = RunSummary(
        run_id=plan.run_id,
        artifact_root=plan.artifact_root,
        stage_status={manifest.stage_id: manifest.status for manifest in stage_manifests},
    )
    write_json(run_paths.summary_path, summary)
    write_json(run_paths.stage_manifests_path, stage_manifests)
    summary_outcome = StageOutcome(
        stage_key=StageKey.SUMMARY,
        status=StageStatus.COMPLETED,
        config_hash=stable_hash({"experiment_name": request.experiment_name, "mode": request.mode.value}),
        input_fingerprint=stable_hash(stage_outcomes),
        artifacts={
            "run_summary": ArtifactRef(
                path=run_paths.summary_path,
                kind="json",
                fingerprint=stable_hash(summary),
            ),
            "stage_manifests": ArtifactRef(
                path=run_paths.stage_manifests_path,
                kind="json",
                fingerprint=stable_hash(stage_manifests),
            ),
        },
        metrics={"stage_count": len(stage_outcomes)},
    )
    return summary, stage_manifests, summary_outcome


def stable_hash(payload: object) -> str:
    """Compute a stable SHA-256 hash for repo-owned JSON-friendly payloads."""
    normalized_payload = BaseConfig.to_jsonable(payload)
    encoded = json.dumps(normalized_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_json(path: Path, payload: object) -> None:
    """Persist one JSON artifact with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(BaseConfig.to_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


def compute_trajectory_evaluation(
    *,
    request: RunRequest,
    plan: RunPlan,
    sequence_manifest: SequenceManifest | None,
    benchmark_inputs: PreparedBenchmarkInputs | None,
    slam: SlamArtifacts | None,
) -> EvaluationArtifact | None:
    """Compute trajectory evaluation for one completed run when enabled."""
    if not request.benchmark.trajectory.enabled:
        return None
    if sequence_manifest is None or benchmark_inputs is None or slam is None:
        raise RuntimeError("Trajectory evaluation requires a sequence manifest, benchmark inputs, and SLAM artifacts.")
    reference = benchmark_inputs.trajectory_for_source(request.benchmark.trajectory.baseline_source)
    if reference is None:
        raise RuntimeError(
            "Prepared benchmark inputs do not include the requested trajectory baseline "
            f"'{request.benchmark.trajectory.baseline_source.value}'."
        )
    evaluator = TrajectoryEvaluationService(PathConfig(artifacts_dir=request.output_dir))
    selection = SelectionSnapshot(
        sequence_slug=sequence_manifest.sequence_id,
        reference_path=reference.path,
        run=DiscoveredRun(
            artifact_root=plan.artifact_root,
            estimate_path=slam.trajectory_tum.path,
            method=plan.method,
            label=plan.method.display_name,
        ),
    )
    return evaluator.compute_evaluation(selection=selection)


__all__ = [
    "compute_trajectory_evaluation",
    "project_summary",
    "stage_manifest_from_outcome",
    "stable_hash",
    "write_json",
]
