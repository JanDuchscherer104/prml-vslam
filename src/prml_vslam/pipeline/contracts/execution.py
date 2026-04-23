"""Pipeline execution lifecycle configuration."""

from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import Field

from prml_vslam.utils import BaseConfig

RayLocalHeadLifecycle: TypeAlias = Literal["ephemeral", "reusable"]


class RayRuntimeConfig(BaseConfig):
    """Configure repository-owned local Ray lifecycle behavior."""

    local_head_lifecycle: RayLocalHeadLifecycle = "ephemeral"
    """Whether the auto-started local Ray head is torn down or preserved after a run."""


class RunRuntimeConfig(BaseConfig):
    """Collect repository-owned execution-lifecycle policy for one run."""

    ray: RayRuntimeConfig = Field(default_factory=RayRuntimeConfig)
    """Local Ray runtime policy translated by the backend layer."""


__all__ = ["RayRuntimeConfig", "RunRuntimeConfig"]
