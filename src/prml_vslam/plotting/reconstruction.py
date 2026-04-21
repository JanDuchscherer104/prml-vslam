"""Plotly builders for persisted reconstruction artifacts."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import open3d as o3d
import plotly.graph_objects as go

from prml_vslam.utils import BaseData

from .theme import apply_standard_3d_layout

DEFAULT_MAX_POINTS = 80_000
DEFAULT_TARGET_TRIANGLES = 120_000
DEFAULT_MESH_COLOR = "#2f6fed"
DEFAULT_MESH_OPACITY = 0.72


class ReconstructionVisualizationSummary(BaseData):
    """Summary of one rendered reconstruction artifact view."""

    artifact_root: Path
    """Run artifact root used to resolve the reconstruction artifacts."""

    cloud_path: Path
    """Reference point-cloud path."""

    mesh_path: Path
    """Reference mesh path."""

    point_count: int
    """Number of points in the source cloud."""

    plotted_point_count: int
    """Number of points included in the Plotly figure."""

    vertex_count: int
    """Number of vertices in the source mesh."""

    triangle_count: int
    """Number of triangles in the source mesh."""

    plotted_triangle_count: int
    """Number of triangles included in the Plotly figure."""

    bounds_min_xyz: tuple[float, float, float]
    """Minimum XYZ bounds across the source cloud and mesh."""

    bounds_max_xyz: tuple[float, float, float]
    """Maximum XYZ bounds across the source cloud and mesh."""


def build_reference_reconstruction_figure(
    artifact_root: Path,
    *,
    show_point_cloud: bool = True,
    show_mesh: bool = True,
    max_points: int = DEFAULT_MAX_POINTS,
    target_triangles: int = DEFAULT_TARGET_TRIANGLES,
    mesh_color: str = DEFAULT_MESH_COLOR,
    mesh_opacity: float = DEFAULT_MESH_OPACITY,
    random_seed: int = 43,
) -> tuple[go.Figure, ReconstructionVisualizationSummary]:
    """Build an interactive Plotly view for reference reconstruction PLY artifacts."""
    if not show_point_cloud and not show_mesh:
        raise ValueError("Select at least one reconstruction modality to render.")
    resolved_root = artifact_root.expanduser().resolve()
    cloud_path = resolved_root / "reference" / "reference_cloud.ply"
    mesh_path = resolved_root / "reference" / "reference_mesh.ply"

    points_xyz = _load_point_cloud(cloud_path) if show_point_cloud else None
    mesh_vertices_xyz: np.ndarray | None = None
    mesh_triangles: np.ndarray | None = None
    if show_mesh:
        mesh_vertices_xyz, mesh_triangles = _load_mesh(mesh_path)

    points_view = (
        None if points_xyz is None else _sample_points(points_xyz, max_points=max_points, random_seed=random_seed)
    )
    mesh_vertices_view: np.ndarray | None = None
    mesh_triangles_view: np.ndarray | None = None
    if mesh_vertices_xyz is not None and mesh_triangles is not None:
        mesh_vertices_view, mesh_triangles_view = _decimate_mesh(
            vertices_xyz=mesh_vertices_xyz,
            triangles=mesh_triangles,
            target_triangles=target_triangles,
        )
    bounds_min, bounds_max = _combined_bounds(
        *(positions for positions in (points_xyz, mesh_vertices_xyz) if positions is not None)
    )
    figure = _build_figure(
        points_view=points_view,
        points_total=0 if points_xyz is None else len(points_xyz),
        mesh_vertices=mesh_vertices_view,
        mesh_triangles=mesh_triangles_view,
        mesh_color=mesh_color,
        mesh_opacity=mesh_opacity,
    )
    return figure, ReconstructionVisualizationSummary(
        artifact_root=resolved_root,
        cloud_path=cloud_path,
        mesh_path=mesh_path,
        point_count=0 if points_xyz is None else len(points_xyz),
        plotted_point_count=0 if points_view is None else len(points_view),
        vertex_count=0 if mesh_vertices_xyz is None else len(mesh_vertices_xyz),
        triangle_count=0 if mesh_triangles is None else len(mesh_triangles),
        plotted_triangle_count=0 if mesh_triangles_view is None else len(mesh_triangles_view),
        bounds_min_xyz=tuple(float(value) for value in bounds_min),
        bounds_max_xyz=tuple(float(value) for value in bounds_max),
    )


def _load_point_cloud(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(f"Reference point cloud does not exist: {path}")
    point_cloud = o3d.io.read_point_cloud(path)
    points_xyz = np.asarray(point_cloud.points, dtype=np.float32)
    if points_xyz.ndim != 2 or points_xyz.shape[1] != 3 or len(points_xyz) == 0:
        raise ValueError(f"Expected a non-empty point cloud with shape (N, 3), got {points_xyz.shape}.")
    if not np.all(np.isfinite(points_xyz)):
        raise ValueError(f"Reference point cloud contains non-finite values: {path}")
    return points_xyz


def _load_mesh(path: Path) -> tuple[np.ndarray, np.ndarray]:
    if not path.exists():
        raise FileNotFoundError(f"Reference mesh does not exist: {path}")
    mesh = o3d.io.read_triangle_mesh(path)
    vertices_xyz = np.asarray(mesh.vertices, dtype=np.float32)
    triangles = np.asarray(mesh.triangles, dtype=np.int32)
    if vertices_xyz.ndim != 2 or vertices_xyz.shape[1] != 3 or len(vertices_xyz) == 0:
        raise ValueError(f"Expected a non-empty mesh vertex array with shape (N, 3), got {vertices_xyz.shape}.")
    if triangles.ndim != 2 or triangles.shape[1] != 3 or len(triangles) == 0:
        raise ValueError(f"Expected a non-empty mesh triangle array with shape (N, 3), got {triangles.shape}.")
    if not np.all(np.isfinite(vertices_xyz)):
        raise ValueError(f"Reference mesh contains non-finite vertices: {path}")
    return vertices_xyz, triangles


def _sample_points(points_xyz: np.ndarray, *, max_points: int, random_seed: int) -> np.ndarray:
    if max_points <= 0 or len(points_xyz) <= max_points:
        return points_xyz
    rng = np.random.default_rng(random_seed)
    return points_xyz[rng.choice(len(points_xyz), size=max_points, replace=False)]


def _decimate_mesh(
    *,
    vertices_xyz: np.ndarray,
    triangles: np.ndarray,
    target_triangles: int,
) -> tuple[np.ndarray, np.ndarray]:
    if target_triangles <= 0 or len(triangles) <= target_triangles:
        return vertices_xyz, triangles
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(np.asarray(vertices_xyz, dtype=np.float64))
    mesh.triangles = o3d.utility.Vector3iVector(np.asarray(triangles, dtype=np.int32))
    decimated = mesh.simplify_quadric_decimation(target_number_of_triangles=target_triangles)
    return (
        np.asarray(decimated.vertices, dtype=np.float32),
        np.asarray(decimated.triangles, dtype=np.int32),
    )


def _combined_bounds(*position_arrays: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    positions = np.concatenate(position_arrays, axis=0)
    return positions.min(axis=0), positions.max(axis=0)


def _build_figure(
    *,
    points_view: np.ndarray | None,
    points_total: int,
    mesh_vertices: np.ndarray | None,
    mesh_triangles: np.ndarray | None,
    mesh_color: str,
    mesh_opacity: float,
) -> go.Figure:
    figure = go.Figure()
    if mesh_vertices is not None and mesh_triangles is not None:
        figure.add_trace(
            go.Mesh3d(
                x=mesh_vertices[:, 0],
                y=mesh_vertices[:, 1],
                z=mesh_vertices[:, 2],
                i=mesh_triangles[:, 0],
                j=mesh_triangles[:, 1],
                k=mesh_triangles[:, 2],
                name=f"TSDF mesh ({len(mesh_triangles):,} triangles)",
                color=mesh_color,
                opacity=mesh_opacity,
            )
        )
    if points_view is not None:
        figure.add_trace(
            go.Scatter3d(
                x=points_view[:, 0],
                y=points_view[:, 1],
                z=points_view[:, 2],
                mode="markers",
                name=f"TSDF points ({len(points_view):,}/{points_total:,})",
                marker={
                    "size": 1.5,
                    "color": points_view[:, 2],
                    "colorscale": "Viridis",
                    "opacity": 0.8,
                },
            )
        )
    apply_standard_3d_layout(
        figure,
        title="Reference Reconstruction",
        scene={
            "aspectmode": "data",
            "xaxis_title": "X",
            "yaxis_title": "Y",
            "zaxis_title": "Z",
        },
    )
    return figure


__all__ = [
    "DEFAULT_MESH_COLOR",
    "DEFAULT_MESH_OPACITY",
    "DEFAULT_MAX_POINTS",
    "DEFAULT_TARGET_TRIANGLES",
    "ReconstructionVisualizationSummary",
    "build_reference_reconstruction_figure",
]
