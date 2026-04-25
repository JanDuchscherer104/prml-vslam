"""Source stage runtime for normalized sequence preparation.

This runtime owns the target source-stage boundary. It prepares the canonical
``SequenceManifest`` and optional ``PreparedBenchmarkInputs`` once, then returns
them as a single ``SourceStageOutput`` payload for downstream stages.
"""

from __future__ import annotations

from pathlib import Path

from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.pipeline.stages.base.protocols import OfflineStageRuntime
from prml_vslam.protocols.source import BenchmarkInputSource, OfflineSequenceSource
from prml_vslam.sources.contracts import SourceStageOutput
from prml_vslam.sources.materialization import materialize_manifest, source_artifacts
from prml_vslam.utils import BaseData, RunArtifactPaths
from prml_vslam.utils.serialization import write_json


class SourceStageInput(BaseData):
    """Run-scoped input required to prepare one normalized source stage.

    The input carries the source launch policy plus the small amount of run
    context needed for artifact ownership and streaming-only frame caps.
    """

    artifact_root: Path
    """Root directory for run-owned source artifacts."""

    mode: PipelineMode
    frame_stride: int = 1
    streaming_max_frames: int | None = None
    config_hash: str = ""
    input_fingerprint: str = ""


class SourceRuntime(OfflineStageRuntime[SourceStageInput]):
    """Prepare the normalized source output for offline or streaming runs.

    The runtime is method-agnostic: it materializes a
    :class:`prml_vslam.sources.contracts.SequenceManifest`, optional
    :class:`prml_vslam.sources.contracts.PreparedBenchmarkInputs`, and a
    terminal :class:`prml_vslam.pipeline.stages.base.contracts.StageResult`.
    It does not resize images for a SLAM backend or choose evaluation policy.
    """

    def __init__(self, *, source: OfflineSequenceSource) -> None:
        self._source = source
        self._status = StageRuntimeStatus(stage_key=StageKey.SOURCE)

    def status(self) -> StageRuntimeStatus:
        """Return the latest source-runtime status."""
        return self._status

    def stop(self) -> None:
        """Mark the source runtime as stopped.

        Source preparation is currently a bounded synchronous operation, so
        stopping only updates status for callers that use the uniform runtime
        lifecycle surface.
        """
        self._status = self._status.model_copy(update={"lifecycle_state": StageStatus.STOPPED})

    def run_offline(self, input_payload: SourceStageInput) -> StageResult:
        """Prepare and persist the canonical source-stage output.

        The result payload is :class:`prml_vslam.sources.contracts.SourceStageOutput`.
        Downstream stages should read this payload from the result store rather
        than reaching back into source adapters or dataset services.
        """
        self._status = self._status.model_copy(
            update={
                "lifecycle_state": StageStatus.RUNNING,
                "progress_message": "Preparing source manifest.",
            }
        )
        try:
            result = self._prepare_source(input_payload)
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

    def _prepare_source(self, input_payload: SourceStageInput) -> StageResult:
        run_paths = RunArtifactPaths.build(input_payload.artifact_root)
        prepared_manifest = self._source.prepare_sequence_manifest(run_paths.sequence_manifest_path.parent)
        benchmark_inputs = None
        if isinstance(self._source, BenchmarkInputSource):
            benchmark_inputs = self._source.prepare_benchmark_inputs(run_paths.benchmark_inputs_path.parent)
            if benchmark_inputs is not None:
                write_json(run_paths.benchmark_inputs_path, benchmark_inputs)
        sequence_manifest = materialize_manifest(
            input_payload=input_payload,
            prepared_manifest=prepared_manifest,
            run_paths=run_paths,
        )
        write_json(run_paths.sequence_manifest_path, sequence_manifest)
        source_output = SourceStageOutput(
            sequence_manifest=sequence_manifest,
            benchmark_inputs=benchmark_inputs,
        )
        outcome = StageOutcome(
            stage_key=StageKey.SOURCE,
            status=StageStatus.COMPLETED,
            config_hash=input_payload.config_hash,
            input_fingerprint=input_payload.input_fingerprint,
            artifacts=source_artifacts(run_paths=run_paths, output=source_output),
        )
        return StageResult(
            stage_key=StageKey.SOURCE,
            payload=source_output,
            outcome=outcome,
            final_runtime_status=StageRuntimeStatus(
                stage_key=StageKey.SOURCE,
                lifecycle_state=StageStatus.COMPLETED,
                progress_message="Source preparation complete.",
            ),
        )


__all__ = [
    "SourceRuntime",
    "SourceStageInput",
]
