"""Bounded runtime adapter for offline reference reconstruction."""

from __future__ import annotations

import time

from prml_vslam.interfaces.artifacts import ArtifactRef, artifact_ref
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus, StageRuntimeUpdate
from prml_vslam.pipeline.stages.base.protocols import LiveUpdateStageRuntime, OfflineStageRuntime
from prml_vslam.reconstruction import ReconstructionArtifacts
from prml_vslam.reconstruction.stage.config import ReconstructionBackend
from prml_vslam.reconstruction.stage.visualization import ReconstructionVisualizationAdapter
from prml_vslam.sources.contracts import PreparedBenchmarkInputs
from prml_vslam.sources.observation_sequence import FileObservationSequenceLoader
from prml_vslam.utils import BaseData, RunArtifactPaths
from prml_vslam.utils.serialization import stable_hash


class ReconstructionStageInput(BaseData):
    """Inputs required to build one offline reference reconstruction."""

    backend: ReconstructionBackend
    run_paths: RunArtifactPaths
    benchmark_inputs: PreparedBenchmarkInputs | None = None


class ReconstructionRuntime(OfflineStageRuntime[ReconstructionStageInput], LiveUpdateStageRuntime):
    """Adapt reconstruction-owned Open3D TSDF execution to the bounded runtime API.

    The runtime turns prepared RGB-D observation references into a
    reconstruction-owned backend call, then wraps the durable output in generic
    stage result/status contracts. Open3D TSDF parameters, output metadata, and
    reconstruction artifact semantics stay in :mod:`prml_vslam.reconstruction`.
    """

    def __init__(self, *, visualization_adapter: ReconstructionVisualizationAdapter | None = None) -> None:
        self._status = StageRuntimeStatus(stage_key=StageKey.RECONSTRUCTION)
        self._visualization_adapter = (
            ReconstructionVisualizationAdapter() if visualization_adapter is None else visualization_adapter
        )
        self._pending_updates: list[StageRuntimeUpdate] = []

    def status(self) -> StageRuntimeStatus:
        """Return the latest reconstruction runtime status."""
        return self._status

    def stop(self) -> None:
        """Mark the bounded runtime as stopped."""
        self._status = self._status.model_copy(update={"lifecycle_state": StageStatus.STOPPED})

    def drain_runtime_updates(self, max_items: int | None = None) -> list[StageRuntimeUpdate]:
        """Return pending reconstruction visualization updates without blocking."""
        if max_items is None:
            updates = self._pending_updates
            self._pending_updates = []
            return updates
        updates = self._pending_updates[:max_items]
        self._pending_updates = self._pending_updates[max_items:]
        return updates

    def run_offline(self, input_payload: ReconstructionStageInput) -> StageResult:
        """Build the reference reconstruction and return a canonical stage result.

        The method expects exactly one prepared RGB-D sequence. Future
        reconstruction modes can widen the stage config, but should preserve
        the same artifact-first ``StageResult`` handoff.
        """
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

    def _run(self, input_payload: ReconstructionStageInput) -> StageResult:
        if input_payload.benchmark_inputs is None:
            raise RuntimeError("Reference reconstruction requires prepared benchmark inputs.")
        if len(input_payload.benchmark_inputs.observation_sequences) != 1:
            raise RuntimeError(
                "Reference reconstruction requires exactly one prepared observation sequence; "
                f"got {len(input_payload.benchmark_inputs.observation_sequences)}."
            )

        sequence_ref = input_payload.benchmark_inputs.observation_sequences[0]
        backend_config = input_payload.backend
        backend = backend_config.setup_target()
        artifacts = backend.run_sequence(
            FileObservationSequenceLoader(sequence_ref).iter_observations(),
            artifact_root=input_payload.run_paths.reference_cloud_path.parent,
        )
        artifact_map = _artifact_map(artifacts)
        outcome = StageOutcome(
            stage_key=StageKey.RECONSTRUCTION,
            status=StageStatus.COMPLETED,
            config_hash=stable_hash(backend_config),
            input_fingerprint=stable_hash(sequence_ref),
            artifacts=artifact_map,
            metrics={"observation_count": sequence_ref.observation_count},
        )
        final_status = StageRuntimeStatus(
            stage_key=StageKey.RECONSTRUCTION,
            lifecycle_state=StageStatus.COMPLETED,
            progress_message="Reference reconstruction complete.",
            completed_steps=sequence_ref.observation_count,
            total_steps=sequence_ref.observation_count,
            progress_unit="observations",
            processed_items=sequence_ref.observation_count,
        )
        visualizations = self._visualization_adapter.build_items(
            artifacts,
            artifact_map,
            reconstruction_id="reference",
        )
        if visualizations:
            self._pending_updates.append(
                StageRuntimeUpdate(
                    stage_key=StageKey.RECONSTRUCTION,
                    timestamp_ns=time.time_ns(),
                    visualizations=visualizations,
                    runtime_status=final_status,
                )
            )
        return StageResult(
            stage_key=StageKey.RECONSTRUCTION,
            payload=artifacts,
            outcome=outcome,
            final_runtime_status=final_status,
        )


def _artifact_map(artifacts: ReconstructionArtifacts) -> dict[str, ArtifactRef]:
    artifact_map = {
        "reference_cloud": artifact_ref(artifacts.reference_cloud_path, kind="ply"),
        "reconstruction_metadata": artifact_ref(artifacts.metadata_path, kind="json"),
    }
    if artifacts.mesh_path is not None:
        artifact_map["reference_mesh"] = artifact_ref(artifacts.mesh_path, kind="ply")
    artifact_map.update(
        {
            f"extra:{key}": artifact_ref(path, kind=path.suffix.lstrip(".") or "file")
            for key, path in artifacts.extras.items()
        }
    )
    return artifact_map


__all__ = ["ReconstructionRuntime", "ReconstructionStageInput"]
