"""Shared validated payload base class for repo-owned DTOs.

This module provides :class:`BaseData`, the canonical low-level base model for
typed contracts across the repository. Higher-level packages such as
:mod:`prml_vslam.interfaces`, :mod:`prml_vslam.pipeline`, and
:mod:`prml_vslam.sources.datasets` build their public DTOs on top of it so validation,
inspection, and IPC serialization stay consistent.
"""

from __future__ import annotations

import pickle
from enum import Enum
from pathlib import Path
from typing import Any, ForwardRef, Self

import numpy as np
from pydantic import BaseModel, ConfigDict
from rich.text import Text
from rich.tree import Tree


class BaseData(BaseModel):
    """Provide a consistent base for typed repo-owned data containers.

    Use :class:`BaseData` for semantic DTOs, persisted result payloads, and
    app/runtime state that should validate on assignment and serialize cleanly
    across process boundaries. Configuration objects that need TOML IO and
    factory behavior should instead inherit from :class:`prml_vslam.utils.BaseConfig`.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        validate_default=True,
        protected_namespaces=(),
    )

    def to_ipc_payload(self) -> Any:
        """Return a pickle-ready Python payload for lightweight IPC transport."""
        payload = self.model_dump(mode="python", round_trip=True)
        return self._normalize_ipc_value(payload)

    def to_ipc_bytes(self) -> bytes:
        """Serialize this model into IPC bytes without widening its public JSON shape."""
        return pickle.dumps(self.to_ipc_payload(), protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def from_ipc_bytes(cls, payload: bytes) -> Self:
        """Deserialize one IPC payload back into the target validated model type."""
        return cls.model_validate(pickle.loads(payload))

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

    @classmethod
    def _normalize_ipc_value(cls, value: Any) -> Any:
        if isinstance(value, BaseData):
            return cls._normalize_ipc_value(value.model_dump(mode="python", round_trip=True))
        if isinstance(value, dict):
            return {key: cls._normalize_ipc_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._normalize_ipc_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(cls._normalize_ipc_value(item) for item in value)
        if isinstance(value, set):
            return {cls._normalize_ipc_value(item) for item in value}
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, np.ndarray | np.generic):
            return value
        return value

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
