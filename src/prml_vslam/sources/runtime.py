"""Source stage runtime for normalized sequence preparation.

This runtime owns the target source-stage boundary. It prepares the canonical
``SequenceManifest`` and optional ``PreparedBenchmarkInputs`` once, then returns
them as a single ``SourceStageOutput`` payload for downstream stages.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from prml_vslam.datasets.contracts import FrameSelectionConfig
from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.interfaces.ingest import SequenceManifest
from prml_vslam.interfaces.runtime import FramePacket
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import stable_hash, write_json
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.pipeline.stages.base.protocols import OfflineStageRuntime
from prml_vslam.protocols.runtime import FramePacketStream
from prml_vslam.protocols.source import BenchmarkInputSource, OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, SourceStageOutput
from prml_vslam.sources.visualization import (
    reference_cloud_artifact_key,
    reference_cloud_metadata_artifact_key,
    reference_point_cloud_sequence_index_artifact_key,
    reference_point_cloud_sequence_payload_artifact_key,
    reference_point_cloud_sequence_trajectory_artifact_key,
    reference_trajectory_artifact_key,
    rgbd_observation_sequence_artifact_key,
)
from prml_vslam.utils import BaseData, Console, PathConfig, RunArtifactPaths
from prml_vslam.utils.video_frames import extract_video_frames

_CONSOLE = Console(__name__).child("SourceRuntime")


class SourceRuntimeInput(BaseData):
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


class SourceRuntime(OfflineStageRuntime[SourceRuntimeInput]):
    """Prepare the normalized source output for offline or streaming runs.

    The runtime is method-agnostic: it materializes a
    :class:`prml_vslam.interfaces.ingest.SequenceManifest`, optional
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
        sequence_manifest = _materialize_manifest(
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
            artifacts=_source_artifacts(run_paths=run_paths, output=source_output),
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
            artifacts[reference_trajectory_artifact_key(reference)] = _artifact_ref(reference.path, kind="tum")
        for reference in output.benchmark_inputs.reference_clouds:
            artifacts[reference_cloud_artifact_key(reference)] = _artifact_ref(reference.path, kind="ply")
            artifacts[reference_cloud_metadata_artifact_key(reference)] = _artifact_ref(
                reference.metadata_path,
                kind="json",
            )
        for reference in output.benchmark_inputs.reference_point_cloud_sequences:
            artifacts[reference_point_cloud_sequence_index_artifact_key(reference)] = _artifact_ref(
                reference.index_path,
                kind="csv",
            )
            artifacts[reference_point_cloud_sequence_trajectory_artifact_key(reference)] = _artifact_ref(
                reference.trajectory_path,
                kind="tum",
            )
            artifacts[reference_point_cloud_sequence_payload_artifact_key(reference)] = _artifact_ref(
                reference.payload_root,
                kind="dir",
            )
        for reference in output.benchmark_inputs.rgbd_observation_sequences:
            artifacts[rgbd_observation_sequence_artifact_key(reference)] = _artifact_ref(
                reference.index_path,
                kind="rgbd_observation_sequence",
            )
    return artifacts


def _artifact_ref(path: Path, *, kind: str) -> ArtifactRef:
    resolved_path = path.resolve()
    return ArtifactRef(
        path=resolved_path,
        kind=kind,
        fingerprint=stable_hash({"path": str(resolved_path), "kind": kind}),
    )


def _materialize_manifest(
    *,
    input_payload: SourceRuntimeInput,
    prepared_manifest: SequenceManifest,
    run_paths: RunArtifactPaths,
) -> SequenceManifest:
    """Materialize the run-owned source manifest for this source stage."""
    _CONSOLE.info("Materializing source manifest for sequence '%s'.", prepared_manifest.sequence_id)
    rotation_degrees = 0
    rgb_dir = prepared_manifest.rgb_dir
    timestamps_path = prepared_manifest.timestamps_path
    intrinsics_path = prepared_manifest.intrinsics_path
    frame_stride = _frame_stride_for_source(input_payload, prepared_manifest=prepared_manifest)
    cached_rgb_dir: Path | None = None
    fallback_timestamps_ns: list[int] = []

    if prepared_manifest.video_path is not None and rgb_dir is None:
        max_frames = _max_frames_for_input(input_payload)
        cached_rgb_dir = _check_extraction_cache(
            video_path=prepared_manifest.video_path,
            output_dir=run_paths.input_frames_dir,
            frame_stride=frame_stride,
            max_frames=max_frames,
        )
        if cached_rgb_dir is not None:
            _CONSOLE.info(
                "Reusing extracted frames from '%s' with frame_stride=%d and max_frames=%s.",
                cached_rgb_dir,
                frame_stride,
                max_frames,
            )
            rgb_dir = cached_rgb_dir
        else:
            _CONSOLE.info(
                "Extracting frames from '%s' into '%s' with frame_stride=%d and max_frames=%s.",
                prepared_manifest.video_path,
                run_paths.input_frames_dir,
                frame_stride,
                max_frames,
            )
            extracted = extract_video_frames(
                video_path=prepared_manifest.video_path,
                output_dir=run_paths.input_frames_dir,
                frame_stride=frame_stride,
                max_frames=max_frames,
            )
            rgb_dir = extracted.rgb_dir
            _write_json_payload(
                rgb_dir / ".ingest_metadata.json",
                {
                    "video_path": str(prepared_manifest.video_path.resolve()),
                    "frame_stride": frame_stride,
                    "max_frames": max_frames,
                },
            )

        fallback_timestamps_ns = [] if cached_rgb_dir is not None else extracted.timestamps_ns

    timestamps_source = _preferred_timestamps_source(
        prepared_manifest=prepared_manifest,
        run_paths=run_paths,
        cached_rgb_dir=cached_rgb_dir,
    )
    if (timestamps_source is not None and timestamps_source.exists()) or fallback_timestamps_ns:
        timestamps_ns = _resolve_timestamps_ns(
            source_path=timestamps_source,
            frame_stride=frame_stride,
            fallback_timestamps_ns=fallback_timestamps_ns,
        )
        timestamps_path = _write_json_payload(
            run_paths.input_timestamps_path,
            {"timestamps_ns": timestamps_ns, "frame_stride": frame_stride},
        )

    if intrinsics_path is not None:
        run_paths.input_intrinsics_path.parent.mkdir(parents=True, exist_ok=True)
        if intrinsics_path.resolve() != run_paths.input_intrinsics_path.resolve():
            shutil.copyfile(intrinsics_path, run_paths.input_intrinsics_path)
        intrinsics_path = run_paths.input_intrinsics_path.resolve()

    rotation_metadata_path = _write_json_payload(
        run_paths.input_rotation_metadata_path,
        {"rotation_degrees": rotation_degrees},
    )

    return prepared_manifest.model_copy(
        update={
            "rgb_dir": rgb_dir,
            "timestamps_path": timestamps_path,
            "intrinsics_path": intrinsics_path,
            "rotation_metadata_path": rotation_metadata_path,
        }
    )


def _frame_stride_for_source(input_payload: SourceRuntimeInput, *, prepared_manifest: SequenceManifest) -> int:
    if prepared_manifest.video_path is None:
        return 1
    return input_payload.frame_stride


def _max_frames_for_input(input_payload: SourceRuntimeInput) -> int | None:
    if input_payload.mode is not PipelineMode.STREAMING:
        return None
    return input_payload.streaming_max_frames


def _check_extraction_cache(
    *,
    video_path: Path,
    output_dir: Path,
    frame_stride: int,
    max_frames: int | None,
) -> Path | None:
    metadata_path = output_dir / ".ingest_metadata.json"
    if not metadata_path.exists():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (
            metadata.get("video_path") == str(video_path.resolve())
            and metadata.get("frame_stride") == frame_stride
            and metadata.get("max_frames") == max_frames
            and any(output_dir.glob("*.png"))
        ):
            return output_dir.resolve()
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _resolve_timestamps_ns(
    *,
    source_path: Path | None,
    frame_stride: int,
    fallback_timestamps_ns: list[int],
) -> list[int]:
    if source_path is None or not source_path.exists():
        return fallback_timestamps_ns
    suffix = source_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("timestamps_ns"), list):
            values = [int(value) for value in payload["timestamps_ns"]]
            return values[::frame_stride]
        raise RuntimeError(f"Expected normalized timestamps JSON with a `timestamps_ns` list at '{source_path}'.")
    rows = []
    for line in source_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        first_field = stripped.split(",", maxsplit=1)[0].strip() if "," in stripped else stripped.split()[0]
        rows.append(first_field)
    if not rows:
        return fallback_timestamps_ns
    values = [int(round(float(value) * 1e9)) for value in rows]
    return values[::frame_stride]


def _preferred_timestamps_source(
    *,
    prepared_manifest: SequenceManifest,
    run_paths: RunArtifactPaths,
    cached_rgb_dir: Path | None,
) -> Path | None:
    if prepared_manifest.timestamps_path is not None and prepared_manifest.timestamps_path.exists():
        return prepared_manifest.timestamps_path
    if cached_rgb_dir is not None and run_paths.input_timestamps_path.exists():
        return run_paths.input_timestamps_path
    return prepared_manifest.timestamps_path


def _write_json_payload(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path.resolve()


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

    def connect(self) -> Any:
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
