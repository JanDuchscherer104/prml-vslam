"""Shared Pydantic model helpers for the PRML VSLAM project."""

from __future__ import annotations

import tomllib
from enum import Enum
from pathlib import Path
from typing import Any, ForwardRef, Self

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
                args: list[str] = []
                for arg in annotation.__args__:
                    if isinstance(arg, ForwardRef):
                        args.append(arg.__forward_arg__)
                    elif hasattr(arg, "__name__"):
                        args.append(arg.__name__)
                    else:
                        args.append(str(arg))
                return f"{origin}[{', '.join(args)}]"
            return str(annotation).replace("typing.", "")
        except Exception:
            return "Any"


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
        return self.to_jsonable(self.model_dump(**kwargs))

    @classmethod
    def to_jsonable(cls, value: Any) -> Any:
        """Convert nested values into JSON-friendly primitives."""
        if isinstance(value, BaseConfig):
            return value.model_dump_jsonable()
        if isinstance(value, BaseData):
            return cls.to_jsonable(value.model_dump(mode="python"))
        if isinstance(value, dict):
            return {str(key): cls.to_jsonable(item) for key, item in value.items()}
        if isinstance(value, list | tuple | set):
            return [cls.to_jsonable(item) for item in value]
        if isinstance(value, Path):
            return value.as_posix()
        if isinstance(value, Enum):
            return value.value if hasattr(value, "value") else str(value)
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, type):
            return value.__name__
        return value

    def to_toml(self, path: Path | str | None = None) -> str:
        """Serialize the config to TOML and optionally persist it."""
        rendered = tomli_w.dumps(self._toml_normalize(self.model_dump(exclude_none=True)))
        if path is not None:
            Path(path).write_text(rendered, encoding="utf-8")
        return rendered

    def save_toml(self, path: Path | str) -> Path:
        """Persist the config to a TOML file and return the resolved path."""
        target_path = Path(path)
        self.to_toml(target_path)
        return target_path

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

    @classmethod
    def _toml_normalize(cls, value: Any) -> Any:
        if isinstance(value, BaseData):
            return cls._toml_normalize(value.model_dump(exclude_none=True))
        if isinstance(value, dict):
            return {str(key): cls._toml_normalize(item) for key, item in value.items()}
        if isinstance(value, list | tuple | set):
            return [cls._toml_normalize(item) for item in value]
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, Enum):
            return value.value if hasattr(value, "value") else str(value)
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()
        return value
