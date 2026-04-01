"""Logging-backed Rich console helpers for the PRML VSLAM project."""

from __future__ import annotations

import inspect
import logging
from typing import Any, ClassVar

from rich.console import Console as RichConsole
from rich.logging import RichHandler
from rich.pretty import Pretty
from rich.theme import Theme

DEFAULT_THEME = Theme(
    {
        "config.name": "bold blue",
        "config.field": "green",
        "config.value": "white",
        "config.type": "dim",
        "config.doc": "italic dim",
    }
)


def caller_namespace(*, stack_offset: int = 0) -> str:
    """Return a dotted namespace for the caller.

    The namespace is derived from the caller's module and qualified function name.
    For bound methods, this yields values like ``my.module.MyClass.method``.
    """
    # Use stack inspection helpers instead of manual frame traversal loop.
    stack = inspect.stack(context=0)
    try:
        record_index = stack_offset + 1
        if record_index >= len(stack):
            return "prml_vslam"

        frame = stack[record_index].frame
        module_name = frame.f_globals.get("__name__", "prml_vslam")
        qualname = frame.f_code.co_qualname.replace(".<locals>.", ".")
        if qualname == "<module>":
            return module_name
        return f"{module_name}.{qualname}"
    finally:
        # Break reference cycles with frame objects.
        del stack


class Console:
    """Small wrapper that unifies Rich output and standard logging."""

    _rich_console: ClassVar[RichConsole] = RichConsole(
        theme=DEFAULT_THEME,
        width=120,
        markup=True,
        highlight=True,
    )
    _logging_configured: ClassVar[bool] = False

    def __init__(
        self,
        namespace: str | None = None,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self.namespace = self._qualify_namespace(namespace or "prml_vslam")
        self.logger = logger or logging.getLogger(self.namespace)

    @classmethod
    def configure_logging(
        cls,
        level: int | str = logging.INFO,
        *,
        force: bool = False,
    ) -> logging.Logger:
        """Attach a Rich logging handler to the ``prml_vslam`` logger tree."""
        project_logger = logging.getLogger("prml_vslam")
        project_logger.setLevel(level)
        project_logger.propagate = False

        has_project_handler = any(
            isinstance(handler, RichHandler) and getattr(handler, "_prml_vslam_handler", False)
            for handler in project_logger.handlers
        )

        if force or not has_project_handler:
            handler = RichHandler(
                console=cls._rich_console,
                markup=True,
                rich_tracebacks=True,
                show_path=False,
                show_time=False,
            )
            handler._prml_vslam_handler = True  # type: ignore[attr-defined]
            handler.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
            project_logger.handlers = [handler]

        cls._logging_configured = True
        return project_logger

    @classmethod
    def from_callsite(cls, *parts: str, stack_offset: int = 0) -> Console:
        """Create a console using the caller's module and qualified function name."""
        namespace = caller_namespace(stack_offset=stack_offset + 1)
        if parts:
            namespace = ".".join([namespace, *filter(None, parts)])
        return cls(namespace=namespace)

    def print(self, *objects: Any, **kwargs: Any) -> None:
        """Render directly via Rich for structured or non-log output."""
        self._rich_console.print(*objects, **kwargs)

    @property
    def rich_console(self) -> RichConsole:
        """Expose the shared Rich console for progress/status helpers."""
        return self._rich_console

    def plog(self, obj: Any, **kwargs: Any) -> None:
        """Pretty-print a Python object with Rich."""
        self.print(Pretty(obj, **kwargs))

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an informational message."""
        self._ensure_logging()
        self.logger.info(message, *args, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message."""
        self._ensure_logging()
        self.logger.debug(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message."""
        self._ensure_logging()
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message."""
        self._ensure_logging()
        self.logger.error(message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an exception with traceback information."""
        self._ensure_logging()
        self.logger.exception(message, *args, **kwargs)

    @classmethod
    def _qualify_namespace(cls, namespace: str) -> str:
        namespace = namespace.strip()
        if not namespace:
            return "prml_vslam"
        if namespace.startswith("prml_vslam"):
            return namespace
        return f"prml_vslam.{namespace}"

    def _ensure_logging(self) -> None:
        if not self._logging_configured:
            self.configure_logging()


def get_console(*parts: str, stack_offset: int = 0) -> Console:
    """Return a callsite-aware console instance.

    This keeps the existing convenience API stable while the project gradually
    moves toward explicit ``Console.from_callsite(...)`` usage.
    """
    return Console.from_callsite(*parts, stack_offset=stack_offset + 1)
