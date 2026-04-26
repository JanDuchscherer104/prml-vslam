"""Source pipeline stage integration."""

from __future__ import annotations

from prml_vslam.sources.stage.config import SourceStageConfig
from prml_vslam.sources.stage.contracts import SourceStageInput, SourceStageOutput
from prml_vslam.sources.stage.runtime import SourceRuntime
from prml_vslam.sources.stage.visualization import SourceVisualizationAdapter

__all__ = [
    "SourceRuntime",
    "SourceStageConfig",
    "SourceStageInput",
    "SourceStageOutput",
    "SourceVisualizationAdapter",
]
