"""Diagnostics derived from ViSTA-native persisted artifacts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path

import numpy as np
from pydantic import Field

from prml_vslam.eval.contracts import IntrinsicsComparisonDiagnostics
from prml_vslam.eval.intrinsics import compare_camera_intrinsics_series
from prml_vslam.interfaces.camera import (
    CameraIntrinsicsSeries,
    center_crop_resize_intrinsics,
    load_camera_intrinsics_yaml,
)
from prml_vslam.methods.vista.artifact_io import (
    VistaViewGraphArtifact,
    load_vista_confidences,
    load_vista_estimated_intrinsics_series,
    load_vista_intrinsics_matrices,
    load_vista_native_trajectory,
    load_vista_vector,
    load_vista_view_graph,
)
from prml_vslam.utils import BaseData, RunArtifactPaths
from prml_vslam.utils.geometry import load_tum_trajectory

_VISTA_MODEL_RASTER_SIZE_PX = 224


class VistaViewGraphEdge(BaseData):
    """One undirected edge in the native ViSTA view graph."""

    source: int
    """Source keyframe index."""

    target: int
    """Target keyframe index."""

    frame_gap: int
    """Absolute frame-index gap between endpoints."""


class VistaViewGraphNodeDegree(BaseData):
    """Degree summary for one view-graph node."""

    node: int
    """Keyframe index."""

    degree: int
    """Number of adjacent view-graph nodes."""


class VistaViewGraphDiagnostics(BaseData):
    """Summary of the native ViSTA view graph."""

    node_count: int
    """Number of view-graph nodes."""

    edge_count: int
    """Number of undirected view-graph edges."""

    loop_min_dist: int | None = None
    """Native loop minimum frame-distance setting, when available."""

    degree_by_node: list[int] = Field(default_factory=list)
    """Per-node degree values in node-index order."""

    edge_gaps: list[int] = Field(default_factory=list)
    """Per-edge absolute frame-index gaps."""

    loop_edges: list[VistaViewGraphEdge] = Field(default_factory=list)
    """Edges whose frame gap exceeds the loop threshold."""

    top_degree_nodes: list[VistaViewGraphNodeDegree] = Field(default_factory=list)
    """Most connected nodes, sorted by descending degree."""


class VistaNativeSlamDiagnostics(BaseData):
    """Diagnostic summary derived from native ViSTA outputs."""

    keyframe_indices: list[int]
    """Native keyframe indices shared by per-keyframe arrays."""

    confidence_threshold: float | None = None
    """Confidence threshold stored in `confs.npz`."""

    estimated_intrinsics: CameraIntrinsicsSeries | None = None
    """Standardized estimated intrinsics series, when available."""

    intrinsics_comparison: IntrinsicsComparisonDiagnostics | None = None
    """Estimated-vs-reference intrinsics comparison in model raster space."""

    confidence_mean: list[float] = Field(default_factory=list)
    """Mean confidence per keyframe."""

    confidence_p90: list[float] = Field(default_factory=list)
    """90th percentile confidence per keyframe."""

    confidence_valid_ratio: list[float] = Field(default_factory=list)
    """Per-keyframe fraction of confidence pixels above threshold."""

    scales: list[float] = Field(default_factory=list)
    """Native per-keyframe Sim(3) scale estimates."""

    fx: list[float] = Field(default_factory=list)
    """Per-keyframe focal length x from native intrinsics."""

    fy: list[float] = Field(default_factory=list)
    """Per-keyframe focal length y from native intrinsics."""

    cx: list[float] = Field(default_factory=list)
    """Per-keyframe principal point x from native intrinsics."""

    cy: list[float] = Field(default_factory=list)
    """Per-keyframe principal point y from native intrinsics."""

    native_positions_xyz: list[tuple[float, float, float]] = Field(default_factory=list)
    """Native trajectory positions from `trajectory.npy`."""

    native_step_distance_m: list[float] = Field(default_factory=list)
    """Per-step translation distance in native trajectory order."""

    slam_sample_intervals_s: list[float] = Field(default_factory=list)
    """Timestamp spacing from normalized `slam/trajectory.tum`."""

    view_graph: VistaViewGraphDiagnostics | None = None
    """Native view-graph summary."""


def load_vista_native_slam_diagnostics(artifact_root: Path) -> VistaNativeSlamDiagnostics:
    """Load lightweight diagnostic summaries from native ViSTA artifacts."""
    run_paths = RunArtifactPaths.build(artifact_root)
    native_dir = run_paths.native_output_dir

    confs, confidence_threshold = load_vista_confidences(native_dir / "confs.npz")
    keyframe_count = int(confs.shape[0])
    keyframe_indices = list(range(keyframe_count))
    confidence_flat = confs.reshape(keyframe_count, -1)
    confidence_mean = _float_list(confidence_flat.mean(axis=1))
    confidence_p90 = _float_list(np.percentile(confidence_flat, 90, axis=1))
    confidence_valid_ratio = (
        _float_list((confidence_flat > confidence_threshold).mean(axis=1)) if confidence_threshold is not None else []
    )

    scales = load_vista_vector(native_dir / "scales.npy", expected_length=keyframe_count, name="scales")
    estimated_intrinsics = load_vista_estimated_intrinsics_series(run_paths.estimated_intrinsics_path)
    if estimated_intrinsics is None:
        intrinsics = load_vista_intrinsics_matrices(native_dir / "intrinsics.npy", expected_length=keyframe_count)
        estimated_intrinsics = CameraIntrinsicsSeries.from_matrices(
            intrinsics,
            raster_space="vista_model",
            source="native/intrinsics.npy",
            method_id="vista",
            width_px=_VISTA_MODEL_RASTER_SIZE_PX,
            height_px=_VISTA_MODEL_RASTER_SIZE_PX,
            keyframe_indices=keyframe_indices,
            metadata={"fallback": True},
        )
    else:
        intrinsics = np.asarray(
            [sample.intrinsics.as_matrix() for sample in estimated_intrinsics.samples],
            dtype=np.float64,
        )
        if len(intrinsics) != keyframe_count:
            raise ValueError(f"Expected {keyframe_count} standardized intrinsics samples, got {len(intrinsics)}.")
    native_positions, native_step_distance = load_vista_native_trajectory(
        native_dir / "trajectory.npy",
        expected_length=keyframe_count,
    )
    slam_sample_intervals = _load_slam_sample_intervals(run_paths.trajectory_path)
    view_graph_artifact = load_vista_view_graph(native_dir / "view_graph.npz")
    view_graph = _summarize_view_graph(view_graph_artifact)
    intrinsics_comparison = None
    if run_paths.input_intrinsics_path.exists() and estimated_intrinsics.samples:
        reference_model_intrinsics = center_crop_resize_intrinsics(
            load_camera_intrinsics_yaml(run_paths.input_intrinsics_path),
            output_width_px=_VISTA_MODEL_RASTER_SIZE_PX,
            output_height_px=_VISTA_MODEL_RASTER_SIZE_PX,
            border_x_px=10,
            border_y_px=10,
        )
        intrinsics_comparison = compare_camera_intrinsics_series(
            estimated_intrinsics=estimated_intrinsics,
            reference=reference_model_intrinsics,
        )

    return VistaNativeSlamDiagnostics(
        keyframe_indices=keyframe_indices,
        confidence_threshold=confidence_threshold,
        estimated_intrinsics=estimated_intrinsics,
        intrinsics_comparison=intrinsics_comparison,
        confidence_mean=confidence_mean,
        confidence_p90=confidence_p90,
        confidence_valid_ratio=confidence_valid_ratio,
        scales=_float_list(scales),
        fx=_float_list(intrinsics[:, 0, 0]),
        fy=_float_list(intrinsics[:, 1, 1]),
        cx=_float_list(intrinsics[:, 0, 2]),
        cy=_float_list(intrinsics[:, 1, 2]),
        native_positions_xyz=[tuple(float(value) for value in row) for row in native_positions],
        native_step_distance_m=_float_list(native_step_distance),
        slam_sample_intervals_s=_float_list(slam_sample_intervals),
        view_graph=view_graph,
    )


def _load_slam_sample_intervals(path: Path) -> np.ndarray:
    if not path.exists():
        return np.empty(0, dtype=np.float64)
    trajectory = load_tum_trajectory(path)
    timestamps = np.asarray(trajectory.timestamps, dtype=np.float64)
    return np.diff(timestamps) if len(timestamps) > 1 else np.empty(0, dtype=np.float64)


def _summarize_view_graph(artifact: VistaViewGraphArtifact) -> VistaViewGraphDiagnostics:
    degrees = {node: len(neighbors) for node, neighbors in artifact.view_graph.items()}
    edges = _view_graph_edges(artifact.view_graph)
    loop_edges = [
        VistaViewGraphEdge(source=source, target=target, frame_gap=gap)
        for source, target, gap in edges
        if artifact.loop_min_dist is not None and gap > artifact.loop_min_dist
    ]
    top_degree_nodes = [
        VistaViewGraphNodeDegree(node=node, degree=degree)
        for node, degree in sorted(degrees.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]
    return VistaViewGraphDiagnostics(
        node_count=len(degrees),
        edge_count=len(edges),
        loop_min_dist=artifact.loop_min_dist,
        degree_by_node=[degrees[node] for node in sorted(degrees)],
        edge_gaps=[gap for _, _, gap in edges],
        loop_edges=loop_edges,
        top_degree_nodes=top_degree_nodes,
    )


def _view_graph_edges(view_graph: Mapping[int, Iterable[int]]) -> list[tuple[int, int, int]]:
    edges: list[tuple[int, int, int]] = []
    for source, neighbors in view_graph.items():
        for target in neighbors:
            if source < target:
                edges.append((source, target, abs(target - source)))
    return sorted(edges)


def _float_list(values: np.ndarray) -> list[float]:
    return np.asarray(values, dtype=np.float64).reshape(-1).tolist()


__all__ = [
    "VistaNativeSlamDiagnostics",
    "VistaViewGraphDiagnostics",
    "VistaViewGraphEdge",
    "VistaViewGraphNodeDegree",
    "load_vista_native_slam_diagnostics",
]
