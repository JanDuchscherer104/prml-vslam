"""Stage lifecycle helpers and runtime result storage."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from prml_vslam.interfaces import Observation
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.methods.stage.contracts import SlamStageOutput
from prml_vslam.pipeline.contracts.context import PipelineExecutionContext
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint, StageConfig
from prml_vslam.pipeline.stages.base.contracts import StageResult
from prml_vslam.pipeline.stages.base.protocols import OfflineStageRuntime, StreamingStageRuntime
from prml_vslam.pipeline.stages.base.spec import StageRuntimeSpec
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.sources.stage.contracts import SourceStageOutput
from prml_vslam.utils import BaseData
from prml_vslam.utils.serialization import stable_hash

RuntimeInput = BaseData
StreamItem = BaseData | Observation
StageStartedCallback = Callable[[StageKey], None]
StageCompletedCallback = Callable[[StageKey, StageResult], None]
StageFailedCallback = Callable[[StageKey, StageOutcome], None]
StageResultTransform = Callable[[StageResult], StageResult]
TPayload = TypeVar("TPayload", bound=BaseData)


class StageDependencyError(RuntimeError):
    """Raised when a downstream stage requests an unavailable result payload."""


class StageResultStore:
    """Store completed stage results by stage key for downstream input builders.

    The store replaces broad mutable handoff bags with one keyed result map.
    It may expose common accessors for shared payloads such as
    :class:`prml_vslam.sources.contracts.SequenceManifest` and
    :class:`prml_vslam.interfaces.slam.SlamArtifacts`, but individual stage
    modules remain responsible for building their own stage-specific input DTOs.
    """

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

    def require_payload(self, stage_key: StageKey, payload_type: type[TPayload]) -> TPayload:
        """Return a completed stage payload of the requested type."""
        payload = self.require_result(stage_key).payload
        if isinstance(payload, payload_type):
            return payload
        payload_name = "None" if payload is None else type(payload).__name__
        raise StageDependencyError(
            f"Stage '{stage_key.value}' did not produce payload type '{payload_type.__name__}'; got '{payload_name}'."
        )

    def require_source_output(self) -> SourceStageOutput:
        """Return the typed source-stage output bundle."""
        return self.require_payload(StageKey.SOURCE, SourceStageOutput)

    def require_sequence_manifest(self) -> SequenceManifest:
        """Return the normalized source manifest from completed stage results."""
        result = self._results.get(StageKey.SOURCE)
        if result is not None and isinstance(result.payload, SourceStageOutput):
            return result.payload.sequence_manifest
        if result is not None and isinstance(result.payload, SequenceManifest):
            return result.payload
        raise StageDependencyError("Missing SequenceManifest from ingest/source stage result.")

    def require_benchmark_inputs(self) -> PreparedBenchmarkInputs | None:
        """Return prepared benchmark inputs when the source stage produced them."""
        result = self._results.get(StageKey.SOURCE)
        if result is not None and isinstance(result.payload, SourceStageOutput):
            return result.payload.benchmark_inputs
        if result is not None and isinstance(result.payload, PreparedBenchmarkInputs):
            return result.payload
        return None

    def require_slam_artifacts(self) -> SlamArtifacts:
        """Return normalized SLAM artifacts from completed stage results."""
        return self.require_slam_output().artifacts

    def require_slam_output(self) -> SlamStageOutput:
        """Return the typed SLAM-stage output bundle."""
        return self.require_payload(StageKey.SLAM, SlamStageOutput)

    def ordered_outcomes(self) -> list[StageOutcome]:
        """Return terminal outcomes in first-completion order."""
        return [self._results[stage_key].outcome for stage_key in self._ordered_stage_keys]


class StageRunner:
    """Own generic stage lifecycle around capability protocol calls.

    ``StageRunner`` handles start/completion/failure callbacks, converts
    exceptions into failed :class:`prml_vslam.pipeline.contracts.events.StageOutcome`
    values through the stage config, and stores successful
    :class:`prml_vslam.pipeline.stages.base.contracts.StageResult` objects. It
    deliberately does not know how to build source, SLAM, alignment, or
    evaluation inputs.
    """

    def __init__(self, result_store: StageResultStore) -> None:
        self._result_store = result_store

    def failure_hash_inputs(
        self,
        *,
        stage_config: StageConfig,
        stage_spec: StageRuntimeSpec,
        context: PipelineExecutionContext,
    ) -> tuple[str, str]:
        """Return stable failure-provenance hashes for one configured stage."""
        if stage_spec.failure_fingerprint is None:
            fingerprint = _default_failure_fingerprint(stage_config=stage_config, context=context)
        else:
            fingerprint = stage_spec.failure_fingerprint(context)
        return stable_hash(fingerprint.config_payload), stable_hash(fingerprint.input_payload)

    def run_configured_offline_stage(
        self,
        *,
        stage_key: StageKey,
        runtime: OfflineStageRuntime[RuntimeInput],
        stage_config: StageConfig,
        stage_spec: StageRuntimeSpec,
        context: PipelineExecutionContext,
        on_stage_started: StageStartedCallback | None = None,
        on_stage_completed: StageCompletedCallback | None = None,
        on_stage_failed: StageFailedCallback | None = None,
        transform_result: StageResultTransform | None = None,
    ) -> StageResult:
        """Build input, invoke one configured bounded stage, and store its result."""
        if stage_spec.build_offline_input is None:
            raise RuntimeError(f"Stage '{stage_key.value}' has no offline input builder.")
        config_hash, input_fingerprint = self.failure_hash_inputs(
            stage_config=stage_config,
            stage_spec=stage_spec,
            context=context,
        )
        return self.run_offline_stage(
            stage_key=stage_key,
            runtime=runtime,
            input_payload=stage_spec.build_offline_input(context),
            stage_config=stage_config,
            config_hash=config_hash,
            input_fingerprint=input_fingerprint,
            on_stage_started=on_stage_started,
            on_stage_completed=on_stage_completed,
            on_stage_failed=on_stage_failed,
            transform_result=transform_result,
        )

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
        transform_result: StageResultTransform | None = None,
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
        if transform_result is not None:
            result = transform_result(result)
        self._result_store.put(result)
        if on_stage_completed is not None:
            on_stage_completed(stage_key, result)
        return result

    def start_configured_streaming_stage(
        self,
        *,
        stage_key: StageKey,
        runtime: StreamingStageRuntime[RuntimeInput, StreamItem],
        stage_config: StageConfig,
        stage_spec: StageRuntimeSpec,
        context: PipelineExecutionContext,
        on_stage_started: StageStartedCallback | None = None,
        on_stage_failed: StageFailedCallback | None = None,
    ) -> None:
        """Build start input and start one configured streaming stage."""
        if stage_spec.build_streaming_start_input is None:
            raise RuntimeError(f"Stage '{stage_key.value}' has no streaming-start input builder.")
        config_hash, input_fingerprint = self.failure_hash_inputs(
            stage_config=stage_config,
            stage_spec=stage_spec,
            context=context,
        )
        try:
            self.start_streaming_stage(
                stage_key=stage_key,
                runtime=runtime,
                input_payload=stage_spec.build_streaming_start_input(context),
                on_stage_started=on_stage_started,
            )
        except Exception as exc:
            if on_stage_failed is not None:
                on_stage_failed(
                    stage_key,
                    stage_config.failure_outcome(
                        error_message=str(exc),
                        config_hash=config_hash,
                        input_fingerprint=input_fingerprint,
                    ),
                )
            raise

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


def _default_failure_fingerprint(
    *,
    stage_config: StageConfig,
    context: PipelineExecutionContext,
) -> FailureFingerprint:
    stage_key = stage_config.stage_key.value if stage_config.stage_key is not None else "unknown"
    return FailureFingerprint(
        config_payload={"stage_key": stage_key},
        input_payload={"run_id": context.plan.run_id, "stage_key": stage_key},
    )


__all__ = [
    "StageDependencyError",
    "StageRunner",
    "StageResultStore",
]
