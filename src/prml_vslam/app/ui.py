"""UI helpers for the packaged Streamlit workbench."""

from __future__ import annotations


def inject_styles() -> None:
    """Keep the hook in place without overriding Streamlit's theme system."""
    return None


__all__ = ["inject_styles"]
