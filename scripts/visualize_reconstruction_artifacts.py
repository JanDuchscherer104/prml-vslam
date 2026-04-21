#!/usr/bin/env python3
"""Render reconstruction-stage PLY artifacts into a browser-friendly HTML view.

Usage:
    uv run --extra vista python scripts/visualize_reconstruction_artifacts.py \
      .artifacts/vista-full-tuning/vista --open-browser
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import webbrowser
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import open3d as o3d
import plotly.graph_objects as go


DEFAULT_OUTPUT_NAME = "reference_reconstruction_plotly.html"
DEFAULT_MAX_POINTS = 80_000
DEFAULT_TARGET_TRIANGLES = 120_000


@dataclass(frozen=True, slots=True)
class ReconstructionVisualizationSummary:
    """Summary of one generated reconstruction HTML view."""

    artifact_root: Path
    cloud_path: Path
    mesh_path: Path
    output_path: Path
    point_count: int
    plotted_point_count: int
    vertex_count: int
    triangle_count: int
    plotted_triangle_count: int
    bounds_min_xyz: tuple[float, float, float]
    bounds_max_xyz: tuple[float, float, float]


def render_reconstruction_html(
    artifact_root: Path,
    *,
    output_path: Path | None = None,
    max_points: int = DEFAULT_MAX_POINTS,
    target_triangles: int = DEFAULT_TARGET_TRIANGLES,
    random_seed: int = 43,
) -> ReconstructionVisualizationSummary:
    """Render reference reconstruction PLY artifacts as an interactive Plotly HTML file."""
    artifact_root = artifact_root.expanduser().resolve()
    cloud_path = artifact_root / "reference" / "reference_cloud.ply"
    mesh_path = artifact_root / "reference" / "reference_mesh.ply"
    output_path = (
        artifact_root / "visualization" / DEFAULT_OUTPUT_NAME if output_path is None else output_path.expanduser()
    ).resolve()

    points_xyz = _load_point_cloud(cloud_path)
    mesh_vertices_xyz, mesh_triangles = _load_mesh(mesh_path)
    points_view = _sample_points(points_xyz, max_points=max_points, random_seed=random_seed)
    mesh_vertices_view, mesh_triangles_view = _decimate_mesh(
        vertices_xyz=mesh_vertices_xyz,
        triangles=mesh_triangles,
        target_triangles=target_triangles,
    )

    bounds_min, bounds_max = _combined_bounds(points_xyz, mesh_vertices_xyz)
    figure = _build_figure(
        points_view=points_view,
        points_total=len(points_xyz),
        mesh_vertices=mesh_vertices_view,
        mesh_triangles=mesh_triangles_view,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(output_path, include_plotlyjs=True)
    return ReconstructionVisualizationSummary(
        artifact_root=artifact_root,
        cloud_path=cloud_path,
        mesh_path=mesh_path,
        output_path=output_path,
        point_count=len(points_xyz),
        plotted_point_count=len(points_view),
        vertex_count=len(mesh_vertices_xyz),
        triangle_count=len(mesh_triangles),
        plotted_triangle_count=len(mesh_triangles_view),
        bounds_min_xyz=tuple(float(value) for value in bounds_min),
        bounds_max_xyz=tuple(float(value) for value in bounds_max),
    )


def _load_point_cloud(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(f"Reference point cloud does not exist: {path}")
    point_cloud = o3d.io.read_point_cloud(str(path))
    points_xyz = np.asarray(point_cloud.points, dtype=np.float32)
    if points_xyz.ndim != 2 or points_xyz.shape[1] != 3 or len(points_xyz) == 0:
        raise ValueError(f"Expected a non-empty point cloud with shape (N, 3), got {points_xyz.shape}.")
    if not np.all(np.isfinite(points_xyz)):
        raise ValueError(f"Reference point cloud contains non-finite values: {path}")
    return points_xyz


def _load_mesh(path: Path) -> tuple[np.ndarray, np.ndarray]:
    if not path.exists():
        raise FileNotFoundError(f"Reference mesh does not exist: {path}")
    mesh = o3d.io.read_triangle_mesh(str(path))
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


def _combined_bounds(points_xyz: np.ndarray, vertices_xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    positions = np.concatenate([points_xyz, vertices_xyz], axis=0)
    return positions.min(axis=0), positions.max(axis=0)


def _build_figure(
    *,
    points_view: np.ndarray,
    points_total: int,
    mesh_vertices: np.ndarray,
    mesh_triangles: np.ndarray,
) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(
        go.Mesh3d(
            x=mesh_vertices[:, 0],
            y=mesh_vertices[:, 1],
            z=mesh_vertices[:, 2],
            i=mesh_triangles[:, 0],
            j=mesh_triangles[:, 1],
            k=mesh_triangles[:, 2],
            name=f"TSDF mesh ({len(mesh_triangles):,} triangles)",
            color="lightsteelblue",
            opacity=0.65,
        )
    )
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
    figure.update_layout(
        title="Reference Reconstruction",
        scene={
            "aspectmode": "data",
            "xaxis_title": "x",
            "yaxis_title": "y",
            "zaxis_title": "z",
        },
        margin={"l": 0, "r": 0, "t": 48, "b": 0},
    )
    return figure


def _open_browser(path: Path) -> None:
    if shutil.which("explorer.exe") and shutil.which("wslpath"):
        completed = subprocess.run(
            ["wslpath", "-w", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(["explorer.exe", completed.stdout.strip()], check=False)
        return
    webbrowser.open(path.resolve().as_uri())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_root", type=Path, help="Run artifact root, e.g. .artifacts/<run>/<method>.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help=f"Output HTML path. Defaults to <artifact_root>/visualization/{DEFAULT_OUTPUT_NAME}.",
    )
    parser.add_argument("--max-points", type=int, default=DEFAULT_MAX_POINTS, help="Maximum cloud points to plot.")
    parser.add_argument(
        "--target-triangles",
        type=int,
        default=DEFAULT_TARGET_TRIANGLES,
        help="Target mesh triangle count for Plotly rendering; set <=0 to disable decimation.",
    )
    parser.add_argument("--seed", type=int, default=43, help="Random seed for point-cloud downsampling.")
    parser.add_argument("--open-browser", action="store_true", help="Open the generated HTML in a browser.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line renderer."""
    args = _build_parser().parse_args(argv)
    summary = render_reconstruction_html(
        args.artifact_root,
        output_path=args.output,
        max_points=args.max_points,
        target_triangles=args.target_triangles,
        random_seed=args.seed,
    )
    print(f"html_path={summary.output_path}")
    print(f"cloud_path={summary.cloud_path}")
    print(f"mesh_path={summary.mesh_path}")
    print(f"point_count={summary.point_count}")
    print(f"plotted_point_count={summary.plotted_point_count}")
    print(f"vertex_count={summary.vertex_count}")
    print(f"triangle_count={summary.triangle_count}")
    print(f"plotted_triangle_count={summary.plotted_triangle_count}")
    print(f"bounds_min={list(summary.bounds_min_xyz)}")
    print(f"bounds_max={list(summary.bounds_max_xyz)}")
    if args.open_browser:
        _open_browser(summary.output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
