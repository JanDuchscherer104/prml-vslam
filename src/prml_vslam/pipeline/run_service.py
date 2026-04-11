"""Pipeline-facing run facade for offline and streaming execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from prml_vslam.datasets.advio import AdvioDatasetService
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.methods import MockSlamBackendConfig
from prml_vslam.methods.contracts import MethodId
from prml_vslam.methods.protocols import OfflineSlamBackend, SlamBackend, StreamingSlamBackend
from prml_vslam.pipeline.contracts.plan import RunPlanStageId
from prml_vslam.pipeline.contracts.request import (
    DatasetSourceSpec,
    PipelineMode,
    Record3DLiveSourceSpec,
    RunRequest,
    VideoSourceSpec,
)
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.pipeline.offline import OfflineRunner
from prml_vslam.pipeline.services import RunPlannerService
from prml_vslam.pipeline.streaming import StreamingRunner
from prml_vslam.protocols.source import OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.utils import Console, PathConfig

if TYPE_CHECKING:
    from collections.abc import Callable

_SUPPORTED_STAGE_IDS = frozenset(
    {
        RunPlanStageId.INGEST,
        RunPlanStageId.SLAM,
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

    def resolve(self, source_spec: object) -> OfflineSequenceSource:
        """Resolve one source spec into an offline-capable source implementation."""
        match source_spec:
            case DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id=sequence_id):
                service = AdvioDatasetService(self.path_config)
                numeric_sequence_id = _advio_sequence_id_from_slug(sequence_id)
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
        slam_backend_factory: Callable[[MethodId], SlamBackend] | None = None,
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

        backend = self._slam_backend_factory(request.slam.method)
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
        return offline_snapshot if offline_snapshot.state is not RunState.IDLE else streaming_snapshot

    def _runner_for_mode(self, mode: PipelineMode) -> OfflineRunner | StreamingRunner:
        return self._offline_runner if mode is PipelineMode.OFFLINE else self._streaming_runner


def _default_slam_backend_factory(method_id: MethodId) -> SlamBackend:
    """Build the repository-local mock backend for one selected method."""
    backend = MockSlamBackendConfig(method_id=method_id).setup_target()
    if backend is None:
        raise RuntimeError(f"Failed to initialize the mock SLAM backend for method '{method_id.value}'.")
    return backend


def _advio_sequence_id_from_slug(sequence_slug: str) -> int:
    if sequence_slug.startswith("advio-"):
        _, suffix = sequence_slug.split("-", maxsplit=1)
        if suffix.isdigit():
            return int(suffix)
    raise RuntimeError(f"ADVIO sequence slug '{sequence_slug}' could not be resolved to a numeric scene id.")


__all__ = ["OfflineSourceResolver", "RunService", "VideoOfflineSequenceSource"]
