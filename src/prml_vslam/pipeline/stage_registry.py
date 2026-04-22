"""Compatibility wrapper for legacy stage-registry planning calls.

The active planner now lives in :mod:`prml_vslam.pipeline.config` and compiles
``RunConfig`` stage sections directly. ``StageRegistry`` remains as a narrow
adapter for call sites that still invoke ``StageRegistry.default().compile(...)``.
"""

from __future__ import annotations

from prml_vslam.methods.descriptors import BackendDescriptor
from prml_vslam.pipeline.config import RunConfig
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.utils import PathConfig


class StageRegistry:
    """Bridge legacy planner calls to direct ``RunConfig`` plan compilation."""

    def compile(
        self,
        *,
        request: RunRequest,
        path_config: PathConfig,
        backend: BackendDescriptor | None = None,
    ) -> RunPlan:
        """Compile one deterministic plan from a legacy ``RunRequest``."""
        return RunConfig.from_run_request(request).compile_plan(path_config=path_config, backend=backend)

    def compile_run_config(
        self,
        *,
        run_config: RunConfig,
        path_config: PathConfig,
        backend: BackendDescriptor | None = None,
    ) -> RunPlan:
        """Compile one deterministic plan from a target ``RunConfig``."""
        return run_config.compile_plan(path_config=path_config, backend=backend)

    @classmethod
    def default(cls) -> StageRegistry:
        """Return the compatibility registry adapter."""
        return cls()


__all__ = ["StageRegistry"]
