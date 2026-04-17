"""Pipeline planning services."""

from __future__ import annotations

from prml_vslam.methods.factory import BackendFactory
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.stage_registry import StageRegistry
from prml_vslam.utils import PathConfig


class RunPlannerService:
    """Canonical planner for the linear pipeline contract.

    Typical usage constructs a fully specified :class:`RunRequest` and then
    calls either :meth:`build_run_plan` directly or ``RunRequest.build()`` to
    obtain the ordered :class:`RunPlan` consumed by the CLI and app surfaces.
    """

    def build_run_plan(self, request: RunRequest, path_config: PathConfig | None = None) -> RunPlan:
        """Build the canonical run plan for one fully specified request.

        Args:
            request: Complete pipeline request containing the source, SLAM
                config, optional stage toggles, and evaluation toggles.
            path_config: Optional path helper that owns canonical repository
                artifact layout.

        Returns:
            Run plan with stable stage ids, current planner ordering, and
            canonical artifact paths for each enabled stage.
        """
        self._validate_request(request)
        config = path_config or PathConfig()
        backend_descriptor = BackendFactory().describe(request.slam.backend)
        return StageRegistry.default().compile(request=request, backend=backend_descriptor, path_config=config)

    @staticmethod
    def _validate_request(request: RunRequest) -> None:
        if request.benchmark.cloud.enabled and not request.slam.outputs.emit_dense_points:
            raise ValueError("Cloud evaluation requires `slam.outputs.emit_dense_points=True`.")


__all__ = ["RunPlannerService"]
