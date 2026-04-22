"""Stage lifecycle helpers and runtime result storage.

This module owns target runtime scaffolding that can coexist with the current
``RuntimeStageProgram`` migration path. It introduces the keyed
``StageResult`` store and a small lifecycle runner without moving existing
stage bodies out of the Ray runtime package.
"""

from __future__ import annotations

from collections.abc import Callable

from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest, SourceStageOutput
from prml_vslam.interfaces.runtime import FramePacket
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.stages import StageKey

# TODO(pipeline-refactor/WP-10): Remove this import after all stage runtimes
# return `StageResult` directly and no helper or actor returns
# `StageCompletionPayload`.
from prml_vslam.pipeline.ray_runtime.stage_program import StageCompletionPayload
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.pipeline.stages.base.protocols import OfflineStageRuntime, StreamingStageRuntime
from prml_vslam.utils import BaseData

RuntimeInput = BaseData
StreamItem = BaseData | FramePacket
StageStartedCallback = Callable[[StageKey], None]
StageCompletedCallback = Callable[[StageKey, StageResult], None]
StageFailedCallback = Callable[[StageKey, StageOutcome], None]


class StageDependencyError(RuntimeError):
    """Raised when a downstream stage requests an unavailable result payload."""


class StageResultStore:
    """Store completed stage results and compatibility payloads by stage key.

    ``StageResult`` is the target runtime handoff. During migration this store
    can also ingest current ``StageCompletionPayload`` values so new code can
    exercise target accessors while existing stage helpers keep their current
    return type.
    """

    def __init__(self) -> None:
        self._results: dict[StageKey, StageResult] = {}
        # TODO(pipeline-refactor/WP-10): Remove the legacy payload cache after
        # all stage runtimes return `StageResult` directly and no helper or
        # actor returns `StageCompletionPayload`.
        self._legacy_payloads: dict[StageKey, StageCompletionPayload] = {}
        self._ordered_stage_keys: list[StageKey] = []

    def put(self, result: StageResult) -> None:
        """Store one completed target result."""
        if result.stage_key not in self._results:
            self._ordered_stage_keys.append(result.stage_key)
        self._results[result.stage_key] = result

    def put_completion_payload(
        self,
        *,
        stage_key: StageKey,
        payload: StageCompletionPayload,
        final_runtime_status: StageRuntimeStatus | None = None,
    ) -> StageResult:
        """Store a current migration payload as a target ``StageResult``."""
        # TODO(pipeline-refactor/WP-10): Remove this compatibility entrypoint
        # after all stage runtimes return `StageResult` directly and no helper
        # or actor returns `StageCompletionPayload`.
        self._legacy_payloads[stage_key] = payload
        result = stage_result_from_completion_payload(
            stage_key=stage_key,
            payload=payload,
            final_runtime_status=final_runtime_status,
        )
        self.put(result)
        return result

    def require_result(self, stage_key: StageKey) -> StageResult:
        """Return the completed result for ``stage_key`` or fail clearly."""
        try:
            return self._results[stage_key]
        except KeyError as exc:
            raise StageDependencyError(f"Missing result for stage '{stage_key.value}'.") from exc

    def require_sequence_manifest(self) -> SequenceManifest:
        """Return the normalized source manifest from target or migration state."""
        result = self._results.get(StageKey.INGEST)
        if result is not None and isinstance(result.payload, SourceStageOutput):
            return result.payload.sequence_manifest
        if result is not None and isinstance(result.payload, SequenceManifest):
            return result.payload
        # TODO(pipeline-refactor/WP-10): Remove this legacy fallback after all
        # stage runtimes return `StageResult` directly and no helper or actor
        # returns `StageCompletionPayload`.
        payload = self._legacy_payloads.get(StageKey.INGEST)
        if payload is not None and payload.sequence_manifest is not None:
            return payload.sequence_manifest
        raise StageDependencyError("Missing SequenceManifest from ingest/source stage result.")

    def require_benchmark_inputs(self) -> PreparedBenchmarkInputs | None:
        """Return prepared benchmark inputs when the source stage produced them."""
        result = self._results.get(StageKey.INGEST)
        if result is not None and isinstance(result.payload, SourceStageOutput):
            return result.payload.benchmark_inputs
        if result is not None and isinstance(result.payload, PreparedBenchmarkInputs):
            return result.payload
        # TODO(pipeline-refactor/WP-10): Remove this legacy fallback after all
        # stage runtimes return `StageResult` directly and no helper or actor
        # returns `StageCompletionPayload`.
        payload = self._legacy_payloads.get(StageKey.INGEST)
        if payload is not None:
            return payload.benchmark_inputs
        return None

    def require_slam_artifacts(self) -> SlamArtifacts:
        """Return normalized SLAM artifacts from target or migration state."""
        result = self._results.get(StageKey.SLAM)
        if result is not None and isinstance(result.payload, SlamArtifacts):
            return result.payload
        # TODO(pipeline-refactor/WP-10): Remove this legacy fallback after all
        # stage runtimes return `StageResult` directly and no helper or actor
        # returns `StageCompletionPayload`.
        payload = self._legacy_payloads.get(StageKey.SLAM)
        if payload is not None and payload.slam is not None:
            return payload.slam
        raise StageDependencyError("Missing SlamArtifacts from SLAM stage result.")

    def ordered_outcomes(self) -> list[StageOutcome]:
        """Return terminal outcomes in first-completion order."""
        return [self._results[stage_key].outcome for stage_key in self._ordered_stage_keys]


class StageRunner:
    """Run target runtime protocol calls and record results generically."""

    def __init__(self, result_store: StageResultStore) -> None:
        self._result_store = result_store

    def run_offline_stage(
        self,
        *,
        stage_key: StageKey,
        runtime: OfflineStageRuntime[RuntimeInput],
        input_payload: RuntimeInput,
        stage_config: StageConfig,
        config_hash: str,
        input_fingerprint: str,
        on_stage_started: StageStartedCallback | None = None,
        on_stage_completed: StageCompletedCallback | None = None,
        on_stage_failed: StageFailedCallback | None = None,
    ) -> StageResult:
        """Invoke one bounded stage runtime and store its result."""
        if on_stage_started is not None:
            on_stage_started(stage_key)
        try:
            result = runtime.run_offline(input_payload)
        except Exception as exc:
            outcome = stage_config.failure_outcome(
                error_message=str(exc),
                config_hash=config_hash,
                input_fingerprint=input_fingerprint,
            )
            if on_stage_failed is not None:
                on_stage_failed(stage_key, outcome)
            raise
        self._result_store.put(result)
        if on_stage_completed is not None:
            on_stage_completed(stage_key, result)
        return result

    def start_streaming_stage(
        self,
        *,
        stage_key: StageKey,
        runtime: StreamingStageRuntime[RuntimeInput, StreamItem],
        input_payload: RuntimeInput,
        on_stage_started: StageStartedCallback | None = None,
    ) -> None:
        """Start one streaming-capable stage runtime."""
        if on_stage_started is not None:
            on_stage_started(stage_key)
        runtime.start_streaming(input_payload)

    def submit_stream_item(
        self,
        *,
        runtime: StreamingStageRuntime[RuntimeInput, StreamItem],
        item: StreamItem,
    ) -> None:
        """Submit one hot-path item to a streaming runtime."""
        runtime.submit_stream_item(item)

    def finish_streaming_stage(
        self,
        *,
        stage_key: StageKey,
        runtime: StreamingStageRuntime[RuntimeInput, StreamItem],
        on_stage_completed: StageCompletedCallback | None = None,
    ) -> StageResult:
        """Finalize one streaming-capable runtime and store its result."""
        result = runtime.finish_streaming()
        self._result_store.put(result)
        if on_stage_completed is not None:
            on_stage_completed(stage_key, result)
        return result


def stage_result_from_completion_payload(
    *,
    stage_key: StageKey,
    payload: StageCompletionPayload,
    final_runtime_status: StageRuntimeStatus | None = None,
) -> StageResult:
    """Project a current ``StageCompletionPayload`` into ``StageResult``."""
    # TODO(pipeline-refactor/WP-10): Remove this projection helper after all
    # stage runtimes return `StageResult` directly and no helper or actor
    # returns `StageCompletionPayload`.
    status = (
        _default_final_status(stage_key=stage_key, outcome=payload.outcome)
        if final_runtime_status is None
        else final_runtime_status
    )
    return StageResult(
        stage_key=stage_key,
        payload=_primary_payload(stage_key=stage_key, payload=payload),
        outcome=payload.outcome,
        final_runtime_status=status,
    )


def _default_final_status(*, stage_key: StageKey, outcome: StageOutcome) -> StageRuntimeStatus:
    return StageRuntimeStatus(
        stage_key=stage_key,
        lifecycle_state=outcome.status,
        last_error=outcome.error_message or None,
    )


def _primary_payload(*, stage_key: StageKey, payload: StageCompletionPayload) -> BaseData | None:
    # TODO(pipeline-refactor/WP-10): Remove this legacy payload selector after
    # all stage runtimes return `StageResult` directly and no helper or actor
    # returns `StageCompletionPayload`.
    if stage_key is StageKey.INGEST and payload.sequence_manifest is not None:
        return SourceStageOutput(
            sequence_manifest=payload.sequence_manifest,
            benchmark_inputs=payload.benchmark_inputs,
        )
    if payload.sequence_manifest is not None:
        return payload.sequence_manifest
    if payload.slam is not None:
        return payload.slam
    if payload.ground_alignment is not None:
        return payload.ground_alignment
    if payload.visualization is not None:
        return payload.visualization
    if payload.summary is not None:
        return payload.summary
    if payload.benchmark_inputs is not None:
        return payload.benchmark_inputs
    return None


__all__ = [
    "StageDependencyError",
    "StageRunner",
    "StageResultStore",
    "stage_result_from_completion_payload",
]
