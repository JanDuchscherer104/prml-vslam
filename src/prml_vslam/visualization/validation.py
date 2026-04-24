"""Deterministic validation helpers for repo-owned Rerun recordings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np
import rerun as rr  # type: ignore[import-not-found]
import rerun.dataframe as rdf  # type: ignore[import-not-found]
from pydantic import Field

from prml_vslam.interfaces import FrameTransform
from prml_vslam.utils import BaseData

matplotlib.use("Agg")
import matplotlib.pyplot as plt

_LIVE_MODEL_POINTS_ENTITY = "/world/live/model/points"
_TRACKING_CAMERA_ENTITY = "/world/live/tracking/camera"
_KEYED_POINTS_PREFIX = "/world/keyframes/points/"
_KEYED_CAMERAS_PREFIX = "/world/keyframes/cameras/"
_RECONSTRUCTION_PREFIX = "/world/reconstruction/"
_REFERENCE_PREFIX = "/world/reference/"


class RerunPointCloudSnapshot(BaseData):
    """Summary of one populated point-cloud entity in a recording."""

    entity_path: str
    index_name: str
    index_value: int
    point_count: int
    bounds_min_xyz: tuple[float, float, float]
    bounds_max_xyz: tuple[float, float, float]


class RerunValidationSummary(BaseData):
    """Deterministic semantic summary extracted from one `.rrd` recording."""

    recording_path: Path
    entity_paths: list[str] = Field(default_factory=list)
    live_model_points: RerunPointCloudSnapshot | None = None
    keyed_point_clouds: list[RerunPointCloudSnapshot] = Field(default_factory=list)
    reconstruction_point_clouds: list[RerunPointCloudSnapshot] = Field(default_factory=list)
    reference_point_clouds: list[RerunPointCloudSnapshot] = Field(default_factory=list)
    reference_trajectory_entities: list[str] = Field(default_factory=list)
    keyed_camera_entities: list[str] = Field(default_factory=list)
    tracking_positions_xyz: list[tuple[float, float, float]] = Field(default_factory=list)


class RerunValidationArtifacts(BaseData):
    """Artifacts emitted by the repo-owned validation loop."""

    summary_json: Path
    summary_markdown: Path
    map_xy_png: Path
    map_xz_png: Path


def load_recording_summary(recording_path: Path) -> RerunValidationSummary:
    """Load one `.rrd` and summarize the current repo-owned Rerun surfaces."""
    recording = rdf.load_recording(recording_path)
    entity_paths = sorted({column.entity_path for column in recording.schema().component_columns()})

    live_model_snapshot, _ = _latest_live_model_snapshot(recording)
    keyed_snapshots, _ = _keyed_point_cloud_snapshots(recording)
    reconstruction_snapshots, _ = _reconstruction_point_cloud_snapshots(recording)
    reference_snapshots = _reference_point_cloud_snapshots(recording)
    return RerunValidationSummary(
        recording_path=recording_path.resolve(),
        entity_paths=entity_paths,
        live_model_points=live_model_snapshot,
        keyed_point_clouds=keyed_snapshots,
        reconstruction_point_clouds=reconstruction_snapshots,
        reference_point_clouds=reference_snapshots,
        reference_trajectory_entities=_reference_trajectory_entities(recording),
        keyed_camera_entities=sorted(
            path
            for path in entity_paths
            if path.startswith(_KEYED_CAMERAS_PREFIX) and "/" not in path.removeprefix(_KEYED_CAMERAS_PREFIX)
        ),
        tracking_positions_xyz=_tracking_positions(recording),
    )


def write_validation_bundle(
    recording_path: Path,
    *,
    output_dir: Path,
    max_keyed_clouds: int = 20,
    max_render_points: int = 30_000,
) -> RerunValidationArtifacts:
    """Write a deterministic validation bundle for one `.rrd` recording."""
    recording = rdf.load_recording(recording_path)
    summary = load_recording_summary(recording_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    live_snapshot, live_world_points = _latest_live_model_snapshot(recording)
    keyed_snapshots, keyed_world_points = _keyed_point_cloud_snapshots(recording, max_keyed_clouds=max_keyed_clouds)
    reconstruction_snapshots, reconstruction_world_points = _reconstruction_point_cloud_snapshots(recording)
    tracking_positions = np.asarray(summary.tracking_positions_xyz, dtype=np.float64).reshape(-1, 3)

    summary = summary.model_copy(
        update={
            "live_model_points": live_snapshot,
            "keyed_point_clouds": keyed_snapshots,
            "reconstruction_point_clouds": reconstruction_snapshots,
            "reference_point_clouds": _reference_point_cloud_snapshots(recording),
            "reference_trajectory_entities": _reference_trajectory_entities(recording),
        }
    )

    summary_json = output_dir / "summary.json"
    summary_json.write_text(summary.model_dump_json(indent=2), encoding="utf-8")

    summary_markdown = output_dir / "summary.md"
    summary_markdown.write_text(_summary_markdown(summary), encoding="utf-8")

    map_xy_png = output_dir / "map_xy.png"
    _write_projection_plot(
        output_path=map_xy_png,
        live_world_points=live_world_points,
        keyed_world_points=[*keyed_world_points, *reconstruction_world_points],
        tracking_positions_xyz=tracking_positions,
        axis_x=0,
        axis_y=1,
        x_label="world x",
        y_label="world y",
        title="Rerun Validation Map (XY)",
        max_render_points=max_render_points,
    )

    map_xz_png = output_dir / "map_xz.png"
    _write_projection_plot(
        output_path=map_xz_png,
        live_world_points=live_world_points,
        keyed_world_points=[*keyed_world_points, *reconstruction_world_points],
        tracking_positions_xyz=tracking_positions,
        axis_x=0,
        axis_y=2,
        x_label="world x",
        y_label="world z",
        title="Rerun Validation Map (XZ)",
        max_render_points=max_render_points,
    )

    return RerunValidationArtifacts(
        summary_json=summary_json.resolve(),
        summary_markdown=summary_markdown.resolve(),
        map_xy_png=map_xy_png.resolve(),
        map_xz_png=map_xz_png.resolve(),
    )


def main(argv: list[str] | None = None) -> int:
    """Run the validation loop on one `.rrd` recording and print the artifact paths."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording_path", type=Path, help="Path to one repo-owned or native `.rrd` recording.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory where validation artifacts should be written. Defaults to '<recording>/validation'.",
    )
    parser.add_argument(
        "--max-keyed-clouds",
        type=int,
        default=20,
        help="Maximum number of keyed clouds to include in rendered overview plots.",
    )
    parser.add_argument(
        "--max-render-points",
        type=int,
        default=30_000,
        help="Maximum number of points to draw per cloud in rendered overview plots.",
    )
    args = parser.parse_args(argv)

    recording_path = args.recording_path.expanduser().resolve()
    output_dir = (
        args.output_dir.expanduser().resolve() if args.output_dir is not None else recording_path.parent / "validation"
    )
    artifacts = write_validation_bundle(
        recording_path,
        output_dir=output_dir,
        max_keyed_clouds=args.max_keyed_clouds,
        max_render_points=args.max_render_points,
    )
    print(json.dumps(artifacts.model_dump(mode="json"), indent=2))
    return 0


def _component_columns(recording: rdf.Recording):
    return list(recording.schema().component_columns())


def _rows_for_index(recording: rdf.Recording, *, index_name: str, contents: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    reader = recording.view(index=index_name, contents=contents).select()
    for batch in reader:
        data = batch.to_pydict()
        if not data:
            continue
        row_count = len(next(iter(data.values())))
        for row_index in range(row_count):
            rows.append({column: values[row_index] for column, values in data.items()})
    return rows


def _static_rows(recording: rdf.Recording, *, contents: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    reader = recording.view(index="log_tick", contents=contents).select_static()
    for batch in reader:
        data = batch.to_pydict()
        if not data:
            continue
        row_count = len(next(iter(data.values())))
        for row_index in range(row_count):
            rows.append({column: values[row_index] for column, values in data.items()})
    return rows


def _unwrap_component(value: object | None) -> np.ndarray | None:
    if value is None:
        return None
    array = np.asarray(value, dtype=np.float64)
    if array.size == 0:
        return None
    while array.ndim > 2 and array.shape[0] == 1:
        array = array[0]
    return array


def _single_vector(value: object | None) -> np.ndarray | None:
    array = _unwrap_component(value)
    if array is None:
        return None
    if array.ndim == 2 and array.shape[0] == 1:
        return array[0]
    return array


def _points_array(value: object | None) -> np.ndarray:
    array = _unwrap_component(value)
    if array is None or array.ndim < 2 or array.shape[-1] != 3:
        return np.empty((0, 3), dtype=np.float64)
    return np.asarray(array, dtype=np.float64).reshape(-1, 3)


def _transform_matrix_from_row(row: dict[str, object], *, entity_path: str) -> np.ndarray | None:
    translation = _single_vector(row.get(f"{entity_path}:Transform3D:translation"))
    quaternion_xyzw = _single_vector(row.get(f"{entity_path}:Transform3D:quaternion"))
    mat3x3 = _single_vector(row.get(f"{entity_path}:Transform3D:mat3x3"))
    relation = _single_vector(row.get(f"{entity_path}:Transform3D:relation"))

    if translation is None and quaternion_xyzw is None and mat3x3 is None and relation is None:
        return None

    matrix = np.eye(4, dtype=np.float64)
    if mat3x3 is not None:
        matrix[:3, :3] = np.asarray(mat3x3, dtype=np.float64).reshape(3, 3)
    elif quaternion_xyzw is not None:
        matrix = FrameTransform.from_quaternion_translation(
            np.asarray(quaternion_xyzw, dtype=np.float64),
            np.zeros(3, dtype=np.float64) if translation is None else np.asarray(translation, dtype=np.float64),
        ).as_matrix()
    if translation is not None:
        matrix[:3, 3] = np.asarray(translation, dtype=np.float64)

    relation_value = rr.TransformRelation.ParentFromChild.value if relation is None else int(np.asarray(relation)[0])
    if relation_value == rr.TransformRelation.ChildFromParent.value:
        matrix = np.linalg.inv(matrix)
    return matrix


def _ancestor_entity_paths(entity_path: str) -> list[str]:
    parts = entity_path.strip("/").split("/")
    return ["/" + "/".join(parts[:index]) for index in range(1, len(parts) + 1)]


def _latest_transform_matrix_before_or_at_log_tick(
    rows: list[dict[str, object]],
    *,
    entity_path: str,
    log_tick: int,
) -> np.ndarray | None:
    latest_transform: np.ndarray | None = None
    for row in rows:
        if row.get("log_tick") is None or row["log_tick"] > log_tick:
            continue
        branch_transform = _transform_matrix_from_row(row, entity_path=entity_path)
        if branch_transform is not None:
            latest_transform = branch_transform
    return latest_transform


def _world_points_for_row(
    row: dict[str, object],
    *,
    points_entity: str,
    log_tick_rows: list[dict[str, object]] | None = None,
) -> np.ndarray:
    points_xyz = _points_array(row.get(f"{points_entity}:Points3D:positions"))
    transform = np.eye(4, dtype=np.float64)
    for ancestor in _ancestor_entity_paths(points_entity):
        branch_transform = (
            _latest_transform_matrix_before_or_at_log_tick(
                log_tick_rows, entity_path=ancestor, log_tick=row["log_tick"]
            )
            if log_tick_rows is not None
            else _transform_matrix_from_row(row, entity_path=ancestor)
        )
        if branch_transform is not None:
            transform = transform @ branch_transform
    points_h = np.concatenate([points_xyz, np.ones((len(points_xyz), 1), dtype=np.float64)], axis=1)
    return (points_h @ transform.T)[:, :3]


def _latest_live_model_snapshot(
    recording: rdf.Recording,
) -> tuple[RerunPointCloudSnapshot | None, np.ndarray | None]:
    rows = _rows_for_index(recording, index_name="frame", contents="/world/live/model/**")
    latest_snapshot: RerunPointCloudSnapshot | None = None
    latest_world_points: np.ndarray | None = None
    for row in rows:
        frame_value = row.get("frame")
        if frame_value is None:
            continue
        world_points = _world_points_for_row(row, points_entity=_LIVE_MODEL_POINTS_ENTITY)
        if len(world_points) == 0:
            continue
        latest_snapshot = _point_cloud_snapshot(
            entity_path=_LIVE_MODEL_POINTS_ENTITY,
            index_name="frame",
            index_value=int(frame_value),
            world_points=world_points,
        )
        latest_world_points = world_points
    return latest_snapshot, latest_world_points


def _keyed_point_cloud_snapshots(
    recording: rdf.Recording,
    *,
    max_keyed_clouds: int | None = None,
) -> tuple[list[RerunPointCloudSnapshot], list[np.ndarray]]:
    point_entities = sorted(
        column.entity_path
        for column in _component_columns(recording)
        if column.component == "Points3D:positions" and column.entity_path.startswith(_KEYED_POINTS_PREFIX)
    )
    snapshots: list[RerunPointCloudSnapshot] = []
    world_points_payloads: list[np.ndarray] = []
    selected_entities = point_entities if max_keyed_clouds is None else point_entities[-max_keyed_clouds:]
    for points_entity in selected_entities:
        parent_entity = points_entity.removesuffix("/points")
        frame_rows = _rows_for_index(recording, index_name="frame", contents=f"{parent_entity}/**")
        latest_row: dict[str, object] | None = None
        latest_world_points: np.ndarray | None = None
        latest_index_name = "frame"
        latest_index_value: int | None = None

        for row in frame_rows:
            frame_value = row.get("frame")
            if frame_value is None:
                continue
            world_points = _world_points_for_row(row, points_entity=points_entity)
            if len(world_points) == 0:
                continue
            latest_row = row
            latest_world_points = world_points
            latest_index_value = int(frame_value)

        if latest_row is None or latest_world_points is None:
            log_tick_rows = _rows_for_index(recording, index_name="log_tick", contents=f"{parent_entity}/**")
            for row in log_tick_rows:
                if row.get("log_tick") is None:
                    continue
                world_points = _world_points_for_row(
                    row,
                    points_entity=points_entity,
                    log_tick_rows=log_tick_rows,
                )
                if len(world_points) == 0:
                    continue
                latest_row = row
                latest_world_points = world_points
                latest_index_name = "log_tick"
                latest_index_value = int(row["log_tick"])

        if latest_row is None or latest_world_points is None or latest_index_value is None:
            continue

        snapshots.append(
            _point_cloud_snapshot(
                entity_path=points_entity,
                index_name=latest_index_name,
                index_value=latest_index_value,
                world_points=latest_world_points,
            )
        )
        world_points_payloads.append(latest_world_points)
    return snapshots, world_points_payloads


def _reconstruction_point_cloud_snapshots(
    recording: rdf.Recording,
) -> tuple[list[RerunPointCloudSnapshot], list[np.ndarray]]:
    point_entities = sorted(
        column.entity_path
        for column in _component_columns(recording)
        if column.component == "Points3D:positions" and column.entity_path.startswith(_RECONSTRUCTION_PREFIX)
    )
    snapshots: list[RerunPointCloudSnapshot] = []
    world_points_payloads: list[np.ndarray] = []
    for points_entity in point_entities:
        latest_points: np.ndarray | None = None
        latest_index_name = "log_tick"
        latest_index_value = 0
        for row in _static_rows(recording, contents=points_entity):
            world_points = _points_array(row.get(f"{points_entity}:Points3D:positions"))
            if len(world_points) == 0:
                continue
            latest_points = world_points
            latest_index_name = "static"
            latest_index_value = 0
        for index_name in ("frame", "log_tick"):
            for row in _rows_for_index(recording, index_name=index_name, contents=points_entity):
                index_value = row.get(index_name)
                if index_value is None:
                    continue
                world_points = _points_array(row.get(f"{points_entity}:Points3D:positions"))
                if len(world_points) == 0:
                    continue
                latest_points = world_points
                latest_index_name = index_name
                latest_index_value = int(index_value)
        if latest_points is None:
            continue
        snapshots.append(
            _point_cloud_snapshot(
                entity_path=points_entity,
                index_name=latest_index_name,
                index_value=latest_index_value,
                world_points=latest_points,
            )
        )
        world_points_payloads.append(latest_points)
    return snapshots, world_points_payloads


def _reference_point_cloud_snapshots(recording: rdf.Recording) -> list[RerunPointCloudSnapshot]:
    point_entities = sorted(
        column.entity_path
        for column in _component_columns(recording)
        if column.component == "Points3D:positions" and column.entity_path.startswith(_REFERENCE_PREFIX)
    )
    snapshots: list[RerunPointCloudSnapshot] = []
    for points_entity in point_entities:
        latest_points: np.ndarray | None = None
        for row in _static_rows(recording, contents=points_entity):
            points = _points_array(row.get(f"{points_entity}:Points3D:positions"))
            if len(points):
                latest_points = points
        if latest_points is None:
            continue
        snapshots.append(
            _point_cloud_snapshot(
                entity_path=points_entity,
                index_name="reference",
                index_value=0,
                world_points=latest_points,
            )
        )
    return snapshots


def _reference_trajectory_entities(recording: rdf.Recording) -> list[str]:
    return sorted(
        column.entity_path
        for column in _component_columns(recording)
        if column.component == "LineStrips3D:strips" and column.entity_path.startswith(_REFERENCE_PREFIX)
    )


def _tracking_positions(recording: rdf.Recording) -> list[tuple[float, float, float]]:
    rows = _rows_for_index(recording, index_name="frame", contents=_TRACKING_CAMERA_ENTITY)
    positions: list[tuple[float, float, float]] = []
    for row in rows:
        translation = _single_vector(row.get(f"{_TRACKING_CAMERA_ENTITY}:Transform3D:translation"))
        frame_value = row.get("frame")
        if translation is None or frame_value is None:
            continue
        positions.append(tuple(float(value) for value in np.asarray(translation, dtype=np.float64)))
    return positions


def _point_cloud_snapshot(
    *,
    entity_path: str,
    index_name: str,
    index_value: int,
    world_points: np.ndarray,
) -> RerunPointCloudSnapshot:
    return RerunPointCloudSnapshot(
        entity_path=entity_path,
        index_name=index_name,
        index_value=index_value,
        point_count=int(len(world_points)),
        bounds_min_xyz=tuple(float(value) for value in world_points.min(axis=0)),
        bounds_max_xyz=tuple(float(value) for value in world_points.max(axis=0)),
    )


def _summary_markdown(summary: RerunValidationSummary) -> str:
    lines = [
        "# Rerun Validation Summary",
        "",
        f"- recording: `{summary.recording_path}`",
        f"- live model points: `{summary.live_model_points.point_count if summary.live_model_points else 0}`",
        f"- keyed point clouds with populated rows: `{len(summary.keyed_point_clouds)}`",
        f"- reconstruction point clouds with populated rows: `{len(summary.reconstruction_point_clouds)}`",
        f"- reference point clouds with populated rows: `{len(summary.reference_point_clouds)}`",
        f"- reference trajectories present: `{len(summary.reference_trajectory_entities)}`",
        f"- keyed camera entities present: `{len(summary.keyed_camera_entities)}`",
        f"- tracking positions: `{len(summary.tracking_positions_xyz)}`",
        "",
        "## Keyed Point Clouds",
    ]
    if not summary.keyed_point_clouds:
        lines.append("- none")
    else:
        for snapshot in summary.keyed_point_clouds[:20]:
            lines.append(
                "- "
                f"`{snapshot.entity_path}` @ {snapshot.index_name}={snapshot.index_value} "
                f"points={snapshot.point_count}"
            )
    lines.extend(["", "## Reference Point Clouds"])
    if not summary.reference_point_clouds:
        lines.append("- none")
    else:
        for snapshot in summary.reference_point_clouds[:20]:
            lines.append(f"- `{snapshot.entity_path}` points={snapshot.point_count}")
    lines.extend(["", "## Reference Trajectories"])
    if not summary.reference_trajectory_entities:
        lines.append("- none")
    else:
        for entity_path in summary.reference_trajectory_entities[:20]:
            lines.append(f"- `{entity_path}`")
    lines.extend(["", "## Reconstruction Point Clouds"])
    if not summary.reconstruction_point_clouds:
        lines.append("- none")
    else:
        for snapshot in summary.reconstruction_point_clouds[:20]:
            lines.append(
                "- "
                f"`{snapshot.entity_path}` @ {snapshot.index_name}={snapshot.index_value} "
                f"points={snapshot.point_count}"
            )
    return "\n".join(lines) + "\n"


def _write_projection_plot(
    *,
    output_path: Path,
    live_world_points: np.ndarray | None,
    keyed_world_points: list[np.ndarray],
    tracking_positions_xyz: np.ndarray,
    axis_x: int,
    axis_y: int,
    x_label: str,
    y_label: str,
    title: str,
    max_render_points: int,
) -> None:
    figure, axis = plt.subplots(figsize=(8, 8), dpi=200)
    axis.set_title(title)
    axis.set_xlabel(x_label)
    axis.set_ylabel(y_label)
    axis.grid(True, alpha=0.25)

    for world_points in keyed_world_points:
        sampled = _sample_points(world_points, max_render_points=max_render_points)
        if len(sampled):
            axis.scatter(sampled[:, axis_x], sampled[:, axis_y], s=0.2, c="#69d2e7", alpha=0.06)

    if live_world_points is not None and len(live_world_points):
        sampled_live = _sample_points(live_world_points, max_render_points=max_render_points)
        axis.scatter(sampled_live[:, axis_x], sampled_live[:, axis_y], s=0.3, c="#f4a261", alpha=0.15)

    if len(tracking_positions_xyz):
        axis.plot(
            tracking_positions_xyz[:, axis_x],
            tracking_positions_xyz[:, axis_y],
            color="#ff4fa3",
            linewidth=1.0,
        )
        axis.scatter(
            tracking_positions_xyz[-1:, axis_x],
            tracking_positions_xyz[-1:, axis_y],
            color="#ff4fa3",
            s=20,
        )

    axis.set_aspect("equal", adjustable="box")
    figure.tight_layout()
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)


def _sample_points(points_xyz: np.ndarray, *, max_render_points: int) -> np.ndarray:
    if len(points_xyz) <= max_render_points:
        return points_xyz
    stride = max(len(points_xyz) // max_render_points, 1)
    return points_xyz[::stride][:max_render_points]


__all__ = [
    "RerunPointCloudSnapshot",
    "RerunValidationArtifacts",
    "RerunValidationSummary",
    "load_recording_summary",
    "main",
    "write_validation_bundle",
]


if __name__ == "__main__":
    raise SystemExit(main())
