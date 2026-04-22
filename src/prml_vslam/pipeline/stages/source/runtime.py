"""Source stage runtime for normalized sequence preparation.

This runtime owns the target source-stage boundary. It prepares the canonical
``SequenceManifest`` and optional ``PreparedBenchmarkInputs`` once, then returns
them as a single ``SourceStageOutput`` payload for downstream stages.
"""

from __future__ import annotations

from pathlib import Path

from prml_vslam.datasets.contracts import FrameSelectionConfig
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest, SourceStageOutput
from prml_vslam.interfaces.runtime import FramePacket
from prml_vslam.interfaces.slam import ArtifactRef
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import stable_hash, write_json
from prml_vslam.pipeline.ingest import materialize_offline_manifest
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.pipeline.stages.base.protocols import OfflineStageRuntime
from prml_vslam.protocols.runtime import FramePacketStream
from prml_vslam.protocols.source import BenchmarkInputSource, OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.utils import BaseData, PathConfig, RunArtifactPaths


class SourceRuntimeInput(BaseData):
    """Run-scoped input required to prepare one normalized source stage.

    This is a migration input while launch still submits
    :class:`prml_vslam.pipeline.contracts.request.RunRequest`. The target
    source runtime should eventually receive target source-stage config plus
    run context instead of reading source policy from the full request.
    """

    # TODO(pipeline-refactor/WP-09): Replace this RunRequest compatibility
    # field with target source-stage config/input once RunConfig drives launch
    # paths directly.
    request: RunRequest
    """Current run request whose source policy and mode drive materialization."""

    artifact_root: Path
    """Root directory for run-owned source artifacts."""


class SourceRuntime(OfflineStageRuntime[SourceRuntimeInput]):
    """Prepare the normalized source output for offline or streaming runs.

    The runtime is method-agnostic: it materializes a
    :class:`prml_vslam.interfaces.ingest.SequenceManifest`, optional
    :class:`prml_vslam.interfaces.ingest.PreparedBenchmarkInputs`, and a
    terminal :class:`prml_vslam.pipeline.stages.base.contracts.StageResult`.
    It does not resize images for a SLAM backend or choose evaluation policy.
    """

    def __init__(self, *, source: OfflineSequenceSource) -> None:
        self._source = source
        # TODO(pipeline-refactor/WP-10): Switch to the target source stage key
        # after persisted events, manifests, and old-run inspection no longer
        # require the current `ingest` executable key.
        self._status = StageRuntimeStatus(stage_key=StageKey.INGEST)

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

    def run_offline(self, input_payload: SourceRuntimeInput) -> StageResult:
        """Prepare and persist the canonical source-stage output.

        The result payload is :class:`prml_vslam.interfaces.ingest.SourceStageOutput`.
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

    def _prepare_source(self, input_payload: SourceRuntimeInput) -> StageResult:
        run_paths = RunArtifactPaths.build(input_payload.artifact_root)
        prepared_manifest = self._source.prepare_sequence_manifest(run_paths.sequence_manifest_path.parent)
        benchmark_inputs = None
        if isinstance(self._source, BenchmarkInputSource):
            benchmark_inputs = self._source.prepare_benchmark_inputs(run_paths.benchmark_inputs_path.parent)
            if benchmark_inputs is not None:
                write_json(run_paths.benchmark_inputs_path, benchmark_inputs)
        sequence_manifest = materialize_offline_manifest(
            request=input_payload.request,
            prepared_manifest=prepared_manifest,
            run_paths=run_paths,
        )
        write_json(run_paths.sequence_manifest_path, sequence_manifest)
        source_output = SourceStageOutput(
            sequence_manifest=sequence_manifest,
            benchmark_inputs=benchmark_inputs,
        )
        outcome = StageOutcome(
            stage_key=StageKey.INGEST,
            status=StageStatus.COMPLETED,
            config_hash=stable_hash(input_payload.request.source),
            input_fingerprint=stable_hash(input_payload.request.source),
            artifacts=_source_artifacts(run_paths=run_paths, output=source_output),
        )
        return StageResult(
            stage_key=StageKey.INGEST,
            payload=source_output,
            outcome=outcome,
            final_runtime_status=StageRuntimeStatus(
                stage_key=StageKey.INGEST,
                lifecycle_state=StageStatus.COMPLETED,
                progress_message="Source preparation complete.",
            ),
        )


def _source_artifacts(*, run_paths: RunArtifactPaths, output: SourceStageOutput) -> dict[str, ArtifactRef]:
    sequence_manifest = output.sequence_manifest
    artifacts = {
        "sequence_manifest": _artifact_ref(run_paths.sequence_manifest_path, kind="json"),
    }
    if sequence_manifest.rgb_dir is not None:
        artifacts["rgb_dir"] = _artifact_ref(sequence_manifest.rgb_dir, kind="dir")
    if sequence_manifest.timestamps_path is not None:
        artifacts["timestamps"] = _artifact_ref(sequence_manifest.timestamps_path, kind="json")
    if sequence_manifest.intrinsics_path is not None:
        artifacts["intrinsics"] = _artifact_ref(sequence_manifest.intrinsics_path, kind="yaml")
    if sequence_manifest.rotation_metadata_path is not None:
        artifacts["rotation_metadata"] = _artifact_ref(sequence_manifest.rotation_metadata_path, kind="json")
    if output.benchmark_inputs is not None:
        artifacts["benchmark_inputs"] = _artifact_ref(run_paths.benchmark_inputs_path, kind="json")
        for reference in output.benchmark_inputs.reference_trajectories:
            artifacts[f"reference_tum:{reference.source.value}"] = _artifact_ref(reference.path, kind="tum")
    return artifacts


def _artifact_ref(path: Path, *, kind: str) -> ArtifactRef:
    resolved_path = path.resolve()
    return ArtifactRef(
        path=resolved_path,
        kind=kind,
        fingerprint=stable_hash({"path": str(resolved_path), "kind": kind}),
    )


class VideoOfflineSequenceSource:
    """Adapt a raw video path into the normalized offline source seam."""

    def __init__(self, *, path_config: PathConfig, video_path: Path, frame_stride: int) -> None:
        self._path_config = path_config
        self._video_path = video_path
        self._frame_stride = frame_stride

    @property
    def label(self) -> str:
        """Return the compact user-facing label for this source."""
        return f"Video '{self._video_path.name}'"

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        """Resolve the video path and return the minimal normalized manifest."""
        del output_dir
        resolved_video_path = self._path_config.resolve_video_path(self._video_path, must_exist=True)
        return SequenceManifest(
            sequence_id=resolved_video_path.stem,
            video_path=resolved_video_path,
        )


class SampledFramePacketStream:
    """Apply source sampling policy to an existing packet stream."""

    def __init__(self, stream: FramePacketStream, *, frame_selection: FrameSelectionConfig) -> None:
        self._stream = stream
        self._frame_selection = frame_selection
        self._seen_packets = 0
        self._last_emitted_timestamp_ns: int | None = None

    def connect(self) -> object:
        """Connect the wrapped stream."""
        return self._stream.connect()

    def disconnect(self) -> None:
        """Disconnect the wrapped stream."""
        self._stream.disconnect()

    def wait_for_packet(self, timeout_seconds: float | None = None) -> FramePacket:
        """Return the next packet accepted by the configured sampling policy."""
        while True:
            packet = self._stream.wait_for_packet(timeout_seconds=timeout_seconds)
            self._seen_packets += 1
            if not self._should_emit(packet):
                continue
            self._last_emitted_timestamp_ns = packet.timestamp_ns
            return packet

    def _should_emit(self, packet: FramePacket) -> bool:
        if self._frame_selection.target_fps is not None:
            if self._last_emitted_timestamp_ns is None:
                return True
            min_delta_ns = int(round(1e9 / self._frame_selection.target_fps))
            return packet.timestamp_ns - self._last_emitted_timestamp_ns >= min_delta_ns
        return (self._seen_packets - 1) % self._frame_selection.frame_stride == 0


class SampledStreamingSource(StreamingSequenceSource):
    """Apply source sampling policy to an existing streaming source."""

    def __init__(self, source: StreamingSequenceSource, *, frame_selection: FrameSelectionConfig) -> None:
        self._source = source
        self._frame_selection = frame_selection
        self.label = source.label

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        """Delegate manifest preparation to the wrapped source."""
        return self._source.prepare_sequence_manifest(output_dir)

    def prepare_benchmark_inputs(self, output_dir: Path) -> PreparedBenchmarkInputs | None:
        """Delegate benchmark preparation when the wrapped source supports it."""
        if not isinstance(self._source, BenchmarkInputSource):
            return None
        return self._source.prepare_benchmark_inputs(output_dir)

    def open_stream(self, *, loop: bool) -> FramePacketStream:
        """Open the wrapped source stream with sampling applied."""
        return SampledFramePacketStream(
            self._source.open_stream(loop=loop),
            frame_selection=self._frame_selection,
        )


__all__ = [
    "SampledFramePacketStream",
    "SampledStreamingSource",
    "SourceRuntime",
    "SourceRuntimeInput",
    "VideoOfflineSequenceSource",
]
