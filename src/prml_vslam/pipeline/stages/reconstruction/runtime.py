"""Bounded runtime adapter for offline reference reconstruction."""

from __future__ import annotations

from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.pipeline.ray_runtime.common import artifact_ref
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.pipeline.stages.reconstruction.contracts import ReconstructionRuntimeInput
from prml_vslam.reconstruction import FileRgbdObservationSource, Open3dTsdfBackendConfig, ReconstructionArtifacts

# TODO: why is this class not derived from common StageRuntime base class?


class ReconstructionRuntime:
    """Adapt reconstruction-owned Open3D TSDF execution to the bounded runtime API."""

    def __init__(self) -> None:
        # TODO(pipeline-refactor/WP-10): Switch to the target `reconstruction`
        # stage key after persisted stage-key aliases are removed.
        self._status = StageRuntimeStatus(stage_key=StageKey.REFERENCE_RECONSTRUCTION)

    def status(self) -> StageRuntimeStatus:
        """Return the latest reconstruction runtime status."""
        return self._status

    def stop(self) -> None:
        """Mark the bounded runtime as stopped."""
        self._status = self._status.model_copy(update={"lifecycle_state": StageStatus.STOPPED})

    def run_offline(self, input_payload: ReconstructionRuntimeInput) -> StageResult:
        """Build the reference reconstruction and return a canonical stage result."""
        self._status = self._status.model_copy(
            update={
                "lifecycle_state": StageStatus.RUNNING,
                "progress_message": "Building reference reconstruction.",
            }
        )
        try:
            result = self._run(input_payload)
        except Exception as exc:
            self._status = self._status.model_copy(
                update={
                    "lifecycle_state": StageStatus.FAILED,
                    "last_error": str(exc),
                }
            )
            raise
        self._status = result.final_runtime_status
        return result

    def _run(self, input_payload: ReconstructionRuntimeInput) -> StageResult:
        if input_payload.benchmark_inputs is None:
            raise RuntimeError("Reference reconstruction requires prepared benchmark inputs.")
        if len(input_payload.benchmark_inputs.rgbd_observation_sequences) != 1:
            raise RuntimeError(
                "Reference reconstruction requires exactly one prepared RGB-D observation sequence; "
                f"got {len(input_payload.benchmark_inputs.rgbd_observation_sequences)}."
            )

        sequence_ref = input_payload.benchmark_inputs.rgbd_observation_sequences[0]
        # TODO(pipeline-refactor/WP-09): Build reconstruction backend config
        # from `[stages.reconstruction]` instead of benchmark reference policy.
        backend_config = Open3dTsdfBackendConfig(extract_mesh=input_payload.request.benchmark.reference.extract_mesh)
        backend = backend_config.setup_target()
        artifacts = backend.run_sequence(
            FileRgbdObservationSource(sequence_ref).iter_observations(),
            backend_config=backend_config,
            artifact_root=input_payload.run_paths.reference_cloud_path.parent,
        )
        outcome = StageOutcome(
            stage_key=StageKey.REFERENCE_RECONSTRUCTION,
            status=StageStatus.COMPLETED,
            config_hash=stable_hash(backend_config),
            input_fingerprint=stable_hash(sequence_ref),
            artifacts=_artifact_map(artifacts),
            metrics={"observation_count": sequence_ref.observation_count},
        )
        return StageResult(
            stage_key=StageKey.REFERENCE_RECONSTRUCTION,
            payload=artifacts,
            outcome=outcome,
            final_runtime_status=StageRuntimeStatus(
                stage_key=StageKey.REFERENCE_RECONSTRUCTION,
                lifecycle_state=StageStatus.COMPLETED,
                progress_message="Reference reconstruction complete.",
                completed_steps=sequence_ref.observation_count,
                total_steps=sequence_ref.observation_count,
                progress_unit="observations",
                processed_items=sequence_ref.observation_count,
            ),
        )


def _artifact_map(artifacts: ReconstructionArtifacts):
    artifact_map = {
        "reference_cloud": artifact_ref(artifacts.reference_cloud_path, kind="ply"),
        "reconstruction_metadata": artifact_ref(artifacts.metadata_path, kind="json"),
    }
    if artifacts.mesh_path is not None:
        artifact_map["reference_mesh"] = artifact_ref(artifacts.mesh_path, kind="ply")
    for key, path in artifacts.extras.items():
        artifact_map[f"extra:{key}"] = artifact_ref(path, kind=path.suffix.lstrip(".") or "file")
    return artifact_map


__all__ = ["ReconstructionRuntime", "ReconstructionRuntimeInput"]
