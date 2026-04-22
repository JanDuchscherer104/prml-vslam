"""Tests for shared trajectory plotting helpers."""

from __future__ import annotations

import numpy as np
import pytest
from evo.core.trajectory import PoseTrajectory3D

from prml_vslam.datasets.advio import AdvioPoseFrameMode
from prml_vslam.eval.contracts import ErrorSeries, IntrinsicsComparisonDiagnostics, TrajectorySeries
from prml_vslam.interfaces import CameraIntrinsics
from prml_vslam.methods.vista.diagnostics import VistaNativeSlamDiagnostics, VistaViewGraphDiagnostics
from prml_vslam.plotting.advio import build_advio_comparison_trajectories
from prml_vslam.plotting.artifact_diagnostics import (
    build_intrinsics_residual_figure,
    build_native_confidence_figure,
    build_native_intrinsics_figure,
    build_native_scale_figure,
    build_native_timing_figure,
    build_view_graph_figure,
)
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


def _native_diagnostics() -> VistaNativeSlamDiagnostics:
    return VistaNativeSlamDiagnostics(
        keyframe_indices=[0, 1, 2],
        confidence_threshold=4.2,
        confidence_mean=[3.5, 4.5, 5.5],
        confidence_p90=[4.5, 5.5, 6.5],
        confidence_valid_ratio=[0.25, 0.5, 0.75],
        scales=[1.0, 1.2, 0.9],
        fx=[10.0, 11.0, 12.0],
        fy=[10.5, 11.5, 12.5],
        cx=[5.0, 5.2, 5.4],
        cy=[6.0, 6.2, 6.4],
        native_positions_xyz=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 2.0, 0.0)],
        native_step_distance_m=[1.0, 2.0],
        slam_sample_intervals_s=[0.5, 0.75],
        intrinsics_comparison=IntrinsicsComparisonDiagnostics(
            raster_space="vista_model",
            reference=CameraIntrinsics(fx=9.0, fy=10.0, cx=5.0, cy=6.0, width_px=224, height_px=224),
            mean_estimate=CameraIntrinsics(fx=11.0, fy=11.5, cx=5.2, cy=6.2, width_px=224, height_px=224),
            fx_residual_px=[1.0, 2.0, 3.0],
            fy_residual_px=[0.5, 1.5, 2.5],
            cx_residual_px=[0.0, 0.2, 0.4],
            cy_residual_px=[0.0, 0.2, 0.4],
        ),
        view_graph=VistaViewGraphDiagnostics(
            node_count=3,
            edge_count=3,
            loop_min_dist=1,
            degree_by_node=[2, 2, 2],
            edge_gaps=[1, 2, 1],
        ),
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


def test_native_artifact_diagnostic_figures_expose_expected_traces() -> None:
    diagnostics = _native_diagnostics()

    confidence = build_native_confidence_figure(diagnostics)
    scale = build_native_scale_figure(diagnostics)
    intrinsics = build_native_intrinsics_figure(diagnostics)
    timing = build_native_timing_figure(diagnostics)
    view_graph = build_view_graph_figure(diagnostics)
    residuals = build_intrinsics_residual_figure(diagnostics)

    assert [trace.name for trace in confidence.data] == ["Mean confidence", "P90 confidence", "Valid ratio"]
    assert [trace.name for trace in scale.data] == ["Scale"]
    assert [trace.name for trace in intrinsics.data] == ["fx", "fy", "cx", "cy"]
    assert [trace.name for trace in timing.data] == ["Native step distance", "TUM sample interval"]
    assert [trace.name for trace in view_graph.data] == ["Node degree", "Edge frame gap"]
    assert [trace.name for trace in residuals.data] == [
        "fx residual",
        "fy residual",
        "cx residual",
        "cy residual",
    ]
