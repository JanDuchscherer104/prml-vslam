"""Plotly figure builders for the packaged Streamlit app."""

from .advio import (
    build_advio_comparison_trajectories,
    build_crowd_density_figure,
    build_local_readiness_figure,
    build_scene_attribute_figure,
    build_scene_mix_figure,
)
from .artifact_diagnostics import (
    build_intrinsics_residual_figure,
    build_native_confidence_figure,
    build_native_intrinsics_figure,
    build_native_scale_figure,
    build_native_timing_figure,
    build_view_graph_figure,
)
from .metrics import build_error_figure, build_trajectory_figure
from .pipeline import build_evo_ape_colormap_figure
from .reconstruction import (
    DEFAULT_MAX_POINTS,
    DEFAULT_MESH_COLOR,
    DEFAULT_MESH_OPACITY,
    DEFAULT_TARGET_TRIANGLES,
    ReconstructionVisualizationSummary,
    SlamReferenceComparisonSummary,
    build_reference_reconstruction_figure,
    build_slam_reference_comparison_figure,
)
from .record3d import build_live_trajectory_figure
from .trajectories import (
    build_3d_trajectory_figure,
    build_bev_trajectory_figure,
    build_height_profile_figure,
    build_sample_interval_figure,
    build_speed_profile_figure,
    trajectory_length_m,
)

__all__ = [
    "build_3d_trajectory_figure",
    "build_advio_comparison_trajectories",
    "build_bev_trajectory_figure",
    "build_crowd_density_figure",
    "build_error_figure",
    "build_evo_ape_colormap_figure",
    "build_height_profile_figure",
    "build_intrinsics_residual_figure",
    "build_live_trajectory_figure",
    "build_local_readiness_figure",
    "build_native_confidence_figure",
    "build_native_intrinsics_figure",
    "build_native_scale_figure",
    "build_native_timing_figure",
    "build_reference_reconstruction_figure",
    "build_sample_interval_figure",
    "build_scene_attribute_figure",
    "build_scene_mix_figure",
    "build_slam_reference_comparison_figure",
    "build_speed_profile_figure",
    "build_trajectory_figure",
    "build_view_graph_figure",
    "DEFAULT_MESH_COLOR",
    "DEFAULT_MESH_OPACITY",
    "DEFAULT_MAX_POINTS",
    "DEFAULT_TARGET_TRIANGLES",
    "ReconstructionVisualizationSummary",
    "SlamReferenceComparisonSummary",
    "trajectory_length_m",
]
