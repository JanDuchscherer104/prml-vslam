"""Shared Pydantic model helpers for the PRML VSLAM project."""

from __future__ import annotations

import tomllib
from enum import Enum
from pathlib import Path
from typing import Any, Generic, Literal, Protocol, Self, TypeVar, cast

import numpy as np
import tomli_w

from .base_data import BaseData
from .console import Console

TTarget = TypeVar("TTarget", covariant=True)


class _ConfigFactory(Protocol[TTarget]):
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
    """Validated config model with TOML IO and inspection helpers."""

    def model_dump_jsonable(self, **kwargs: Any) -> dict[str, Any]:
        """Return a JSON-serializable view of the config."""
        return _normalize_value(self.model_dump(**kwargs), mode="json")

    @classmethod
    def to_jsonable(cls, value: Any) -> Any:
        """Convert nested values into JSON-friendly primitives."""
        return _normalize_value(value, mode="json")

    def to_toml(self, path: Path | str | None = None) -> str:
        """Serialize the config to TOML and optionally persist it."""
        rendered = tomli_w.dumps(_normalize_value(self.model_dump(exclude_none=True), mode="toml"))
        if path is not None:
            Path(path).write_text(rendered, encoding="utf-8")
        return rendered

    def save_toml(self, path: Path | str) -> Path:
        """Persist the config to a TOML file and return the resolved path."""
        self.to_toml(path)
        return Path(path)

    @classmethod
    def from_toml(cls: type[Self], source: str | Path | bytes) -> Self:
        """Load a config from TOML text, bytes, or a file path."""
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
        """Render the config structure as a Rich tree."""
        Console.from_callsite(stack_offset=1).print(
            self._build_tree(show_docs=show_docs),
            soft_wrap=False,
            highlight=True,
            markup=True,
            emoji=False,
        )


class FactoryConfig(Generic[TTarget]):
    """Generic mixin for configs that can materialize a runtime target."""

    @property
    def target_type(self) -> type[TTarget]:
        """Runtime type used by :meth:`setup_target`."""
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
