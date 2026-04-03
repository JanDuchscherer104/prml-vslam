"""Shared Pydantic model helpers for the PRML VSLAM project."""

from __future__ import annotations

import tomllib
from enum import Enum
from pathlib import Path
from typing import Any, ForwardRef, Literal, Self

import numpy as np
import tomli_w
from pydantic import BaseModel, ConfigDict
from rich.text import Text
from rich.tree import Tree

from .console import Console


class BaseData(BaseModel):
    """Plain validated payload shared by data contracts, state, and results."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        validate_default=True,
        protected_namespaces=(),
    )

    def _build_tree(self, *, show_docs: bool = False) -> Tree:
        tree = Tree(Text(self.__class__.__name__, style="config.name"))

        if show_docs and self.__class__.__doc__:
            tree.add(Text(self.__class__.__doc__, style="config.doc"))

        for field_name, field in self.__class__.model_fields.items():
            value = getattr(self, field_name)
            field_text = Text()
            field_text.append(f"{field_name}: ", style="config.field")

            if isinstance(value, BaseData):
                subtree = tree.add(field_text)
                subtree.add(value._build_tree(show_docs=show_docs))
                continue

            if isinstance(value, list | tuple) and value and all(isinstance(item, BaseData) for item in value):
                subtree = tree.add(field_text)
                for index, item in enumerate(value):
                    item_tree = item._build_tree(show_docs=show_docs)
                    subtree.add(Text(f"[{index}]", style="config.field")).add(item_tree)
                continue

            field_text.append(self._format_value(value), style="config.value")
            field_text.append(f" ({self._get_type_name(field.annotation)})", style="config.type")
            node = tree.add(field_text)
            if show_docs and field.description:
                node.add(Text(field.description, style="config.doc"))

        return tree

    @staticmethod
    def _format_value(value: Any) -> str:
        if isinstance(value, str):
            return f'"{value}"'
        if value is None:
            return "None"
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, Enum):
            return str(value.value if hasattr(value, "value") else value)
        return repr(value)

    @staticmethod
    def _get_type_name(annotation: Any) -> str:
        try:
            if hasattr(annotation, "__origin__"):
                origin = annotation.__origin__.__name__
                args = [
                    arg.__forward_arg__ if isinstance(arg, ForwardRef) else getattr(arg, "__name__", str(arg))
                    for arg in annotation.__args__
                ]
                return f"{origin}[{', '.join(args)}]"
            return str(annotation).replace("typing.", "")
        except Exception:
            return "Any"


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
    """Validated config model with TOML IO and config-as-factory helpers."""

    @property
    def target_type(self) -> type[Any] | None:
        """Runtime type used by :meth:`setup_target`."""
        return None

    def setup_target(self, **kwargs: Any) -> Any | None:
        """Instantiate or build the runtime object described by this config."""
        target_type = self.target_type
        if target_type is None:
            return None

        factory = getattr(target_type, "setup_target", target_type)

        if not callable(factory):
            msg = (
                f"target_type {target_type!r} of type {type(factory).__name__} is not callable and does "
                "not define a setup_target method."
            )
            Console.from_callsite(stack_offset=1).error(msg)
            raise TypeError(msg)

        return factory(self, **kwargs)  # type: ignore[return-value]

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
