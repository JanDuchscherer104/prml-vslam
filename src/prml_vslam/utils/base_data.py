"""Shared Pydantic base model for validated data containers."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, ForwardRef

from pydantic import BaseModel, ConfigDict
from rich.text import Text
from rich.tree import Tree


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
