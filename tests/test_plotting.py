"""Tests for shared trajectory plotting helpers."""

from __future__ import annotations

import numpy as np
import pytest
from evo.core.trajectory import PoseTrajectory3D

from prml_vslam.datasets.advio import AdvioPoseFrameMode
from prml_vslam.eval.contracts import ErrorSeries, TrajectorySeries
from prml_vslam.plotting.advio import build_advio_comparison_trajectories
from prml_vslam.plotting.metrics import build_trajectory_figure
from prml_vslam.plotting.pipeline import build_evo_ape_colormap_figure, pointmap_preview_image
from prml_vslam.plotting.record3d import build_live_trajectory_figure
from prml_vslam.plotting.trajectories import build_bev_trajectory_figure, build_height_profile_figure


def _trajectory_series(name: str) -> TrajectorySeries:
    return TrajectorySeries(
        name=name,
        positions_xyz=np.asarray([[0.0, 0.0, 0.0], [1.0, 0.5, 0.25]], dtype=np.float64),
        timestamps_s=np.asarray([0.0, 1.0], dtype=np.float64),
    )


def _pose_trajectory(positions_xyz: list[tuple[float, float, float]]) -> PoseTrajectory3D:
    return PoseTrajectory3D(
        positions_xyz=np.asarray(positions_xyz, dtype=np.float64),
        orientations_quat_wxyz=np.tile(np.asarray([[1.0, 0.0, 0.0, 0.0]], dtype=np.float64), (len(positions_xyz), 1)),
        timestamps=np.asarray([0.0, 0.1, 0.2][: len(positions_xyz)], dtype=np.float64),
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
    assert figure.layout.margin.t >= 112
    assert figure.layout.legend.yanchor == "top"
    assert figure.layout.legend.y <= 1.02


def test_pipeline_pointmap_preview_image_uses_generic_projection() -> None:
    pointmap = np.array(
        [
            [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
            [[7.0, 8.0, 9.0], [10.0, 11.0, 12.0]],
        ],
        dtype=np.float32,
    )

    preview = pointmap_preview_image(pointmap)

    assert preview is not None
    assert preview.shape == (2, 2)
    assert not np.array_equal(preview, pointmap[..., 2])


def test_advio_plotting_supports_dataset_specific_axes() -> None:
    trajectory = _pose_trajectory([(0.0, 1.0, 2.0), (1.0, 2.0, 3.0), (2.0, 3.0, 4.0)])
    bev = build_bev_trajectory_figure([("GT", trajectory)], plane_axes=(0, 2))
    height = build_height_profile_figure([("GT", trajectory)], height_axis=1)

    assert bev.layout.xaxis.title.text == "X (m)"
    assert bev.layout.yaxis.title.text == "Z (m)"
    assert np.array_equal(np.asarray(bev.data[0].y), np.asarray([2.0, 3.0, 4.0]))
    assert height.layout.yaxis.title.text == "Y (m)"
    assert np.array_equal(np.asarray(height.data[0].y), np.asarray([1.0, 2.0, 3.0]))


def test_advio_comparison_trajectories_align_and_rebase_provider_tracks() -> None:
    ground_truth = _pose_trajectory([(1.0, 2.0, 3.0), (1.5, 2.5, 3.5), (2.0, 3.0, 4.0)])
    arcore = _pose_trajectory([(10.0, 20.0, 30.0), (10.5, 20.5, 30.5), (11.0, 21.0, 31.0)])

    aligned = build_advio_comparison_trajectories(
        ground_truth=ground_truth,
        arcore=arcore,
        arkit=None,
        pose_frame_mode=AdvioPoseFrameMode.REFERENCE_WORLD,
    )
    rebased = build_advio_comparison_trajectories(
        ground_truth=ground_truth,
        arcore=arcore,
        arkit=None,
        pose_frame_mode=AdvioPoseFrameMode.LOCAL_FIRST_POSE,
    )

    assert aligned[1][1].positions_xyz[0, 0] == pytest.approx(1.0, abs=1e-3)
    assert rebased[1][1].positions_xyz[0, 0] == pytest.approx(0.0, abs=1e-6)
