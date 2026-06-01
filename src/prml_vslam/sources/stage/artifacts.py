"""Source-stage artifact key and projection helpers."""

from __future__ import annotations

from prml_vslam.interfaces import ObservationSequenceRef
from prml_vslam.interfaces.artifacts import ArtifactRef, artifact_ref
from prml_vslam.sources.contracts import (
    ReferenceCloudRef,
    ReferenceSource,
    ReferenceTrajectoryRef,
)
from prml_vslam.sources.stage.contracts import SourceStageOutput
from prml_vslam.utils import RunArtifactPaths


def source_artifacts(*, run_paths: RunArtifactPaths, output: SourceStageOutput) -> dict[str, ArtifactRef]:
    """Project source output contracts into durable stage artifact refs."""
    sequence_manifest = output.sequence_manifest
    artifacts = {
        "sequence_manifest": artifact_ref(run_paths.sequence_manifest_path, kind="json"),
    }
    for key, path, kind in (
        ("rgb_dir", sequence_manifest.rgb_dir, "dir"),
        ("timestamps", sequence_manifest.timestamps_path, "json"),
        ("intrinsics", sequence_manifest.intrinsics_path, "yaml"),
        ("rotation_metadata", sequence_manifest.rotation_metadata_path, "json"),
    ):
        if path is not None:
            artifacts[key] = artifact_ref(path, kind=kind)
    if output.benchmark_inputs is not None:
        artifacts["benchmark_inputs"] = artifact_ref(run_paths.benchmark_inputs_path, kind="json")
        for trajectory_reference in output.benchmark_inputs.reference_trajectories:
            artifacts[reference_trajectory_artifact_key(trajectory_reference)] = artifact_ref(
                trajectory_reference.path,
                kind="tum",
            )
        for cloud_reference in output.benchmark_inputs.reference_clouds:
            artifacts[reference_cloud_artifact_key(cloud_reference)] = artifact_ref(cloud_reference.path, kind="ply")
            artifacts[reference_cloud_metadata_artifact_key(cloud_reference)] = artifact_ref(
                cloud_reference.metadata_path,
                kind="json",
            )
        for observation_reference in output.benchmark_inputs.observation_sequences:
            artifacts[observation_sequence_artifact_key(observation_reference)] = artifact_ref(
                observation_reference.index_path,
                kind="observation_sequence",
            )
    return artifacts


def reference_trajectory_artifact_key(reference: ReferenceTrajectoryRef | ReferenceSource) -> str:
    """Return the source-stage artifact key for one prepared trajectory."""
    if isinstance(reference, ReferenceSource):
        return f"reference_tum:{reference.value}"
    target_frame = _entity_token(reference.target_frame or "world")
    coordinate_status = _entity_token(
        reference.coordinate_status.value if reference.coordinate_status is not None else "source_native"
    )
    return f"reference_tum:{reference.source.value}:{target_frame}:{coordinate_status}"


def reference_cloud_artifact_key(reference: ReferenceCloudRef) -> str:
    """Return the source-stage artifact key for one prepared static cloud."""
    return f"reference_cloud:{reference.source.value}:{reference.coordinate_status.value}"


def reference_cloud_metadata_artifact_key(reference: ReferenceCloudRef) -> str:
    """Return the source-stage artifact key for one static cloud metadata file."""
    return f"reference_cloud_metadata:{reference.source.value}:{reference.coordinate_status.value}"


def observation_sequence_artifact_key(reference: ObservationSequenceRef) -> str:
    """Return the source-stage artifact key for one observation sequence index."""
    return f"observation_sequence:{reference.source_id}:{reference.sequence_id}"


def _entity_token(value: str) -> str:
    stripped = value.strip().replace(" ", "_")
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in stripped) or "reference"


__all__ = [
    "observation_sequence_artifact_key",
    "reference_cloud_artifact_key",
    "reference_cloud_metadata_artifact_key",
    "reference_trajectory_artifact_key",
    "source_artifacts",
]
