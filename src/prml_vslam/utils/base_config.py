"""Shared config and config-as-factory helpers for the repository.

This module owns :class:`BaseConfig` and :class:`FactoryConfig`, the utility
layer that packages use when a validated config must also serialize to TOML and
materialize a runtime target. Repo-specific orchestration policy does not live
here; package owners such as :mod:`prml_vslam.pipeline` and
:mod:`prml_vslam.methods` build their own config models on top of these shared
primitives.
"""

from __future__ import annotations

import tomllib
from abc import abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Generic, Literal, Protocol, Self, TypeVar, cast

import numpy as np
import tomli_w

from .base_data import BaseData
from .console import Console

TTarget = TypeVar("TTarget", covariant=True)


class _ConfigFactory(Protocol[TTarget]):
    @abstractmethod
    def __call__(self, config: object, **kwargs: Any) -> TTarget: ...


def _normalize_value(value: Any, *, mode: Literal["json", "toml"]) -> Any:
    if isinstance(value, BaseData):
        dump_kwargs: dict[str, Any] = {"exclude_none": mode == "toml"}
        if mode == "json":
            dump_kwargs["mode"] = "python"
        return _normalize_value(value.model_dump(**dump_kwargs), mode=mode)
    if isinstance(value, dict):
        return {str(key): _normalize_value(item, mode=mode) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_normalize_value(item, mode=mode) for item in value]

    match value:
        case Path():
            return value.as_posix() if mode == "json" else str(value)
        case Enum():
            return value.value if hasattr(value, "value") else str(value)
        case np.ndarray():
            return value.tolist()
        case np.generic():
            return value.item()
        case _ if mode == "json" and isinstance(value, type):
            return value.__name__
        case _:
            return value


class BaseConfig(BaseData):
    """Augment :class:`BaseData` with deterministic TOML IO and config inspection.

    Use this base for durable repo-owned configuration surfaces such as
    :class:`prml_vslam.pipeline.contracts.request.RunRequest`,
    :class:`prml_vslam.methods.config_contracts.SlamBackendConfig`, and
    :class:`prml_vslam.visualization.contracts.VisualizationConfig`.
    """

    def model_dump_jsonable(self, **kwargs: Any) -> dict[str, Any]:
        """Return a JSON-serializable view suitable for UI payloads and debugging."""
        return _normalize_value(self.model_dump(**kwargs), mode="json")

    @classmethod
    def to_jsonable(cls, value: Any) -> Any:
        """Normalize nested config values into JSON-friendly primitives."""
        return _normalize_value(value, mode="json")

    def to_toml(self, path: Path | str | None = None) -> str:
        """Serialize the config to deterministic TOML and optionally persist it."""
        rendered = tomli_w.dumps(_normalize_value(self.model_dump(exclude_none=True), mode="toml"))
        if path is not None:
            Path(path).write_text(rendered, encoding="utf-8")
        return rendered

    def save_toml(self, path: Path | str) -> Path:
        """Persist the config to TOML and return the resulting file path."""
        self.to_toml(path)
        return Path(path)

    @classmethod
    def from_toml(cls: type[Self], source: str | Path | bytes) -> Self:
        """Load the validated config from TOML text, bytes, or a file path."""
        if isinstance(source, Path):
            data = tomllib.loads(source.read_text(encoding="utf-8"))
        elif isinstance(source, bytes):
            data = tomllib.loads(source.decode("utf-8"))
        elif "\n" in source or "\r" in source:
            data = tomllib.loads(source)
        else:
            candidate = Path(source)
            if candidate.exists():
                data = tomllib.loads(candidate.read_text(encoding="utf-8"))
            else:
                data = tomllib.loads(source)

        return cls.model_validate(data)

    def inspect(self, *, show_docs: bool = False) -> None:
        """Render the config as a Rich tree for quick human inspection."""
        Console.from_callsite(stack_offset=1).print(
            self._build_tree(show_docs=show_docs),
            soft_wrap=False,
            highlight=True,
            markup=True,
            emoji=False,
        )


class FactoryConfig(Generic[TTarget]):
    """Mixin for configs that construct one runtime owner or adapter.

    This pattern keeps construction policy close to the typed config while
    avoiding ad hoc dict-based factories. It is appropriate for concrete
    domain/source/backend variants such as method backends, Record3D sources,
    and reconstruction backends. It should not be used for pipeline stage
    policy configs, because target stage runtime construction belongs to
    :class:`prml_vslam.pipeline.runtime_manager.RuntimeManager`.
    """

    @property
    def target_type(self) -> type[TTarget]:
        """Return the runtime type or owner constructed by :meth:`setup_target`."""
        raise NotImplementedError

    def setup_target(self, **kwargs: Any) -> TTarget:
        """Instantiate or build the runtime object described by this config."""
        target_type = self.target_type
        factory = cast(_ConfigFactory[TTarget], getattr(target_type, "setup_target", target_type))

        if not callable(factory):
            msg = (
                f"target_type {target_type!r} of type {type(factory).__name__} is not callable and does "
                "not define a setup_target method."
            )
            Console.from_callsite(stack_offset=1).error(msg)
            raise TypeError(msg)

        return factory(self, **kwargs)
