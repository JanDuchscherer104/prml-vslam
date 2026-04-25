"""Persisted SLAM stage policy."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import ConfigDict, Field

from prml_vslam.methods.stage.backend_config import BackendConfig, MethodId, SlamOutputPolicy
from prml_vslam.pipeline.contracts.context import PipelineExecutionContext, PipelinePlanContext
from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint, StageConfig
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime


class SlamStageConfig(StageConfig):
    """Persisted SLAM stage policy, backend selection, and output policy."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.SLAM
    backend: BackendConfig | None = None
    """Selected SLAM backend config."""

    outputs: SlamOutputPolicy = Field(default_factory=SlamOutputPolicy)
    """SLAM output materialization policy."""

    def planned_outputs(self, context: PipelinePlanContext) -> list[Path]:
        """Return SLAM-owned output artifacts."""
        if self.backend is None:
            return []
        run_paths = context.run_paths
        artifact_paths = [run_paths.trajectory_path]
        if self.backend.method_id is MethodId.VISTA:
            if self.outputs.emit_sparse_points or self.outputs.emit_dense_points:
                artifact_paths.append(run_paths.point_cloud_path)
            return artifact_paths
        if self.outputs.emit_sparse_points:
            artifact_paths.append(run_paths.sparse_points_path)
        if self.outputs.emit_dense_points:
            artifact_paths.append(run_paths.dense_points_path)
        return artifact_paths

    def availability(self, context: PipelinePlanContext) -> tuple[bool, str | None]:
        """Return whether the selected backend can execute in the selected mode."""
        if self.backend is None:
            return False, "SLAM stage requires `[stages.slam.backend]`."
        backend = context.slam_backend if context.slam_backend is not None else self.backend
        if context.run_config.mode is PipelineMode.OFFLINE and not backend.supports_offline:
            return False, f"{backend.display_name} does not support offline execution."
        if context.run_config.mode is PipelineMode.STREAMING and not backend.supports_streaming:
            return False, f"{backend.display_name} does not support streaming execution."
        return True, None

    def runtime_factory(self, context: PipelineExecutionContext) -> Callable[[], BaseStageRuntime]:
        """Return a lazy SLAM runtime factory."""
        del context
        from prml_vslam.methods.stage.runtime import SlamStageRuntime

        return SlamStageRuntime

    def build_offline_input(self, context: PipelineExecutionContext):
        """Build the narrow offline SLAM input DTO."""
        from prml_vslam.methods.stage.contracts import SlamOfflineStageInput

        if self.backend is None:
            raise RuntimeError("SLAM runtime requires `[stages.slam.backend]`.")
        return SlamOfflineStageInput(
            backend=self.backend,
            outputs=self.outputs,
            artifact_root=context.plan.artifact_root,
            path_config=context.path_config,
            baseline_source=context.run_config.stages.evaluate_trajectory.evaluation.baseline_source,
            sequence_manifest=context.results.require_sequence_manifest(),
            benchmark_inputs=context.results.require_benchmark_inputs(),
            preserve_native_rerun=context.run_config.visualization.preserve_native_rerun,
        )

    def build_streaming_start_input(self, context: PipelineExecutionContext):
        """Build the narrow streaming-start SLAM input DTO."""
        from prml_vslam.methods.stage.contracts import SlamStreamingStartStageInput

        if self.backend is None:
            raise RuntimeError("SLAM runtime requires `[stages.slam.backend]`.")
        return SlamStreamingStartStageInput(
            backend=self.backend,
            outputs=self.outputs,
            artifact_root=context.plan.artifact_root,
            path_config=context.path_config,
            sequence_manifest=context.results.require_sequence_manifest(),
            benchmark_inputs=context.results.require_benchmark_inputs(),
            baseline_source=context.run_config.stages.evaluate_trajectory.evaluation.baseline_source,
            log_diagnostic_preview=context.run_config.visualization.log_diagnostic_preview,
            preserve_native_rerun=context.run_config.visualization.preserve_native_rerun,
        )

    def failure_fingerprint(self, context: PipelineExecutionContext) -> FailureFingerprint:
        """Return SLAM config and normalized sequence fingerprint payloads."""
        return FailureFingerprint(config_payload=self, input_payload=context.results.require_sequence_manifest())


__all__ = ["SlamStageConfig"]
