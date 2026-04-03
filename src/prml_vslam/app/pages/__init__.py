"""Page modules for the packaged Streamlit workbench."""

from .advio import render as render_advio_page
from .metrics import render as render_metrics_page
from .pipeline import render as render_pipeline_page
from .record3d import render as render_record3d_page

__all__ = ["render_advio_page", "render_metrics_page", "render_pipeline_page", "render_record3d_page"]
