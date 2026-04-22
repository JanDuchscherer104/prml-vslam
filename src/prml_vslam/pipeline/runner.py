"""Stage lifecycle helpers and runtime result storage."""

from __future__ import annotations

from collections.abc import Callable

from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest, SourceStageOutput
from prml_vslam.interfaces.runtime import FramePacket
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.pipeline.stages.base.contracts import StageResult
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
    """Store completed stage results by stage key."""

    def __init__(self) -> None:
        self._results: dict[StageKey, StageResult] = {}
        self._ordered_stage_keys: list[StageKey] = []

    def put(self, result: StageResult) -> None:
        """Store one completed target result."""
        if result.stage_key not in self._results:
            self._ordered_stage_keys.append(result.stage_key)
        self._results[result.stage_key] = result

    def require_result(self, stage_key: StageKey) -> StageResult:
        """Return the completed result for ``stage_key`` or fail clearly."""
        try:
            return self._results[stage_key]
        except KeyError as exc:
            raise StageDependencyError(f"Missing result for stage '{stage_key.value}'.") from exc

    def require_sequence_manifest(self) -> SequenceManifest:
        """Return the normalized source manifest from completed stage results."""
        result = self._results.get(StageKey.INGEST)
        if result is not None and isinstance(result.payload, SourceStageOutput):
            return result.payload.sequence_manifest
        if result is not None and isinstance(result.payload, SequenceManifest):
            return result.payload
        raise StageDependencyError("Missing SequenceManifest from ingest/source stage result.")

    def require_benchmark_inputs(self) -> PreparedBenchmarkInputs | None:
        """Return prepared benchmark inputs when the source stage produced them."""
        result = self._results.get(StageKey.INGEST)
        if result is not None and isinstance(result.payload, SourceStageOutput):
            return result.payload.benchmark_inputs
        if result is not None and isinstance(result.payload, PreparedBenchmarkInputs):
            return result.payload
        return None

    def require_slam_artifacts(self) -> SlamArtifacts:
        """Return normalized SLAM artifacts from completed stage results."""
        result = self._results.get(StageKey.SLAM)
        if result is not None and isinstance(result.payload, SlamArtifacts):
            return result.payload
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


__all__ = [
    "StageDependencyError",
    "StageRunner",
    "StageResultStore",
]
