from __future__ import annotations
import logging as logging
import os as os
from pathlib import Path

__all__: list[str] = ["LogRecord", "Path", "code2md", "get_runid", "logging", "os"]

class LogRecord(logging.LogRecord):
    """
    Class for logging information.
    """
    def getMessage(self): ...

def code2md(code_text, language=None):
    """
    Format code as markdown for display (eg in tensorboard)
    """

def get_runid(path):
    """
    Get runid for an experiment.
    """
