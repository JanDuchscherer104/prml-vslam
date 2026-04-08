"""Tests for shared trajectory plotting helpers."""

from __future__ import annotations

import numpy as np

from prml_vslam.eval.contracts import ErrorSeries, TrajectorySeries
from prml_vslam.plotting.metrics import build_trajectory_figure
from prml_vslam.plotting.pipeline import build_evo_ape_colormap_figure
from prml_vslam.plotting.record3d import build_live_trajectory_figure


def _trajectory_series(name: str) -> TrajectorySeries:
    return TrajectorySeries(
        name=name,
        positions_xyz=np.asarray([[0.0, 0.0, 0.0], [1.0, 0.5, 0.25]], dtype=np.float64),
        timestamps_s=np.asarray([0.0, 1.0], dtype=np.float64),
    )


def test_live_trajectory_figure_includes_shared_end_markers() -> None:
    positions_xyz = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.5, 0.25]], dtype=np.float64)
    figure = build_live_trajectory_figure(positions_xyz)

    assert [trace.name for trace in figure.data] == ["Ego trajectory", "Start", "Current"]
    assert figure.layout.scene.aspectmode == "data"


def test_metrics_trajectory_figure_uses_standard_xy_axes() -> None:
    figure = build_trajectory_figure([_trajectory_series("Estimate")])

    assert [trace.name for trace in figure.data] == ["Estimate"]
    assert figure.layout.xaxis.title.text == "X (m)"
    assert figure.layout.yaxis.scaleanchor == "x"


def test_pipeline_evo_figure_uses_shared_3d_layout() -> None:
    reference = _trajectory_series("Reference")
    estimate = _trajectory_series("Estimate")
    error_series = ErrorSeries(
        timestamps_s=np.asarray([0.0, 1.0], dtype=np.float64),
        values=np.asarray([0.1, 0.2], dtype=np.float64),
    )

    figure = build_evo_ape_colormap_figure(reference=reference, estimate=estimate, error_series=error_series)

    assert [trace.name for trace in figure.data] == ["Reference", "Estimate", "APE (m)"]
    assert figure.layout.scene.zaxis.title.text == "Z (m)"
    assert figure.layout.scene.aspectmode == "data"
