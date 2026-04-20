"""Canonical visualization-stage DTOs shared outside the visualization package."""

from __future__ import annotations

from pydantic import Field

from prml_vslam.interfaces.slam import ArtifactRef
from prml_vslam.utils import BaseData


class VisualizationArtifacts(BaseData):
    """Viewer artifacts associated with one run."""

    native_rerun_rrd: ArtifactRef | None = None
    native_output_dir: ArtifactRef | None = None
    extras: dict[str, ArtifactRef] = Field(default_factory=dict)


__all__ = ["VisualizationArtifacts"]
