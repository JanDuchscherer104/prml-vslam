"""Load source and SLAM handoff payloads from an existing artifact root."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.interfaces import ObservationSequenceRef
from prml_vslam.interfaces.artifacts import ArtifactRef, artifact_ref
from prml_vslam.methods.contracts import SlamArtifacts
from prml_vslam.methods.stage.contracts import SlamStageOutput
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.ray_runtime.common import slam_artifacts_map
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.sources.contracts import (
    PreparedBenchmarkInputs,
    ReferenceCloudRef,
    ReferenceTrajectoryRef,
    SequenceManifest,
)
from prml_vslam.sources.stage.artifacts import source_artifacts
from prml_vslam.sources.stage.contracts import SourceStageOutput
from prml_vslam.utils import RunArtifactPaths
from prml_vslam.utils.serialization import stable_hash


def load_reused_stage_results(artifact_root: Path) -> list[StageResult]:
    """Return source and SLAM results reconstructed from one artifact root."""
    run_paths = RunArtifactPaths.build(artifact_root)
    return [_load_source_result(run_paths), _load_slam_result(run_paths)]


def _load_source_result(run_paths: RunArtifactPaths) -> StageResult:
    if not run_paths.sequence_manifest_path.exists():
        raise FileNotFoundError(f"Reuse source manifest is missing: {run_paths.sequence_manifest_path}")
    if not run_paths.benchmark_inputs_path.exists():
        raise FileNotFoundError(f"Reuse benchmark inputs are missing: {run_paths.benchmark_inputs_path}")
    output = SourceStageOutput(
        sequence_manifest=_rebase_sequence_manifest(
            SequenceManifest.model_validate_json(run_paths.sequence_manifest_path.read_text(encoding="utf-8")),
            artifact_root=run_paths.artifact_root,
        ),
        benchmark_inputs=_rebase_benchmark_inputs(
            PreparedBenchmarkInputs.model_validate_json(run_paths.benchmark_inputs_path.read_text(encoding="utf-8")),
            artifact_root=run_paths.artifact_root,
        ),
    )
    return StageResult(
        stage_key=StageKey.SOURCE,
        payload=output,
        outcome=_outcome(StageKey.SOURCE, artifacts=source_artifacts(run_paths=run_paths, output=output)),
        final_runtime_status=_status(StageKey.SOURCE, "Reused persisted source artifacts."),
    )


def _load_slam_result(run_paths: RunArtifactPaths) -> StageResult:
    if not run_paths.trajectory_path.exists():
        raise FileNotFoundError(f"Reuse SLAM trajectory is missing: {run_paths.trajectory_path}")
    slam = SlamArtifacts(
        trajectory_tum=artifact_ref(run_paths.trajectory_path, kind="tum"),
        sparse_points_ply=_optional_ply(run_paths.sparse_points_path),
        dense_points_ply=_optional_ply(run_paths.point_cloud_path) or _optional_ply(run_paths.dense_points_path),
        depth_maps_npz=_optional_npz(run_paths.depth_maps_path),
        point_maps_npz=_optional_npz(run_paths.point_maps_path),
        point_cloud_confidences_npz=_optional_npz(run_paths.point_cloud_confidences_path),
    )
    return StageResult(
        stage_key=StageKey.SLAM,
        payload=SlamStageOutput(artifacts=slam),
        outcome=_outcome(StageKey.SLAM, artifacts=slam_artifacts_map(slam)),
        final_runtime_status=_status(StageKey.SLAM, "Reused persisted SLAM artifacts."),
    )


def _optional_ply(path: Path) -> ArtifactRef | None:
    return artifact_ref(path, kind="ply") if path.exists() else None


def _optional_npz(path: Path) -> ArtifactRef | None:
    return artifact_ref(path, kind="npz") if path.exists() else None


def _rebase_sequence_manifest(manifest: SequenceManifest, *, artifact_root: Path) -> SequenceManifest:
    return manifest.model_copy(
        update={
            "intrinsics_path": _rebase_artifact_path(manifest.intrinsics_path, artifact_root=artifact_root),
            "rotation_metadata_path": _rebase_artifact_path(
                manifest.rotation_metadata_path, artifact_root=artifact_root
            ),
            "timestamps_path": _rebase_artifact_path(manifest.timestamps_path, artifact_root=artifact_root),
        }
    )


def _rebase_benchmark_inputs(
    benchmark_inputs: PreparedBenchmarkInputs, *, artifact_root: Path
) -> PreparedBenchmarkInputs:
    return benchmark_inputs.model_copy(
        update={
            "reference_trajectories": [
                _rebase_reference_trajectory(reference, artifact_root=artifact_root)
                for reference in benchmark_inputs.reference_trajectories
            ],
            "reference_clouds": [
                _rebase_reference_cloud(reference, artifact_root=artifact_root)
                for reference in benchmark_inputs.reference_clouds
            ],
            "observation_sequences": [
                _rebase_observation_sequence(sequence, artifact_root=artifact_root)
                for sequence in benchmark_inputs.observation_sequences
            ],
        }
    )


def _rebase_reference_trajectory(reference: ReferenceTrajectoryRef, *, artifact_root: Path) -> ReferenceTrajectoryRef:
    return reference.model_copy(
        update={
            "path": _rebase_artifact_path(reference.path, artifact_root=artifact_root),
            "metadata_path": _rebase_artifact_path(reference.metadata_path, artifact_root=artifact_root),
        }
    )


def _rebase_reference_cloud(reference: ReferenceCloudRef, *, artifact_root: Path) -> ReferenceCloudRef:
    return reference.model_copy(
        update={
            "path": _rebase_artifact_path(reference.path, artifact_root=artifact_root),
            "metadata_path": _rebase_artifact_path(reference.metadata_path, artifact_root=artifact_root),
        }
    )


def _rebase_observation_sequence(sequence: ObservationSequenceRef, *, artifact_root: Path) -> ObservationSequenceRef:
    return sequence.model_copy(
        update={"index_path": _rebase_artifact_path(sequence.index_path, artifact_root=artifact_root)}
    )


def _rebase_artifact_path(path: Path | None, *, artifact_root: Path) -> Path | None:
    if path is None or path.exists():
        return path
    artifact_dirs = {"alignment", "benchmark", "evaluation", "input", "reconstruction", "reference", "slam", "summary"}
    for index, part in enumerate(path.parts):
        if part in artifact_dirs:
            return artifact_root.joinpath(*path.parts[index:])
    return path


def _outcome(stage_key: StageKey, *, artifacts: dict[str, ArtifactRef]) -> StageOutcome:
    return StageOutcome(
        stage_key=stage_key,
        status=StageStatus.COMPLETED,
        config_hash=stable_hash({"reuse": stage_key.value}),
        input_fingerprint=stable_hash({key: ref.path.as_posix() for key, ref in artifacts.items()}),
        artifacts=artifacts,
    )


def _status(stage_key: StageKey, message: str) -> StageRuntimeStatus:
    return StageRuntimeStatus(stage_key=stage_key, lifecycle_state=StageStatus.COMPLETED, progress_message=message)


__all__ = ["load_reused_stage_results"]
