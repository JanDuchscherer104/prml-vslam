"""Configuration base classes and TOML serialization helpers for PRML VSLAM.

This module defines a shared configuration model foundation built on Pydantic
(BaseModel), providing:
- semantics-preserving TOML serialization and deserialization (.to_toml / .from_toml_*),
- nested model coercion for nested config objects and standard Python containers,
- runtime target factory wiring via `setup_target`, and
- rich inspection output via `inspect` and Rich Tree rendering.

Higher-level config classes across the project should inherit from BaseConfig for
consistent behavior and TOML interoperability.
"""

from __future__ import annotations

import tomllib
from enum import Enum
from pathlib import Path
from typing import Any, ForwardRef, Self, get_args, get_origin

import numpy as np
import tomli_w
from pydantic import BaseModel, ConfigDict, model_validator
from rich.text import Text
from rich.tree import Tree

from .console import Console


class BaseConfig(BaseModel):
    """Base model for PRML VSLAM configuration objects.

    BaseConfig extends Pydantic BaseModel with project-specific behavior:

    - `to_toml` and `from_toml_*` methods to persist and restore config state in TOML.
    - `model_dump_jsonable` for JSON-safe model extraction with fallback support.
    - `target_type`/`setup_target` pattern for building runtime objects from configs.
    - nested coercion support and rich-tree inspection (`inspect`).

    Subclasses should define typed config fields and can override `target_type`.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        validate_default=True,
        protected_namespaces=(),
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_special_field_inputs(cls, data: Any) -> Any:
        """Coerce TOML-friendly inputs back into explicitly typed runtime values."""
        if not isinstance(data, dict):
            return data

        coerced = dict(data)
        for field_name, field in cls.model_fields.items():
            if field_name not in coerced:
                continue
            coerced[field_name] = cls._coerce_value_for_annotation(coerced[field_name], field.annotation)
        return coerced

    @property
    def target_type(self) -> type[Any] | None:
        """Runtime type used by :meth:`setup_target`."""
        return None

    def setup_target(self, **kwargs: Any) -> Any | None:
        """Create or retrieve the runtime object represented by this config.

        If `target_type` is defined on the class, this method resolves a factory
        function via `target_type.setup_target` (if available) or `target_type` itself.
        The config instance is passed as the first argument to preserve object-level
        context.

        Returns:
            - runtime object created by the factory
            - None when `target_type` is unset

        Raises:
            TypeError: if resolved factory is not callable.
        """
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
        return self.model_dump(mode="json", fallback=self._serialization_fallback, **kwargs)

    def to_toml(self, path: Path | str | None = None) -> str:
        """Serialize the config to a TOML document and optionally write to disk.

        Args:
            path: Optional file path where the TOML text is written.

        Returns:
            The generated TOML string.

        Notes:
            Uses `model_dump_jsonable(exclude_none=True)` to produce data compatible
            with TOML and advanced serialization types.
        """
        rendered = tomli_w.dumps(self.model_dump_jsonable(exclude_none=True))
        if path is not None:
            Path(path).write_text(rendered, encoding="utf-8")
        return rendered

    def save_toml(self, path: Path | str) -> Path:
        """Persist the config to a TOML file and return the resolved path.

        This convenience wrapper preserves the older call surface used by the
        planner and UI layers while delegating all serialization logic to
        :meth:`to_toml`.
        """
        target_path = Path(path)
        self.to_toml(target_path)
        return target_path

    @classmethod
    def from_toml_text(cls: type[Self], source: str | bytes) -> Self:
        """Create a config instance from TOML input provided as text or bytes.

        Args:
            source: TOML input as `str` or `bytes`.

        Returns:
            A validated config model instance.
        """
        if isinstance(source, bytes):
            data = tomllib.loads(source.decode("utf-8"))
        else:
            data = tomllib.loads(source)
        return cls.model_validate(data)

    @classmethod
    def from_toml_file(cls: type[Self], path: Path) -> Self:
        """Load a config from a TOML file path."""
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        return cls.model_validate(data)

    @classmethod
    def from_toml(cls: type[Self], source: str | bytes) -> Self:
        """Load a config from TOML text or bytes."""
        if isinstance(source, Path):
            msg = "from_toml() no longer accepts Path inputs; use from_toml_file()."
            raise TypeError(msg)
        data = tomllib.loads(source.decode("utf-8")) if isinstance(source, bytes) else tomllib.loads(source)
        return cls.model_validate(data)

    def inspect(self, *, show_docs: bool = False) -> None:
        """Render the config tree for interactive debugging and inspection.

        Args:
            show_docs: Show field-level docstrings when True.

        This is a convenience helper for human-readable CLI output and does not
        affect serialization or model behavior.
        """
        Console.from_callsite(stack_offset=1).print(
            self._build_tree(show_docs=show_docs),
            soft_wrap=False,
            highlight=True,
            markup=True,
            emoji=False,
        )

    def _build_tree(self, *, show_docs: bool = False) -> Tree:
        tree = Tree(Text(self.__class__.__name__, style="config.name"))

        if show_docs and self.__class__.__doc__:
            tree.add(Text(self.__class__.__doc__, style="config.doc"))

        for field_name, field in self.__class__.model_fields.items():
            value = getattr(self, field_name)
            field_text = Text()
            field_text.append(f"{field_name}: ", style="config.field")

            if isinstance(value, BaseConfig):
                subtree = tree.add(field_text)
                subtree.add(value._build_tree(show_docs=show_docs))
                continue

            if isinstance(value, list | tuple) and value and all(isinstance(item, BaseConfig) for item in value):
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

    @staticmethod
    def _serialization_fallback(value: Any) -> Any:
        """Fallback serializer for values that are not JSON natively serializable.

        Supported fallbacks:
            - numpy.ndarray -> list
            - numpy scalar -> Python scalar
            - Python type -> name string
            - Enum -> value, string fallback
            - Path -> POSIX string path

        Raises:
            TypeError: when value type is unsupported.
        """
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, type):
            return value.__name__
        if isinstance(value, Enum):
            return value.value if hasattr(value, "value") else str(value)
        if isinstance(value, Path):
            return value.as_posix()
        msg = f"Unable to serialize value of type {type(value).__name__}"
        raise TypeError(msg)

    @classmethod
    def _coerce_value_for_annotation(cls, value: Any, annotation: Any) -> Any:
        if value is None:
            return None

        origin = get_origin(annotation)
        if origin in (list, tuple, set):
            args = get_args(annotation)
            if not args or not isinstance(value, list | tuple | set):
                return value
            coerced_items = [cls._coerce_value_for_annotation(item, args[0]) for item in value]
            if origin is tuple:
                return tuple(coerced_items)
            if origin is set:
                return set(coerced_items)
            return coerced_items

        if origin is not None:
            union_args = [arg for arg in get_args(annotation) if arg is not type(None)]
            for arg in union_args:
                coerced = cls._coerce_value_for_annotation(value, arg)
                if coerced is not value:
                    return coerced
            return value

        if not isinstance(annotation, type):
            return value

        if issubclass(annotation, BaseConfig) and isinstance(value, dict):
            return annotation.model_validate(value)
        if annotation is np.ndarray and isinstance(value, list):
            return np.array(value)
        if issubclass(annotation, np.generic):
            return annotation(value)
        return value
