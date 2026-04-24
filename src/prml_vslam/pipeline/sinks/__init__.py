"""Observer sinks for pipeline runtime events."""

from .jsonl import JsonlEventSink

__all__ = ["JsonlEventSink"]
