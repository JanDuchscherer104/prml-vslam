"""Tests for shared trajectory plotting helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pytest
from evo.core.trajectory import PoseTrajectory3D

from prml_vslam.eval.contracts import (
    CloudEstimateKind,
    CloudMetricId,
    DenseCloudEstimateEvaluation,
    DenseCloudEvaluationArtifact,
    IntrinsicsComparisonDiagnostics,
)
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
from prml_vslam.plotting.datasets import build_reference_cloud_scene_figure, build_trajectory_metric_figure
from prml_vslam.plotting.metrics import (
    build_cloud_accuracy_completeness_xy_figure,
    build_cloud_distance_metrics_figure,
    build_cloud_icp_impact_figure,
    build_cloud_point_count_figure,
    build_cloud_quality_metrics_figure,
    build_trajectory_figure,
)
from prml_vslam.plotting.pipeline import build_evo_ape_colormap_figure, pointmap_preview_image
from prml_vslam.plotting.record3d import build_live_trajectory_figure
from prml_vslam.plotting.trajectories import build_bev_trajectory_figure, build_height_profile_figure
from prml_vslam.sources.datasets.advio import AdvioPoseFrameMode
from prml_vslam.utils.geometry import write_point_cloud_ply


@dataclass(slots=True)
class _TrajectorySeries:
    name: str
    positions_xyz: np.ndarray
    timestamps_s: np.ndarray


@dataclass(slots=True)
class _ErrorSeries:
    timestamps_s: np.ndarray
    values: np.ndarray


def _trajectory_series(name: str) -> _TrajectorySeries:
    return _TrajectorySeries(
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


def test_cloud_metric_figures_expose_distance_quality_and_count_traces(tmp_path) -> None:
    artifact = DenseCloudEvaluationArtifact(
        path=tmp_path / "cloud_metrics.json",
        title="Dense Cloud Evaluation (Open3D)",
        reference_cloud_path=tmp_path / "reference.ply",
        f1_threshold_m=0.05,
        estimates=[
            DenseCloudEstimateEvaluation(
                estimate_kind=CloudEstimateKind.SIM3,
                estimate_cloud_path=tmp_path / "sim3.ply",
                reference_point_count=10,
                estimate_point_count=20,
                metrics={
                    CloudMetricId.ACCURACY: 0.1,
                    CloudMetricId.COMPLETENESS: 0.2,
                    CloudMetricId.CHAMFER: 0.3,
                    CloudMetricId.F1: 0.4,
                },
            ),
            DenseCloudEstimateEvaluation(
                estimate_kind=CloudEstimateKind.SIM3_ICP,
                estimate_cloud_path=tmp_path / "icp.ply",
                reference_point_count=10,
                estimate_point_count=18,
                metrics={
                    CloudMetricId.ACCURACY: 0.05,
                    CloudMetricId.COMPLETENESS: 0.15,
                    CloudMetricId.CHAMFER: 0.2,
                    CloudMetricId.F1: 0.8,
                    CloudMetricId.ICP_FITNESS: 0.9,
                },
            ),
        ],
    )

    distance = build_cloud_distance_metrics_figure(artifact)
    quality = build_cloud_quality_metrics_figure(artifact)
    counts = build_cloud_point_count_figure(artifact)
    impact = build_cloud_icp_impact_figure(artifact)
    xy = build_cloud_accuracy_completeness_xy_figure(artifact)

    assert [trace.name for trace in distance.data] == ["Accuracy", "Completeness", "Chamfer"]
    assert [trace.name for trace in quality.data] == ["F1 @ 0.05 m", "ICP fitness"]
    assert [trace.name for trace in counts.data] == ["Estimate points", "Reference points"]
    assert list(impact.data[0].x) == ["Accuracy", "Completeness", "Chamfer", "F1"]
    assert list(impact.data[0].y) == pytest.approx([0.05, 0.05, 0.1, 0.4])
    assert [trace.name for trace in xy.data] == ["Sim3", "Sim3 + ICP"]
    assert xy.layout.annotations[0].text == "ICP"
    assert distance.layout.barmode == "group"
    assert quality.layout.yaxis.range == (0.0, 1.0)


def test_pipeline_evo_figure_uses_shared_3d_layout() -> None:
    reference = _trajectory_series("Reference")
    estimate = _trajectory_series("Estimate")
    error_series = _ErrorSeries(
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


def test_dataset_trajectory_metric_figure_uses_scene_subject_labels() -> None:
    frame = pd.DataFrame.from_records(
        [
            {
                "sequence_id": "scene-a",
                "subject": "ground_truth/source_native",
                "trajectory_mean_speed_m_s": "0.4",
                "trajectory_mean_curvature_rad_m": "0.12",
            },
            {
                "sequence_id": "scene-a",
                "subject": "arkit/aligned",
                "trajectory_mean_speed_m_s": "0.7",
                "trajectory_mean_curvature_rad_m": "0.18",
            },
            {
                "sequence_id": "scene-b",
                "subject": "arkit/aligned",
                "trajectory_mean_speed_m_s": "1.1",
                "trajectory_mean_curvature_rad_m": "0.35",
            },
        ]
    )

    speed = build_trajectory_metric_figure(
        frame,
        value_column="trajectory_mean_speed_m_s",
        title="Mean Speed per Scene",
        yaxis_title="Mean Speed (m/s)",
    )
    curvature = build_trajectory_metric_figure(
        frame,
        value_column="trajectory_mean_curvature_rad_m",
        title="Mean Curvature per Scene",
        yaxis_title="Mean Curvature (rad/m)",
    )

    assert [trace.name for trace in speed.data] == ["ground_truth/source_native", "arkit/aligned"]
    assert list(speed.data[0].x) == ["scene-a"]
    assert list(speed.data[1].x) == ["scene-a", "scene-b"]
    assert list(speed.data[0].y) == [0.4]
    assert list(speed.data[1].y) == [0.7, 1.1]
    assert speed.data[0].marker.color != speed.data[1].marker.color
    assert speed.layout.barmode == "group"
    assert speed.layout.showlegend is True
    assert [trace.name for trace in curvature.data] == [trace.name for trace in speed.data]
    assert list(curvature.data[0].y) == [0.12]
    assert list(curvature.data[1].y) == [0.18, 0.35]


def test_reference_cloud_scene_figure_samples_cloud_and_overlays_trajectory(tmp_path) -> None:
    cloud_path = write_point_cloud_ply(
        tmp_path / "cloud.ply",
        np.asarray([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0], [2.0, 2.0, 2.0]], dtype=np.float64),
    )
    trajectory = _pose_trajectory([(0.0, 0.0, 0.0), (2.0, 0.0, 1.0)])

    figure = build_reference_cloud_scene_figure(
        clouds=[("Reference cloud", cloud_path)],
        trajectories=[("Ground truth", trajectory)],
        max_points=2,
        random_seed=1,
    )

    assert [trace.name for trace in figure.data] == ["Reference cloud (2/3)", "Ground truth"]
    assert figure.layout.scene.aspectmode == "data"


def test_advio_comparison_trajectories_rebase_provider_tracks() -> None:
    ground_truth = _pose_trajectory([(1.0, 2.0, 3.0), (1.5, 2.5, 3.5), (2.0, 3.0, 4.0)])
    arcore = _pose_trajectory([(10.0, 20.0, 30.0), (10.5, 20.5, 30.5), (11.0, 21.0, 31.0)])

    rebased = build_advio_comparison_trajectories(
        ground_truth=ground_truth,
        arcore=arcore,
        arkit=None,
        pose_frame_mode=AdvioPoseFrameMode.LOCAL_FIRST_POSE,
    )

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
