"""Page modules for the packaged Streamlit workbench."""

from .metrics import render as render_metrics_page
from .record3d import render as render_record3d_page

__all__ = ["render_metrics_page", "render_record3d_page"]
