"""SLAM stage binding."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.binding import (
    FailureFingerprint,
    PlanContext,
    RuntimeBuildContext,
    StageBinding,
    StageInputContext,
)
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime
from prml_vslam.pipeline.stages.base.proxy import RuntimeCapability
from prml_vslam.pipeline.stages.slam.config import MethodId
from prml_vslam.pipeline.stages.slam.contracts import SlamOfflineInput, SlamStreamingStartInput


class SlamStageBinding(StageBinding):
    """Bind SLAM config to planning, runtime construction, and inputs."""

    key = StageKey.SLAM
    section_name = "slam"

    def planned_outputs(self, context: PlanContext) -> list[Path]:
        """Return SLAM-owned output artifacts."""
        slam_backend = context.run_config.stages.slam.backend
        if slam_backend is None:
            return []
        run_paths = context.run_paths
        artifact_paths = [run_paths.trajectory_path]
        if slam_backend.method_id is MethodId.VISTA:
            if context.run_config.stages.slam.outputs.emit_sparse_points or (
                context.run_config.stages.slam.outputs.emit_dense_points
            ):
                artifact_paths.append(run_paths.point_cloud_path)
            return artifact_paths
        if context.run_config.stages.slam.outputs.emit_sparse_points:
            artifact_paths.append(run_paths.sparse_points_path)
        if context.run_config.stages.slam.outputs.emit_dense_points:
            artifact_paths.append(run_paths.dense_points_path)
        return artifact_paths

    def availability(self, context: PlanContext) -> tuple[bool, str | None]:
        """Return whether the selected backend can execute in the selected mode."""
        slam_backend = context.run_config.stages.slam.backend
        if slam_backend is None:
            return False, "SLAM stage requires `[stages.slam.backend]`."
        descriptor = context.backend if context.backend is not None else slam_backend.describe()
        if context.run_config.mode is PipelineMode.OFFLINE and not descriptor.capabilities.offline:
            return False, f"{descriptor.display_name} does not support offline execution."
        if context.run_config.mode is PipelineMode.STREAMING and not descriptor.capabilities.streaming:
            return False, f"{descriptor.display_name} does not support streaming execution."
        return True, None

    def runtime_factory(self, context: RuntimeBuildContext) -> Callable[[], BaseStageRuntime]:
        """Return a lazy SLAM runtime factory."""
        del context
        from prml_vslam.pipeline.stages.slam.runtime import SlamStageRuntime

        return SlamStageRuntime

    def runtime_capabilities(self, mode: PipelineMode) -> frozenset[RuntimeCapability]:
        """Return capabilities exposed by the SLAM runtime."""
        if mode is PipelineMode.STREAMING:
            return frozenset({RuntimeCapability.OFFLINE, RuntimeCapability.LIVE_UPDATES, RuntimeCapability.STREAMING})
        return frozenset({RuntimeCapability.OFFLINE})

    def build_offline_input(self, context: StageInputContext) -> SlamOfflineInput:
        """Build the narrow offline SLAM input DTO."""
        slam_config = context.run_config.stages.slam
        if slam_config.backend is None:
            raise RuntimeError("SLAM runtime requires `[stages.slam.backend]`.")
        return SlamOfflineInput(
            backend=slam_config.backend,
            outputs=slam_config.outputs,
            artifact_root=context.plan.artifact_root,
            path_config=context.path_config,
            baseline_source=context.run_config.stages.evaluate_trajectory.evaluation.baseline_source,
            sequence_manifest=context.results.require_sequence_manifest(),
            benchmark_inputs=context.results.require_benchmark_inputs(),
            preserve_native_rerun=context.run_config.visualization.preserve_native_rerun,
        )

    def build_streaming_start_input(self, context: StageInputContext) -> SlamStreamingStartInput:
        """Build the narrow streaming-start SLAM input DTO."""
        slam_config = context.run_config.stages.slam
        if slam_config.backend is None:
            raise RuntimeError("SLAM runtime requires `[stages.slam.backend]`.")
        return SlamStreamingStartInput(
            backend=slam_config.backend,
            outputs=slam_config.outputs,
            artifact_root=context.plan.artifact_root,
            path_config=context.path_config,
            sequence_manifest=context.results.require_sequence_manifest(),
            benchmark_inputs=context.results.require_benchmark_inputs(),
            baseline_source=context.run_config.stages.evaluate_trajectory.evaluation.baseline_source,
            log_diagnostic_preview=context.run_config.visualization.log_diagnostic_preview,
            preserve_native_rerun=context.run_config.visualization.preserve_native_rerun,
        )

    def failure_fingerprint(self, context: StageInputContext) -> FailureFingerprint:
        """Return SLAM config and normalized sequence fingerprint payloads."""
        return FailureFingerprint(
            config_payload=context.run_config.stages.slam,
            input_payload=context.results.require_sequence_manifest(),
        )


__all__ = ["SlamStageBinding"]
