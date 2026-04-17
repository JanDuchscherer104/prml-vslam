"""Pipeline-facing run facade for offline and streaming execution."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from prml_vslam.datasets.advio import AdvioDatasetService
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.methods import MockSlamBackendConfig, VistaSlamBackendConfig, Mast3rSlamBackendConfig
from prml_vslam.methods.contracts import MethodId, SlamBackendConfig
from prml_vslam.methods.protocols import OfflineSlamBackend, StreamingSlamBackend
from prml_vslam.pipeline.contracts.plan import RunPlanStageId
from prml_vslam.pipeline.contracts.request import (
    DatasetSourceSpec,
    PipelineMode,
    Record3DLiveSourceSpec,
    VideoSourceSpec,
)
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.pipeline.offline import OfflineRunner
from prml_vslam.pipeline.services import RunPlannerService
from prml_vslam.pipeline.state import RunSnapshot, RunState
from prml_vslam.pipeline.streaming import StreamingRunner
from prml_vslam.protocols.source import OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.utils import Console, PathConfig

if TYPE_CHECKING:
    from collections.abc import Callable

    from .contracts.request import RunRequest, SourceSpec

_SUPPORTED_STAGE_IDS = frozenset(
    {
        RunPlanStageId.INGEST,
        RunPlanStageId.SLAM,
        RunPlanStageId.TRAJECTORY_EVALUATION,
        RunPlanStageId.SUMMARY,
    }
)


class VideoOfflineSequenceSource:
    """Video-backed offline source resolved by the pipeline facade."""

    def __init__(self, *, path_config: PathConfig, video_path: Path, frame_stride: int) -> None:
        self._path_config = path_config
        self._video_path = video_path
        self._frame_stride = frame_stride

    @property
    def label(self) -> str:
        """Return the human-readable source label."""
        return f"Video '{self._video_path.name}'"

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        """Resolve the initial offline manifest for one video source."""
        del output_dir
        resolved_video_path = self._path_config.resolve_video_path(self._video_path, must_exist=True)
        return SequenceManifest(
            sequence_id=resolved_video_path.stem,
            video_path=resolved_video_path,
        )


@dataclass(slots=True)
class OfflineSourceResolver:
    """Resolve offline-capable sources for the pipeline façade."""

    path_config: PathConfig

    def resolve(self, source_spec: SourceSpec) -> OfflineSequenceSource:
        """Resolve one source spec into an offline-capable source implementation."""
        match source_spec:
            case DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id=sequence_id):
                service = AdvioDatasetService(self.path_config)
                numeric_sequence_id = service.resolve_sequence_id(sequence_id)
                return service.build_offline_source(sequence_id=numeric_sequence_id)
            case VideoSourceSpec(video_path=video_path, frame_stride=frame_stride):
                return VideoOfflineSequenceSource(
                    path_config=self.path_config,
                    video_path=video_path,
                    frame_stride=frame_stride,
                )
            case Record3DLiveSourceSpec():
                raise RuntimeError("Record3D live sources require `streaming` mode.")
            case _:
                raise RuntimeError(f"Unsupported offline source spec: {source_spec!r}")


class RunService:
    """App-facing façade for the current pipeline execution slice."""

    def __init__(
        self,
        *,
        path_config: PathConfig | None = None,
        planner_service: RunPlannerService | None = None,
        offline_runner: OfflineRunner | None = None,
        streaming_runner: StreamingRunner | None = None,
        slam_backend_factory: Callable[[MethodId], object] | None = None,
        offline_source_resolver: OfflineSourceResolver | None = None,
    ) -> None:
        self.path_config = PathConfig() if path_config is None else path_config
        self._planner_service = RunPlannerService() if planner_service is None else planner_service
        self._offline_runner = OfflineRunner() if offline_runner is None else offline_runner
        self._streaming_runner = StreamingRunner() if streaming_runner is None else streaming_runner
        self._slam_backend_factory = (
            _default_slam_backend_factory if slam_backend_factory is None else slam_backend_factory
        )
        self._offline_source_resolver = (
            OfflineSourceResolver(self.path_config) if offline_source_resolver is None else offline_source_resolver
        )
        self._console = Console(__name__).child(self.__class__.__name__)

    def start_run(self, *, request: RunRequest, runtime_source: StreamingSequenceSource | None = None) -> None:
        """Plan and launch one pipeline run."""
        plan = self._planner_service.build_run_plan(request=request, path_config=self.path_config)
        unsupported_stage_ids = [stage.id for stage in plan.stages if stage.id not in _SUPPORTED_STAGE_IDS]
        if unsupported_stage_ids:
            error_message = "Unsupported stages for the current executable slice: " + ", ".join(
                stage_id.value for stage_id in unsupported_stage_ids
            )
            self._console.error(error_message)
            self._runner_for_mode(request.mode).set_failed_start(plan=plan, error_message=error_message)
            raise RuntimeError(error_message)

        backend = _invoke_slam_backend_factory(
            self._slam_backend_factory,
            method_id=request.slam.method,
            backend_config=request.slam.backend,
            path_config=self.path_config,
        )
        if request.mode is PipelineMode.OFFLINE:
            if runtime_source is not None:
                raise RuntimeError("Offline runs do not accept an injected streaming source.")
            if not isinstance(backend, OfflineSlamBackend):
                raise RuntimeError(f"Backend '{request.slam.method.value}' does not support offline execution.")
            source = self._offline_source_resolver.resolve(request.source)
            self._streaming_runner.stop()
            self._offline_runner.start(request=request, plan=plan, source=source, slam_backend=backend)
            return

        if runtime_source is None:
            raise RuntimeError("Streaming runs require an explicit `runtime_source`.")
        if not isinstance(backend, StreamingSlamBackend):
            raise RuntimeError(f"Backend '{request.slam.method.value}' does not support streaming execution.")
        self._offline_runner.stop()
        self._streaming_runner.start(request=request, plan=plan, source=runtime_source, slam_backend=backend)

    def stop_run(self) -> None:
        """Stop the active run."""
        self._offline_runner.stop()
        self._streaming_runner.stop()

    def snapshot(self) -> RunSnapshot:
        """Return the latest run snapshot from the active runner."""
        offline_snapshot = self._offline_runner.snapshot()
        streaming_snapshot = self._streaming_runner.snapshot()
        return streaming_snapshot if streaming_snapshot.state is not RunState.IDLE else offline_snapshot

    def _runner_for_mode(self, mode: PipelineMode) -> OfflineRunner | StreamingRunner:
        return self._offline_runner if mode is PipelineMode.OFFLINE else self._streaming_runner


def _default_slam_backend_factory(
    method_id: MethodId,
    backend_config: SlamBackendConfig | None = None,
    path_config: PathConfig | None = None,
) -> object:
    """Build the repository-local backend for one selected method."""
    if method_id is MethodId.VISTA:
        vista_backend_config = (
            backend_config if isinstance(backend_config, VistaSlamBackendConfig) else VistaSlamBackendConfig()
        )
        backend = vista_backend_config.setup_target(path_config=path_config)
    elif method_id is MethodId.MAST3R:
        from prml_vslam.methods import Mast3rSlamBackendConfig
        mast3r_backend_config = (
            backend_config
            if isinstance(backend_config, Mast3rSlamBackendConfig)
            else Mast3rSlamBackendConfig()
        )
        backend = mast3r_backend_config.setup_target(path_config=path_config)
    elif method_id is MethodId.MOCK:
        backend = MockSlamBackendConfig(method_id=method_id).setup_target()
    else:
        raise RuntimeError(f"Backend '{method_id.value}' does not support execution yet.")

    if backend is None:
        raise RuntimeError(f"Failed to initialize the SLAM backend for method '{method_id.value}'.")
    return backend


def _invoke_slam_backend_factory(
    factory: object,
    *,
    method_id: MethodId,
    backend_config: SlamBackendConfig,
    path_config: PathConfig,
) -> object:
    """Call one backend factory while preserving compatibility with older test doubles."""
    signature = inspect.signature(factory)
    parameters = list(signature.parameters.values())
    if any(parameter.kind is inspect.Parameter.VAR_POSITIONAL for parameter in parameters):
        return factory(method_id, backend_config, path_config)  # type: ignore[misc]
    positional_count = len(
        [
            parameter
            for parameter in parameters
            if parameter.kind in {inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD}
        ]
    )
    if positional_count >= 3:
        return factory(method_id, backend_config, path_config)  # type: ignore[misc]
    if positional_count == 2:
        return factory(method_id, backend_config)  # type: ignore[misc]
    return factory(method_id)  # type: ignore[misc]


__all__ = ["OfflineSourceResolver", "RunService", "VideoOfflineSequenceSource"]
