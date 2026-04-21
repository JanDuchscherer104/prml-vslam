"""Phase-aware stage executor for the linear Ray-backed pipeline.

This module contains the stage-runtime bindings that decide whether a planned
stage runs during offline execution, streaming prepare, or streaming finalize.
It keeps stage order aligned with the compiled :class:`RunPlan` instead of
letting the coordinator hardcode stage sequencing itself.
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any, Protocol

from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.slam import ArtifactRef, SlamArtifacts
from prml_vslam.interfaces.visualization import VisualizationArtifacts
from prml_vslam.pipeline.contracts.events import StageOutcome, StageStatus
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.provenance import RunSummary, StageManifest
from prml_vslam.pipeline.contracts.request import PipelineMode
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.pipeline.ray_runtime.stage_execution import (
    StageExecutionContext,
    run_ground_alignment_stage,
    run_ingest_stage,
    run_offline_slam_stage,
    run_reference_reconstruction_stage,
    run_summary_stage,
    run_trajectory_evaluation_stage,
)
from prml_vslam.protocols.source import OfflineSequenceSource, StreamingSequenceSource


@dataclass(slots=True)
class RuntimeExecutionState:
    """Mutable cross-stage state accumulated during one run.

    Attributes:
        sequence_manifest: Normalized ingest boundary once ingest succeeds.
        benchmark_inputs: Prepared benchmark-side reference data, when the
            source provides it.
        slam: Normalized SLAM outputs once the SLAM stage completes.
        visualization: Optional viewer-owned artifacts emitted by the backend.
        stage_outcomes: Terminal outcomes in execution order. This list is the
            direct input to :func:`project_summary`.
    """

    sequence_manifest: SequenceManifest | None = None
    benchmark_inputs: PreparedBenchmarkInputs | None = None
    slam: SlamArtifacts | None = None
    ground_alignment: GroundAlignmentMetadata | None = None
    visualization: VisualizationArtifacts | None = None
    stage_outcomes: list[StageOutcome] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class StageCompletionPayload:
    """Bundle returned by one successful stage implementation.

    The payload carries the terminal :class:`StageOutcome` plus any typed state
    that downstream stages or the projected snapshot need to retain.
    """

    outcome: StageOutcome
    sequence_manifest: SequenceManifest | None = None
    benchmark_inputs: PreparedBenchmarkInputs | None = None
    slam: SlamArtifacts | None = None
    ground_alignment: GroundAlignmentMetadata | None = None
    visualization: VisualizationArtifacts | None = None
    summary: RunSummary | None = None
    stage_manifests: list[StageManifest] = field(default_factory=list)


class RuntimeStageDriver(Protocol):
    """Coordinator-facing hooks required by streaming-capable stage execution."""

    stop_requested: bool
    streaming_error: str | None

    @abstractmethod
    def start_streaming_slam_stage(self, *, context: StageExecutionContext) -> None:
        """Construct and start the ordered streaming SLAM stage."""
        ...

    @abstractmethod
    def close_streaming_slam_stage(
        self,
        *,
        context: StageExecutionContext,
        sequence_manifest: SequenceManifest,
    ) -> StageCompletionPayload:
        """Close the ordered streaming SLAM stage and return its completion payload."""
        ...


OfflineStageFn = Callable[
    [StageExecutionContext, RuntimeExecutionState, OfflineSequenceSource, RuntimeStageDriver],
    StageCompletionPayload,
]
StreamingPrepareStageFn = Callable[
    [StageExecutionContext, RuntimeExecutionState, StreamingSequenceSource, RuntimeStageDriver],
    StageCompletionPayload | None,
]
StreamingFinalizeStageFn = Callable[
    [StageExecutionContext, RuntimeExecutionState, RuntimeStageDriver],
    StageCompletionPayload,
]
FailureOutcomeFn = Callable[
    [StageExecutionContext, RuntimeExecutionState, str, Mapping[str, ArtifactRef] | None],
    StageOutcome,
]


@dataclass(frozen=True, slots=True)
class StageRuntimeSpec:
    """Bind one :class:`StageKey` to its executable runtime entrypoints."""

    key: StageKey
    run_offline: OfflineStageFn | None = None
    run_streaming_prepare: StreamingPrepareStageFn | None = None
    run_streaming_finalize: StreamingFinalizeStageFn | None = None
    build_failure_outcome: FailureOutcomeFn | None = None


StageInvokeFn = Callable[[StageRuntimeSpec], StageCompletionPayload | None]
StageSkipFn = Callable[[StageRuntimeSpec], bool]


class RuntimeStageProgram:
    """Execute planned stages in offline and streaming-specific phases."""

    def __init__(self, specs: list[StageRuntimeSpec]) -> None:
        self._specs = {spec.key: spec for spec in specs}

    @classmethod
    def default(cls) -> RuntimeStageProgram:
        """Build the repository-owned runtime bindings for executable stages."""
        return cls(
            [
                StageRuntimeSpec(
                    key=StageKey.INGEST,
                    run_offline=_run_ingest,
                    run_streaming_prepare=_run_ingest,
                    build_failure_outcome=_failure_builder(
                        stage_key=StageKey.INGEST,
                        config_payload=lambda context, state: context.request.source,
                        input_payload=lambda context, state: context.request.source,
                    ),
                ),
                StageRuntimeSpec(
                    key=StageKey.SLAM,
                    run_offline=_run_slam_offline,
                    run_streaming_prepare=_run_slam_streaming_prepare,
                    run_streaming_finalize=_run_slam_streaming_finalize,
                    build_failure_outcome=_failure_builder(
                        stage_key=StageKey.SLAM,
                        config_payload=lambda context, state: context.request.slam,
                        input_payload=lambda context, state: state.sequence_manifest
                        if state.sequence_manifest is not None
                        else {"run_id": context.plan.run_id, "stage_key": StageKey.SLAM.value},
                    ),
                ),
                StageRuntimeSpec(
                    key=StageKey.GROUND_ALIGNMENT,
                    run_offline=_run_ground_alignment,
                    run_streaming_finalize=_run_ground_alignment,
                    build_failure_outcome=_failure_builder(
                        stage_key=StageKey.GROUND_ALIGNMENT,
                        config_payload=lambda context, state: context.request.alignment.ground,
                        input_payload=lambda _context, state: {
                            "trajectory_tum": None if state.slam is None else state.slam.trajectory_tum,
                            "dense_points_ply": None if state.slam is None else state.slam.dense_points_ply,
                            "sparse_points_ply": None if state.slam is None else state.slam.sparse_points_ply,
                        },
                    ),
                ),
                StageRuntimeSpec(
                    key=StageKey.TRAJECTORY_EVALUATION,
                    run_offline=_run_trajectory,
                    run_streaming_finalize=_run_trajectory,
                    build_failure_outcome=_failure_builder(
                        stage_key=StageKey.TRAJECTORY_EVALUATION,
                        config_payload=lambda context, state: context.request.benchmark.trajectory,
                        input_payload=lambda context, state: {
                            "benchmark_inputs": state.benchmark_inputs,
                            "slam_trajectory": None if state.slam is None else state.slam.trajectory_tum,
                        },
                    ),
                ),
                StageRuntimeSpec(
                    key=StageKey.REFERENCE_RECONSTRUCTION,
                    run_offline=_run_reference_reconstruction,
                    run_streaming_finalize=_run_reference_reconstruction,
                    build_failure_outcome=_failure_builder(
                        stage_key=StageKey.REFERENCE_RECONSTRUCTION,
                        config_payload=lambda context, state: context.request.benchmark.reference,
                        input_payload=lambda _context, state: state.benchmark_inputs,
                    ),
                ),
                StageRuntimeSpec(
                    key=StageKey.SUMMARY,
                    run_offline=_run_summary,
                    run_streaming_finalize=_run_summary,
                    build_failure_outcome=_failure_builder(
                        stage_key=StageKey.SUMMARY,
                        config_payload=lambda context, state: {
                            "experiment_name": context.request.experiment_name,
                            "mode": context.request.mode.value,
                        },
                        input_payload=lambda context, state: state.stage_outcomes,
                    ),
                ),
            ]
        )

    def execute_offline(
        self,
        *,
        plan: RunPlan,
        context: StageExecutionContext,
        state: RuntimeExecutionState,
        source: OfflineSequenceSource,
        driver: RuntimeStageDriver,
        emit_stage_started: Callable[[StageKey], None],
        record_stage_completion: Callable[[StageKey, StageCompletionPayload], None],
        record_stage_failure: Callable[[StageKey, StageOutcome], None],
    ) -> None:
        """Execute all offline-capable planned stages in plan order."""
        self._execute_phase(
            plan=plan,
            context=context,
            state=state,
            emit_stage_started=emit_stage_started,
            record_stage_completion=record_stage_completion,
            record_stage_failure=record_stage_failure,
            should_skip=lambda spec: spec.run_offline is None
            or (spec.key is StageKey.TRAJECTORY_EVALUATION and driver.stop_requested),
            invoke=lambda spec: spec.run_offline(context, state, source, driver),
        )

    def execute_streaming_prepare(
        self,
        *,
        plan: RunPlan,
        context: StageExecutionContext,
        state: RuntimeExecutionState,
        source: StreamingSequenceSource,
        driver: RuntimeStageDriver,
        emit_stage_started: Callable[[StageKey], None],
        record_stage_completion: Callable[[StageKey, StageCompletionPayload], None],
        record_stage_failure: Callable[[StageKey, StageOutcome], None],
    ) -> None:
        """Execute the non-hot-path prefix of a streaming run."""
        self._execute_phase(
            plan=plan,
            context=context,
            state=state,
            emit_stage_started=emit_stage_started,
            record_stage_completion=record_stage_completion,
            record_stage_failure=record_stage_failure,
            should_skip=lambda spec: spec.run_streaming_prepare is None,
            invoke=lambda spec: spec.run_streaming_prepare(context, state, source, driver),
        )

    def execute_streaming_finalize(
        self,
        *,
        plan: RunPlan,
        context: StageExecutionContext,
        state: RuntimeExecutionState,
        driver: RuntimeStageDriver,
        emit_stage_started: Callable[[StageKey], None],
        record_stage_completion: Callable[[StageKey, StageCompletionPayload], None],
        record_stage_failure: Callable[[StageKey, StageOutcome], None],
    ) -> None:
        """Execute the post-stream suffix of a streaming run."""
        self._execute_phase(
            plan=plan,
            context=context,
            state=state,
            emit_stage_started=emit_stage_started,
            record_stage_completion=record_stage_completion,
            record_stage_failure=record_stage_failure,
            should_skip=lambda spec: spec.run_streaming_finalize is None
            or (
                spec.key is StageKey.TRAJECTORY_EVALUATION
                and (driver.streaming_error is not None or driver.stop_requested)
            ),
            invoke=lambda spec: spec.run_streaming_finalize(context, state, driver),
        )

    def _ordered_specs(self, plan: RunPlan) -> list[StageRuntimeSpec]:
        ordered: list[StageRuntimeSpec] = []
        for stage in plan.stages:
            if not stage.available:
                continue
            spec = self._specs.get(stage.key)
            if spec is None:
                raise RuntimeError(f"Missing runtime stage spec for available stage '{stage.key.value}'.")
            if plan.mode is PipelineMode.OFFLINE and spec.run_offline is None:
                raise RuntimeError(f"Stage '{stage.key.value}' has no offline runtime implementation.")
            if (
                plan.mode is PipelineMode.STREAMING
                and spec.run_streaming_prepare is None
                and spec.run_streaming_finalize is None
            ):
                raise RuntimeError(f"Stage '{stage.key.value}' has no streaming runtime implementation.")
            ordered.append(spec)
        return ordered

    @staticmethod
    def _execute_stage(
        *,
        spec: StageRuntimeSpec,
        context: StageExecutionContext,
        state: RuntimeExecutionState,
        emit_stage_started: Callable[[StageKey], None],
        record_stage_completion: Callable[[StageKey, StageCompletionPayload], None],
        record_stage_failure: Callable[[StageKey, StageOutcome], None],
        invoke: Callable[[], StageCompletionPayload | None],
    ) -> None:
        emit_stage_started(spec.key)
        try:
            payload = invoke()
        except Exception as exc:
            if spec.build_failure_outcome is None:
                raise
            outcome = spec.build_failure_outcome(context, state, str(exc), None)
            state.stage_outcomes.append(outcome)
            record_stage_failure(spec.key, outcome)
            raise
        if payload is None:
            return
        if payload.outcome.status is StageStatus.FAILED:
            state.stage_outcomes.append(payload.outcome)
            record_stage_failure(spec.key, payload.outcome)
            return
        _apply_completion(state, payload)
        record_stage_completion(spec.key, payload)

    def _execute_phase(
        self,
        *,
        plan: RunPlan,
        context: StageExecutionContext,
        state: RuntimeExecutionState,
        emit_stage_started: Callable[[StageKey], None],
        record_stage_completion: Callable[[StageKey, StageCompletionPayload], None],
        record_stage_failure: Callable[[StageKey, StageOutcome], None],
        should_skip: StageSkipFn,
        invoke: StageInvokeFn,
    ) -> None:
        for spec in self._ordered_specs(plan):
            if should_skip(spec):
                continue
            self._execute_stage(
                spec=spec,
                context=context,
                state=state,
                emit_stage_started=emit_stage_started,
                record_stage_completion=record_stage_completion,
                record_stage_failure=record_stage_failure,
                invoke=lambda current_spec=spec: invoke(current_spec),
            )


def _run_ingest(
    context: StageExecutionContext,
    _state: RuntimeExecutionState,
    source: OfflineSequenceSource,
    _driver: RuntimeStageDriver,
) -> StageCompletionPayload:
    return run_ingest_stage(context=context, source=source)


def _run_slam_offline(
    context: StageExecutionContext,
    state: RuntimeExecutionState,
    _source: OfflineSequenceSource,
    _driver: RuntimeStageDriver,
) -> StageCompletionPayload:
    return run_offline_slam_stage(
        context=context,
        sequence_manifest=_require_sequence_manifest(state),
        benchmark_inputs=state.benchmark_inputs,
    )


def _run_slam_streaming_prepare(
    context: StageExecutionContext,
    _state: RuntimeExecutionState,
    _source: StreamingSequenceSource,
    driver: RuntimeStageDriver,
) -> None:
    driver.start_streaming_slam_stage(context=context)
    return None


def _run_slam_streaming_finalize(
    context: StageExecutionContext,
    state: RuntimeExecutionState,
    driver: RuntimeStageDriver,
) -> StageCompletionPayload:
    payload = driver.close_streaming_slam_stage(
        context=context,
        sequence_manifest=_require_sequence_manifest(state),
    )
    if driver.streaming_error is not None:
        return replace(
            payload,
            outcome=_failure_builder(
                stage_key=StageKey.SLAM,
                config_payload=lambda current_context, current_state: current_context.request.slam,
                input_payload=lambda current_context, current_state: current_state.sequence_manifest
                if current_state.sequence_manifest is not None
                else {"run_id": current_context.plan.run_id, "stage_key": StageKey.SLAM.value},
            )(context, state, driver.streaming_error, payload.outcome.artifacts),
        )
    if driver.stop_requested:
        return replace(payload, outcome=payload.outcome.model_copy(update={"status": StageStatus.STOPPED}))
    return payload


def _run_trajectory(
    context: StageExecutionContext,
    state: RuntimeExecutionState,
    _source_or_driver: OfflineSequenceSource | RuntimeStageDriver,
    _driver: RuntimeStageDriver | None = None,
) -> StageCompletionPayload:
    return run_trajectory_evaluation_stage(
        context=context,
        sequence_manifest=_require_sequence_manifest(state),
        benchmark_inputs=state.benchmark_inputs,
        slam=_require_slam_artifacts(state),
    )


def _run_ground_alignment(
    context: StageExecutionContext,
    state: RuntimeExecutionState,
    _source_or_driver: OfflineSequenceSource | RuntimeStageDriver,
    _driver: RuntimeStageDriver | None = None,
) -> StageCompletionPayload:
    return run_ground_alignment_stage(
        context=context,
        slam=_require_slam_artifacts(state),
    )


def _run_reference_reconstruction(
    context: StageExecutionContext,
    state: RuntimeExecutionState,
    _source_or_driver: OfflineSequenceSource | RuntimeStageDriver,
    _driver: RuntimeStageDriver | None = None,
) -> StageCompletionPayload:
    return run_reference_reconstruction_stage(
        context=context,
        benchmark_inputs=state.benchmark_inputs,
    )


def _run_summary(
    context: StageExecutionContext,
    state: RuntimeExecutionState,
    _source_or_driver: OfflineSequenceSource | RuntimeStageDriver,
    _driver: RuntimeStageDriver | None = None,
) -> StageCompletionPayload:
    return run_summary_stage(context=context, stage_outcomes=list(state.stage_outcomes))


def _apply_completion(state: RuntimeExecutionState, payload: StageCompletionPayload) -> None:
    state.stage_outcomes.append(payload.outcome)
    if payload.sequence_manifest is not None:
        state.sequence_manifest = payload.sequence_manifest
    if payload.benchmark_inputs is not None:
        state.benchmark_inputs = payload.benchmark_inputs
    if payload.slam is not None:
        state.slam = payload.slam
    if payload.ground_alignment is not None:
        state.ground_alignment = payload.ground_alignment
    if payload.visualization is not None:
        state.visualization = payload.visualization


def _failure_builder(
    *,
    stage_key: StageKey,
    config_payload: Callable[[StageExecutionContext, RuntimeExecutionState], Any],
    input_payload: Callable[[StageExecutionContext, RuntimeExecutionState], Any],
) -> FailureOutcomeFn:
    def _build(
        context: StageExecutionContext,
        state: RuntimeExecutionState,
        error_message: str,
        artifacts: Mapping[str, ArtifactRef] | None,
    ) -> StageOutcome:
        return StageOutcome(
            stage_key=stage_key,
            status=StageStatus.FAILED,
            config_hash=stable_hash(config_payload(context, state)),
            input_fingerprint=stable_hash(input_payload(context, state)),
            artifacts=dict(artifacts or {}),
            error_message=error_message,
        )

    return _build


def _require_sequence_manifest(state: RuntimeExecutionState) -> SequenceManifest:
    if state.sequence_manifest is None:
        raise RuntimeError("Sequence manifest is not available.")
    return state.sequence_manifest


def _require_slam_artifacts(state: RuntimeExecutionState) -> SlamArtifacts:
    if state.slam is None:
        raise RuntimeError("SLAM artifacts are not available.")
    return state.slam


__all__ = [
    "RuntimeExecutionState",
    "RuntimeStageProgram",
    "RuntimeStageDriver",
    "StageCompletionPayload",
    "StageRuntimeSpec",
]
