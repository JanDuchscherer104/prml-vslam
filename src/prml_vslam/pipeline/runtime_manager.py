"""Runtime construction and preflight scaffolding for pipeline stages."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from pydantic import Field

from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime
from prml_vslam.pipeline.stages.base.proxy import DeploymentKind, RuntimeCapability, StageRuntimeHandle
from prml_vslam.utils import BaseData

RuntimeFactory = Callable[[], BaseStageRuntime]
JsonScalar = str | int | float | bool | None


class RuntimePreflightResult(BaseData):
    """Result of checking a run plan against registered runtime capabilities."""

    run_id: str
    """Run id from the checked plan."""

    planned_stage_keys: list[StageKey] = Field(default_factory=list)
    """Available stages that require a runtime."""

    missing_runtime_keys: list[StageKey] = Field(default_factory=list)
    """Available stages with no registered runtime factory."""

    unsupported_capabilities: dict[StageKey, list[RuntimeCapability]] = Field(default_factory=dict)
    """Required capabilities not advertised by a registered runtime."""

    unsupported_deployments: dict[StageKey, DeploymentKind] = Field(default_factory=dict)
    """Planned stages whose selected deployment kind is not executable."""

    @property
    def ok(self) -> bool:
        """Return whether preflight found all required runtimes and capabilities."""
        return not self.missing_runtime_keys and not self.unsupported_capabilities and not self.unsupported_deployments

    def raise_for_errors(self) -> None:
        """Raise a clear error when preflight found missing runtime support."""
        if self.ok:
            return
        messages: list[str] = []
        if self.missing_runtime_keys:
            missing = ", ".join(stage_key.value for stage_key in self.missing_runtime_keys)
            messages.append(f"missing runtimes: {missing}")
        if self.unsupported_capabilities:
            unsupported = ", ".join(
                f"{stage_key.value} requires {', '.join(capability.value for capability in capabilities)}"
                for stage_key, capabilities in self.unsupported_capabilities.items()
            )
            messages.append(f"unsupported capabilities: {unsupported}")
        if self.unsupported_deployments:
            unsupported_deployments = ", ".join(
                f"{stage_key.value} uses deployment_kind={deployment_kind!r}"
                for stage_key, deployment_kind in self.unsupported_deployments.items()
            )
            messages.append(
                "unsupported deployment kinds: "
                f"{unsupported_deployments}; Ray-hosted stage runtime handles are not implemented"
            )
        raise RuntimeError("; ".join(messages))


class RuntimeManager:
    """Preflight and lazily construct local stage runtime handles."""

    def __init__(
        self,
        *,
        runtime_factories: Mapping[StageKey, RuntimeFactory] | None = None,
        runtime_capabilities: Mapping[StageKey, frozenset[RuntimeCapability]] | None = None,
        deployment_kinds: Mapping[StageKey, DeploymentKind] | None = None,
        executor_ids: Mapping[StageKey, str] | None = None,
        resource_assignments: Mapping[StageKey, dict[str, JsonScalar]] | None = None,
        stage_configs: Mapping[StageKey, StageConfig] | None = None,
    ) -> None:
        self._runtime_factories = {} if runtime_factories is None else dict(runtime_factories)
        self._runtime_capabilities = {} if runtime_capabilities is None else dict(runtime_capabilities)
        self._deployment_kinds = {} if deployment_kinds is None else dict(deployment_kinds)
        self._executor_ids = {} if executor_ids is None else dict(executor_ids)
        self._resource_assignments = {} if resource_assignments is None else dict(resource_assignments)
        self._stage_configs = {} if stage_configs is None else dict(stage_configs)
        self._runtime_cache: dict[StageKey, StageRuntimeHandle] = {}

    def register(
        self,
        stage_key: StageKey,
        *,
        factory: RuntimeFactory,
        capabilities: frozenset[RuntimeCapability],
        stage_config: StageConfig | None = None,
        deployment_kind: DeploymentKind = "in_process",
        executor_id: str | None = None,
        resource_assignment: dict[str, JsonScalar] | None = None,
    ) -> None:
        """Register a lazy runtime factory for one stage."""
        self._runtime_factories[stage_key] = factory
        self._runtime_capabilities[stage_key] = capabilities
        self._deployment_kinds[stage_key] = deployment_kind
        if executor_id is not None:
            self._executor_ids[stage_key] = executor_id
        self._resource_assignments[stage_key] = {} if resource_assignment is None else dict(resource_assignment)
        if stage_config is not None:
            self._stage_configs[stage_key] = stage_config

    def preflight(self, plan: RunPlan) -> RuntimePreflightResult:
        """Validate runtime availability without constructing runtimes."""
        planned_stage_keys = [stage.key for stage in plan.stages if stage.available]
        missing_runtime_keys: list[StageKey] = []
        unsupported_capabilities: dict[StageKey, list[RuntimeCapability]] = {}
        unsupported_deployments: dict[StageKey, DeploymentKind] = {}
        for stage_key in planned_stage_keys:
            if stage_key not in self._runtime_factories:
                missing_runtime_keys.append(stage_key)
                continue
            deployment_kind = self._deployment_kinds.get(stage_key, "in_process")
            if deployment_kind == "ray":
                unsupported_deployments[stage_key] = deployment_kind
            required = self.required_capabilities(plan.mode, stage_key)
            unsupported = sorted(
                required - self._runtime_capabilities.get(stage_key, frozenset()),
                key=lambda capability: capability.value,
            )
            if unsupported:
                unsupported_capabilities[stage_key] = unsupported
        return RuntimePreflightResult(
            run_id=plan.run_id,
            planned_stage_keys=planned_stage_keys,
            missing_runtime_keys=missing_runtime_keys,
            unsupported_capabilities=unsupported_capabilities,
            unsupported_deployments=unsupported_deployments,
        )

    def runtime_for(self, stage_key: StageKey) -> StageRuntimeHandle:
        """Return a lazily constructed runtime handle for ``stage_key``."""
        cached = self._runtime_cache.get(stage_key)
        if cached is not None:
            return cached
        factory = self._runtime_factories.get(stage_key)
        if factory is None:
            raise RuntimeError(f"No runtime registered for stage '{stage_key.value}'.")
        deployment_kind = self._deployment_kinds.get(stage_key, "in_process")
        if deployment_kind == "ray":
            raise NotImplementedError(
                f"Stage '{stage_key.value}' requested deployment_kind='ray', but Ray-hosted stage runtime handles "
                "are not implemented yet."
            )
        runtime = factory()
        proxy = StageRuntimeHandle(
            stage_key=stage_key,
            runtime=runtime,
            supported_capabilities=self._runtime_capabilities.get(stage_key, frozenset()),
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

    @staticmethod
    def required_capabilities(mode: PipelineMode, stage_key: StageKey) -> frozenset[RuntimeCapability]:
        """Return initial runtime capabilities required by a plan stage."""
        if mode is PipelineMode.STREAMING and stage_key is StageKey.SLAM:
            return frozenset({RuntimeCapability.LIVE_UPDATES, RuntimeCapability.STREAMING})
        return frozenset({RuntimeCapability.OFFLINE})


__all__ = [
    "RuntimeManager",
    "RuntimePreflightResult",
]
