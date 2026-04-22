"""Visualization artifact DTOs shared outside the visualization package.

These DTOs describe durable viewer/export artifacts associated with a run.
They do not encode Rerun SDK commands, entity paths, or frame-normalization
policy; those responsibilities stay in :mod:`prml_vslam.visualization` and the
pipeline Rerun sink.
"""

from __future__ import annotations

from pydantic import Field

from prml_vslam.interfaces.slam import ArtifactRef
from prml_vslam.utils import BaseData


class VisualizationArtifacts(BaseData):
    """Viewer artifacts associated with one run.

    Native upstream recordings and repo-owned viewer outputs are useful for
    inspection, but they are not the scientific source of truth. Consumers
    should use normalized SLAM/reconstruction/evaluation artifacts for
    benchmark decisions and treat these paths as visualization provenance.
    """

    native_rerun_rrd: ArtifactRef | None = None
    native_output_dir: ArtifactRef | None = None
    extras: dict[str, ArtifactRef] = Field(default_factory=dict)


__all__ = ["VisualizationArtifacts"]
