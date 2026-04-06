"""Pipeline-facing run facade for the bounded demo slice."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prml_vslam.methods import MockSlamBackendConfig
from prml_vslam.methods.contracts import MethodId
from prml_vslam.methods.protocols import StreamingSlamBackend
from prml_vslam.pipeline.contracts import RunPlanStageId, RunRequest
from prml_vslam.pipeline.services import RunPlannerService
from prml_vslam.pipeline.session import PipelineSessionService, PipelineSessionSnapshot
from prml_vslam.protocols.source import StreamingSequenceSource
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


class RunService:
    """App-facing facade for the currently supported pipeline slice."""

    def __init__(
        self,
        *,
        path_config: PathConfig | None = None,
        planner_service: RunPlannerService | None = None,
        session_service: PipelineSessionService | None = None,
        slam_backend_factory: Callable[[MethodId], StreamingSlamBackend] | None = None,
    ) -> None:
        self.path_config = PathConfig() if path_config is None else path_config
        self._planner_service = RunPlannerService() if planner_service is None else planner_service
        self._session_service = PipelineSessionService() if session_service is None else session_service
        self._slam_backend_factory = (
            _default_slam_backend_factory if slam_backend_factory is None else slam_backend_factory
        )
        self._console = Console(__name__).child(self.__class__.__name__)

    def start_run(self, *, request: RunRequest, source: StreamingSequenceSource) -> None:
        """Plan and launch one bounded pipeline run."""
        plan = self._planner_service.build_run_plan(request=request, path_config=self.path_config)
        unsupported_stage_ids = [stage.id for stage in plan.stages if stage.id not in _SUPPORTED_STAGE_IDS]
        if unsupported_stage_ids:
            error_message = "Unsupported stages for the current streaming slice: " + ", ".join(
                stage_id.value for stage_id in unsupported_stage_ids
            )
            self._console.error(error_message)
            self._session_service.set_failed_start(plan=plan, error_message=error_message)
            raise RuntimeError(error_message)

        slam_backend = self._slam_backend_factory(request.slam.method)
        self._session_service.start(
            request=request,
            plan=plan,
            source=source,
            slam_backend=slam_backend,
        )

    def stop_run(self) -> None:
        """Stop the active bounded run."""
        self._session_service.stop()

    def snapshot(self) -> PipelineSessionSnapshot:
        """Return the latest bounded-run snapshot."""
        return self._session_service.snapshot()


def _default_slam_backend_factory(method_id: MethodId) -> StreamingSlamBackend:
    """Build the repository-local mock backend for one selected method."""
    backend = MockSlamBackendConfig(method_id=method_id).setup_target()
    if backend is None:
        raise RuntimeError(f"Failed to initialize the mock SLAM backend for method '{method_id.value}'.")
    return backend


__all__ = ["RunService"]
