"""Runtime construction and preflight scaffolding for pipeline stages."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from pydantic import Field

from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime
from prml_vslam.pipeline.stages.base.proxy import StageRuntimeHandle
from prml_vslam.utils import BaseData

RuntimeFactory = Callable[[], BaseStageRuntime]
JsonScalar = str | int | float | bool | None


class RuntimePreflightResult(BaseData):
    """Result of checking a run plan against registered runtime factories."""

    run_id: str
    """Run id from the checked plan."""

    planned_stage_keys: list[StageKey] = Field(default_factory=list)
    """Available stages that require a runtime."""

    missing_runtime_keys: list[StageKey] = Field(default_factory=list)
    """Available stages with no registered runtime factory."""

    @property
    def ok(self) -> bool:
        """Return whether preflight found all required runtimes."""
        return not self.missing_runtime_keys

    def raise_for_errors(self) -> None:
        """Raise a clear error when preflight found missing runtime factories."""
        if self.ok:
            return
        messages: list[str] = []
        if self.missing_runtime_keys:
            missing = ", ".join(stage_key.value for stage_key in self.missing_runtime_keys)
            messages.append(f"missing runtimes: {missing}")
        raise RuntimeError("; ".join(messages))


class RuntimeManager:
    """Preflight and lazily construct local stage runtime handles."""

    def __init__(
        self,
        *,
        runtime_factories: Mapping[StageKey, RuntimeFactory] | None = None,
        executor_ids: Mapping[StageKey, str] | None = None,
        resource_assignments: Mapping[StageKey, dict[str, JsonScalar]] | None = None,
        stage_configs: Mapping[StageKey, StageConfig] | None = None,
    ) -> None:
        self._runtime_factories = {} if runtime_factories is None else dict(runtime_factories)
        self._executor_ids = {} if executor_ids is None else dict(executor_ids)
        self._resource_assignments = {} if resource_assignments is None else dict(resource_assignments)
        self._stage_configs = {} if stage_configs is None else dict(stage_configs)
        self._runtime_cache: dict[StageKey, StageRuntimeHandle] = {}

    def register(
        self,
        stage_key: StageKey,
        *,
        factory: RuntimeFactory,
        stage_config: StageConfig | None = None,
        executor_id: str | None = None,
        resource_assignment: dict[str, JsonScalar] | None = None,
    ) -> None:
        """Register a lazy runtime factory for one stage."""
        self._runtime_factories[stage_key] = factory
        if executor_id is not None:
            self._executor_ids[stage_key] = executor_id
        self._resource_assignments[stage_key] = {} if resource_assignment is None else dict(resource_assignment)
        if stage_config is not None:
            self._stage_configs[stage_key] = stage_config

    def preflight(self, plan: RunPlan) -> RuntimePreflightResult:
        """Validate runtime availability without constructing runtimes."""
        planned_stage_keys = [stage.key for stage in plan.stages if stage.available]
        missing_runtime_keys: list[StageKey] = []
        for stage_key in planned_stage_keys:
            if stage_key not in self._runtime_factories:
                missing_runtime_keys.append(stage_key)
        return RuntimePreflightResult(
            run_id=plan.run_id,
            planned_stage_keys=planned_stage_keys,
            missing_runtime_keys=missing_runtime_keys,
        )

    def runtime_for(self, stage_key: StageKey) -> StageRuntimeHandle:
        """Return a lazily constructed runtime handle for ``stage_key``."""
        cached = self._runtime_cache.get(stage_key)
        if cached is not None:
            return cached
        factory = self._runtime_factories.get(stage_key)
        if factory is None:
            raise RuntimeError(f"No runtime registered for stage '{stage_key.value}'.")
        runtime = factory()
        proxy = StageRuntimeHandle(
            stage_key=stage_key,
            runtime=runtime,
            executor_id=self._executor_ids.get(stage_key),
            resource_assignment=self._resource_assignments.get(stage_key, {}),
        )
        self._runtime_cache[stage_key] = proxy
        return proxy

    def stage_config(self, stage_key: StageKey) -> StageConfig:
        """Return the stage config used for failure-provenance policy."""
        config = self._stage_configs.get(stage_key)
        if config is not None:
            return config
        return StageConfig(stage_key=stage_key)


__all__ = [
    "RuntimeManager",
    "RuntimePreflightResult",
]
