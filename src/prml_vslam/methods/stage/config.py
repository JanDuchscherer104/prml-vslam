"""Persisted SLAM stage config and backend muxing.

The SLAM stage owns the public backend discriminator, output policy, and
config-as-factory variants used by pipeline launch. Concrete method adapters
remain in :mod:`prml_vslam.methods`; stage configs import those implementations
only when ``setup_target(...)`` is called so heavy resources are created in the
execution process.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal, TypeAlias

from pydantic import ConfigDict, Field

from prml_vslam.pipeline.contracts.context import PipelineExecutionContext, PipelinePlanContext
from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint, StageConfig
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime
from prml_vslam.utils import BaseConfig, FactoryConfig, PathConfig

if TYPE_CHECKING:
    from prml_vslam.methods.mast3r import Mast3rSlamBackend
    from prml_vslam.methods.vista.adapter import VistaSlamBackend


class MethodId(StrEnum):
    """Name the SLAM backends exposed by the pipeline stage config."""

    VISTA = "vista"
    MAST3R = "mast3r"

    @property
    def display_name(self) -> str:
        """Return the upstream method name shown to users."""
        match self:
            case MethodId.VISTA:
                return "ViSTA-SLAM"
            case MethodId.MAST3R:
                return "MASt3R-SLAM"


class SlamOutputPolicy(BaseConfig):
    """Describe optional SLAM geometry materialization."""

    model_config = ConfigDict(extra="ignore")

    emit_dense_points: bool = True
    """Whether the backend should materialize a dense point cloud artifact."""

    emit_sparse_points: bool = True
    """Whether the backend should materialize sparse geometry artifacts."""


class SlamBackendConfig(BaseConfig):
    """Base for concrete stage-owned SLAM backend variants."""

    model_config = ConfigDict(extra="ignore")

    method_id: MethodId | None = None
    """Stable backend discriminator used by the stage-owned union."""

    max_frames: int | None = None
    """Optional frame cap used for debugging or short smoke runs."""

    @property
    def display_name(self) -> str:
        """Return the user-facing backend label used by planning and UI surfaces."""
        if self.method_id is None:
            raise NotImplementedError("Concrete backend configs must define method_id.")
        return self.method_id.display_name

    @property
    def kind(self) -> str:
        """Return the backend discriminator string."""
        if self.method_id is None:
            raise NotImplementedError("Concrete backend configs must define method_id.")
        return self.method_id.value

    @property
    def supports_offline(self) -> bool:
        """Whether the backend supports offline execution."""
        raise NotImplementedError

    @property
    def supports_streaming(self) -> bool:
        """Whether the backend supports streaming execution."""
        raise NotImplementedError

    @property
    def supports_dense_points(self) -> bool:
        """Whether the backend can expose point-cloud outputs."""
        raise NotImplementedError

    @property
    def supports_live_preview(self) -> bool:
        """Whether the backend can emit live preview payloads."""
        raise NotImplementedError

    @property
    def supports_native_visualization(self) -> bool:
        """Whether the backend may emit native visualization artifacts."""
        raise NotImplementedError

    @property
    def supports_trajectory_benchmark(self) -> bool:
        """Whether the backend supports repository trajectory evaluation."""
        raise NotImplementedError

    @property
    def default_resources(self) -> dict[str, float]:
        """Return backend-owned default resource hints."""
        return {}

    @property
    def notes(self) -> list[str]:
        """Return backend-specific planning notes surfaced to callers."""
        return []


class Mast3rSlamBackendConfig(SlamBackendConfig, FactoryConfig["Mast3rSlamBackend"]):
    """Configure the placeholder MASt3R wrapper used for planning."""

    method_id: Literal[MethodId.MAST3R] = MethodId.MAST3R

    @property
    def supports_offline(self) -> bool:
        """Whether the backend supports offline execution."""
        return False

    @property
    def supports_streaming(self) -> bool:
        """Whether the backend supports streaming execution."""
        return False

    @property
    def supports_dense_points(self) -> bool:
        """Whether the backend can expose point-cloud outputs."""
        return False

    @property
    def supports_live_preview(self) -> bool:
        """Whether the backend can emit live preview payloads."""
        return False

    @property
    def supports_native_visualization(self) -> bool:
        """Whether the backend may emit native visualization artifacts."""
        return False

    @property
    def supports_trajectory_benchmark(self) -> bool:
        """Whether the backend supports repository trajectory evaluation."""
        return False

    @property
    def notes(self) -> list[str]:
        """Return backend-specific planning notes."""
        return ["MASt3R remains a placeholder backend in this repository."]

    @property
    def target_type(self) -> type[Mast3rSlamBackend]:
        """Return the placeholder backend type."""
        from prml_vslam.methods.mast3r import Mast3rSlamBackend

        return Mast3rSlamBackend

    def setup_target(self, **kwargs: Any) -> Mast3rSlamBackend:
        """Instantiate the placeholder backend in the execution process."""
        kwargs.pop("path_config", None)
        from prml_vslam.methods.mast3r import Mast3rSlamBackend

        return Mast3rSlamBackend(self)


class VistaSlamBackendConfig(SlamBackendConfig, FactoryConfig["VistaSlamBackend"]):
    """Configure the canonical ViSTA-SLAM backend."""

    method_id: Literal[MethodId.VISTA] = MethodId.VISTA
    vista_slam_dir: Path = Path("external/vista-slam")
    checkpoint_path: Path = Path("external/vista-slam/pretrains/frontend_sta_weights.pth")
    vocab_path: Path = Path("external/vista-slam/pretrains/ORBvoc.txt")
    max_view_num: int = 400
    flow_thres: float = 5.0
    neighbor_edge_num: int = 3
    loop_edge_num: int = 3
    loop_dist_min: int = 40
    loop_nms: int = 40
    loop_cand_thresh_neighbor: int = 5
    point_conf_thres: float = 4.2
    rel_pose_thres: float = 0.75
    pgo_every: int = 500
    random_seed: int = 43
    device: Literal["auto", "cuda", "cpu"] = "auto"

    @property
    def supports_offline(self) -> bool:
        """Whether the backend supports offline execution."""
        return True

    @property
    def supports_streaming(self) -> bool:
        """Whether the backend supports streaming execution."""
        return True

    @property
    def supports_dense_points(self) -> bool:
        """Whether the backend can expose point-cloud outputs."""
        return True

    @property
    def supports_live_preview(self) -> bool:
        """Whether the backend can emit live preview payloads."""
        return True

    @property
    def supports_native_visualization(self) -> bool:
        """Whether the backend may emit native visualization artifacts."""
        return True

    @property
    def supports_trajectory_benchmark(self) -> bool:
        """Whether the backend supports repository trajectory evaluation."""
        return True

    @property
    def default_resources(self) -> dict[str, float]:
        """Return backend-owned default resource hints."""
        return {"CPU": 2.0, "GPU": 1.0}

    @property
    def notes(self) -> list[str]:
        """Return backend-specific planning notes."""
        return ["GPU acceleration is recommended for real ViSTA runs."]

    @property
    def target_type(self) -> type[VistaSlamBackend]:
        """Return the backend type instantiated by ``setup_target``."""
        from prml_vslam.methods.vista.adapter import VistaSlamBackend

        return VistaSlamBackend

    def setup_target(self, *, path_config: PathConfig | None = None, **_kwargs: Any) -> VistaSlamBackend:
        """Instantiate the ViSTA backend in the execution process."""
        from prml_vslam.methods.vista.adapter import VistaSlamBackend

        return VistaSlamBackend(self, path_config=path_config)


BackendConfig: TypeAlias = Annotated[
    VistaSlamBackendConfig | Mast3rSlamBackendConfig,
    Field(discriminator="method_id"),
]


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


BackendConfigValue: TypeAlias = Path | str | int | float | bool | None


def build_slam_backend_config(
    *,
    method: MethodId,
    max_frames: int | None = None,
    overrides: dict[str, BackendConfigValue] | None = None,
) -> BackendConfig:
    """Build a typed backend config from a selected method and overrides."""
    backend_payload: dict[str, BackendConfigValue] = {"max_frames": max_frames}
    if overrides is not None:
        backend_payload.update(overrides)
    match method:
        case MethodId.VISTA:
            return VistaSlamBackendConfig.model_validate({"method_id": MethodId.VISTA, **backend_payload})
        case MethodId.MAST3R:
            return Mast3rSlamBackendConfig.model_validate({"method_id": MethodId.MAST3R, **backend_payload})


__all__ = [
    "BackendConfig",
    "BackendConfigValue",
    "Mast3rSlamBackendConfig",
    "MethodId",
    "SlamBackendConfig",
    "SlamOutputPolicy",
    "SlamStageConfig",
    "VistaSlamBackendConfig",
    "build_slam_backend_config",
]
