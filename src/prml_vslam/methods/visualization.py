"""Minimal visualization helpers for mock method outputs."""

from __future__ import annotations

from pathlib import Path


def write_plotly_scene_html(
    *,
    output_path: Path,
    point_cloud_path: Path,
    trajectory_path: Path,
    view_graph_path: Path | None = None,
    max_points: int = 50_000,
) -> Path:
    """Persist a tiny HTML stub that records the requested artifact paths."""
    del max_points
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        (
            "<html><body>"
            "<h1>Mock Method Scene</h1>"
            f"<p>Point cloud: {point_cloud_path.name}</p>"
            f"<p>Trajectory: {trajectory_path.name}</p>"
            f"<p>View graph: {None if view_graph_path is None else view_graph_path.name}</p>"
            "</body></html>"
        ),
        encoding="utf-8",
    )
    return output_path.resolve()


def show_open3d_scene(
    *,
    point_cloud_path: Path,
    trajectory_path: Path,
    view_graph_path: Path | None = None,
) -> None:
    """Fail clearly because real 3D viewers are out of scope for the mock package."""
    del point_cloud_path, trajectory_path, view_graph_path
    raise RuntimeError("Open3D viewing is not implemented for the repository-local method mocks.")


__all__ = ["show_open3d_scene", "write_plotly_scene_html"]
