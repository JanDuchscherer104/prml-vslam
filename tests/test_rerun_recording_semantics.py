"""Recording-level semantic tests for the repo-owned Rerun integration."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rerun as rr
import rerun.dataframe as rdf

from prml_vslam.interfaces import CameraIntrinsics, FrameTransform
from prml_vslam.methods.contracts import SlamUpdate
from prml_vslam.methods.stage.visualization import (
    DEPTH_REF,
    IMAGE_REF,
    POINTMAP_REF,
    PREVIEW_REF,
    SlamVisualizationAdapter,
)
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageRuntimeUpdate
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.visualization import rerun as rerun_helpers
from prml_vslam.visualization.rerun_policy import RerunLoggingPolicy


@dataclass(frozen=True, slots=True)
class _SyntheticKeyframePayload:
    frame_index: int
    keyframe_index: int
    pose: FrameTransform
    intrinsics: CameraIntrinsics
    rgb: np.ndarray
    depth_m: np.ndarray
    preview_rgb: np.ndarray
    pointmap_xyz_camera: np.ndarray


def _synthetic_keyframe_payloads() -> list[_SyntheticKeyframePayload]:
    return [
        _SyntheticKeyframePayload(
            frame_index=12,
            keyframe_index=3,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=1.0),
            intrinsics=CameraIntrinsics(fx=2.0, fy=2.0, cx=1.0, cy=1.0, width_px=4, height_px=3),
            rgb=np.full((3, 4, 3), 32, dtype=np.uint8),
            depth_m=np.ones((3, 4), dtype=np.float32),
            preview_rgb=np.full((3, 4, 3), 128, dtype=np.uint8),
            pointmap_xyz_camera=np.array([[[0.5, 0.0, 2.0], [0.0, 0.0, 0.0]]], dtype=np.float32),
        ),
        _SyntheticKeyframePayload(
            frame_index=24,
            keyframe_index=4,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=-1.5, ty=1.0, tz=2.5),
            intrinsics=CameraIntrinsics(fx=2.0, fy=2.0, cx=1.0, cy=1.0, width_px=4, height_px=3),
            rgb=np.full((3, 4, 3), 96, dtype=np.uint8),
            depth_m=np.full((3, 4), 1.5, dtype=np.float32),
            preview_rgb=np.full((3, 4, 3), 224, dtype=np.uint8),
            pointmap_xyz_camera=np.array([[[-0.25, 0.1, 1.5], [0.0, 0.0, 0.0]]], dtype=np.float32),
        ),
    ]


def _normalize_entity_path(entity_path: str) -> str:
    return "/" + entity_path.lstrip("/")


def _write_loaded_recording(stream: rr.RecordingStream, *, tmp_path: Path, filename: str) -> rdf.Recording:
    path = tmp_path / filename
    path.write_bytes(stream.memory_recording().drain_as_bytes())
    return rdf.load_recording(path)


def _rows_for_index(recording: rdf.Recording, *, index_name: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    reader = recording.view(index=index_name, contents="/**").select()
    for batch in reader:
        data = batch.to_pydict()
        if not data:
            continue
        row_count = len(next(iter(data.values())))
        for row_index in range(row_count):
            rows.append({column: values[row_index] for column, values in data.items()})
    return rows


def _rows_for_log_tick(recording: rdf.Recording) -> list[dict[str, object]]:
    return _rows_for_index(recording, index_name="log_tick")


def _rows_for_frame(recording: rdf.Recording) -> list[dict[str, object]]:
    return _rows_for_index(recording, index_name="frame")


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
    if array is None:
        return np.empty((0, 3), dtype=np.float64)
    return np.atleast_2d(array)


def _transform_matrix_from_row(row: dict[str, object], *, entity_path: str) -> np.ndarray | None:
    normalized = _normalize_entity_path(entity_path)
    translation = _single_vector(row.get(f"{normalized}:Transform3D:translation"))
    quaternion_xyzw = _single_vector(row.get(f"{normalized}:Transform3D:quaternion"))
    mat3x3 = _single_vector(row.get(f"{normalized}:Transform3D:mat3x3"))
    relation = _single_vector(row.get(f"{normalized}:Transform3D:relation"))

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
    normalized = _normalize_entity_path(entity_path)
    parts = normalized.strip("/").split("/")
    return ["/" + "/".join(parts[:index]) for index in range(1, len(parts) + 1)]


def _row_for_points_entity(
    recording: rdf.Recording, *, index_name: str, index_value: int, points_entity: str
) -> dict[str, object]:
    normalized_points_entity = _normalize_entity_path(points_entity)
    points_column = f"{normalized_points_entity}:Points3D:positions"
    for row in _rows_for_index(recording, index_name=index_name):
        if row.get(index_name) != index_value:
            continue
        if _points_array(row.get(points_column)).size == 0:
            continue
        return row
    raise AssertionError(f"No row found for entity '{points_entity}' on index {index_name}={index_value}.")


def _row_for_points_entity_any_log_tick(recording: rdf.Recording, *, points_entity: str) -> dict[str, object]:
    normalized_points_entity = _normalize_entity_path(points_entity)
    points_column = f"{normalized_points_entity}:Points3D:positions"
    for row in _rows_for_log_tick(recording):
        if _points_array(row.get(points_column)).size > 0:
            return row
    raise AssertionError(f"No row found for entity '{points_entity}' on any log_tick row.")


def _row_for_points_entity_any_frame(recording: rdf.Recording, *, points_entity: str) -> dict[str, object]:
    normalized_points_entity = _normalize_entity_path(points_entity)
    points_column = f"{normalized_points_entity}:Points3D:positions"
    for row in _rows_for_frame(recording):
        if _points_array(row.get(points_column)).size > 0:
            return row
    raise AssertionError(f"No row found for entity '{points_entity}' on any frame row.")


def _world_points_for(recording: rdf.Recording, *, index_name: str, index_value: int, points_entity: str) -> np.ndarray:
    row = _row_for_points_entity(recording, index_name=index_name, index_value=index_value, points_entity=points_entity)
    normalized_points_entity = _normalize_entity_path(points_entity)
    points_xyz = _points_array(row[f"{normalized_points_entity}:Points3D:positions"])
    transform = np.eye(4, dtype=np.float64)
    for ancestor in _ancestor_entity_paths(points_entity):
        branch_transform = (
            _latest_transform_matrix_before_or_at_log_tick(recording, entity_path=ancestor, log_tick=index_value)
            if index_name == "log_tick"
            else _transform_matrix_from_row(row, entity_path=ancestor)
        )
        if branch_transform is not None:
            transform = transform @ branch_transform
    points_h = np.concatenate([points_xyz, np.ones((len(points_xyz), 1), dtype=np.float64)], axis=1)
    world_points_h = points_h @ transform.T
    return world_points_h[:, :3]


def _latest_transform_matrix_before_or_at_log_tick(
    recording: rdf.Recording,
    *,
    entity_path: str,
    log_tick: int,
) -> np.ndarray | None:
    latest_transform: np.ndarray | None = None
    for row in _rows_for_log_tick(recording):
        if row.get("log_tick") is None or row["log_tick"] > log_tick:
            continue
        branch_transform = _transform_matrix_from_row(row, entity_path=entity_path)
        if branch_transform is not None:
            latest_transform = branch_transform
    return latest_transform


def _component_columns(recording: rdf.Recording):
    return list(recording.schema().component_columns())


def _build_repo_owned_recording(*, tmp_path: Path, payloads: Sequence[_SyntheticKeyframePayload]) -> rdf.Recording:
    stream = rerun_helpers.create_recording_stream(app_id="prml-vslam-test", recording_id="repo-semantics")
    policy = RerunLoggingPolicy(
        log_pinhole=rerun_helpers.log_pinhole,
        log_pointcloud=rerun_helpers.log_pointcloud,
        log_pointcloud_ply=rerun_helpers.log_pointcloud_ply,
        log_mesh_ply=rerun_helpers.log_mesh_ply,
        log_line_strip3d=rerun_helpers.log_line_strip3d,
        log_clear=rerun_helpers.log_clear,
        log_depth_image=rerun_helpers.log_depth_image,
        log_ground_plane_patch=rerun_helpers.log_ground_plane_patch,
        log_rgb_image=rerun_helpers.log_rgb_image,
        log_transform=rerun_helpers.log_transform,
    )
    adapter = SlamVisualizationAdapter()
    for payload in payloads:
        policy.observe_update(
            stream,
            StageRuntimeUpdate(
                stage_key=StageKey.SLAM,
                timestamp_ns=payload.frame_index,
                visualizations=adapter.build_items(
                    SlamUpdate(
                        seq=payload.frame_index,
                        timestamp_ns=payload.frame_index,
                        source_seq=payload.frame_index,
                        source_timestamp_ns=payload.frame_index,
                        pose=payload.pose,
                    ),
                    {},
                ),
            ),
            payloads={},
        )
        refs = {
            PREVIEW_REF: TransientPayloadRef(
                handle_id="preview",
                payload_kind="image",
                shape=payload.preview_rgb.shape,
                dtype=str(payload.preview_rgb.dtype),
            ),
            IMAGE_REF: TransientPayloadRef(
                handle_id="rgb",
                payload_kind="image",
                shape=payload.rgb.shape,
                dtype=str(payload.rgb.dtype),
            ),
            DEPTH_REF: TransientPayloadRef(
                handle_id="depth",
                payload_kind="depth",
                shape=payload.depth_m.shape,
                dtype=str(payload.depth_m.dtype),
            ),
            POINTMAP_REF: TransientPayloadRef(
                handle_id="pointmap",
                payload_kind="point_cloud",
                shape=payload.pointmap_xyz_camera.shape,
                dtype=str(payload.pointmap_xyz_camera.dtype),
            ),
        }
        policy.observe_update(
            stream,
            StageRuntimeUpdate(
                stage_key=StageKey.SLAM,
                timestamp_ns=payload.frame_index,
                visualizations=adapter.build_items(
                    SlamUpdate(
                        seq=payload.frame_index,
                        timestamp_ns=payload.frame_index,
                        source_seq=payload.frame_index,
                        source_timestamp_ns=payload.frame_index,
                        is_keyframe=True,
                        keyframe_index=payload.keyframe_index,
                        pose=payload.pose,
                        camera_intrinsics=payload.intrinsics,
                    ),
                    refs,
                ),
            ),
            payloads={
                "preview": payload.preview_rgb,
                "rgb": payload.rgb,
                "depth": payload.depth_m,
                "pointmap": payload.pointmap_xyz_camera,
            },
        )
    return _write_loaded_recording(stream, tmp_path=tmp_path, filename="repo_owned.rrd")


def _build_vista_style_reference_recording(
    *, tmp_path: Path, payloads: Sequence[_SyntheticKeyframePayload]
) -> rdf.Recording:
    stream = rr.RecordingStream(application_id="vista-style-ref", recording_id="vista-style-ref")
    rerun_helpers.log_root_world_transform(stream)
    for payload in payloads:
        pose_matrix = payload.pose.as_matrix()
        translation = pose_matrix[:3, 3]
        rotation = pose_matrix[:3, :3]
        valid_points_xyz_camera = payload.pointmap_xyz_camera.reshape(-1, 3)
        valid_points_xyz_camera = valid_points_xyz_camera[
            np.isfinite(valid_points_xyz_camera[:, 2]) & (valid_points_xyz_camera[:, 2] > 0.0)
        ]

        stream.set_time("frame", sequence=payload.frame_index)
        stream.log(
            f"world/est/ref_frame_{payload.frame_index:06d}",
            rr.Transform3D(
                translation=translation,
                mat3x3=rotation,
            ),
        )
        stream.log(
            f"world/est/ref_frame_{payload.frame_index:06d}/points",
            rr.Points3D(valid_points_xyz_camera),
        )

        stream.log(
            f"world/est/ref_keyframe_{payload.keyframe_index:06d}",
            rr.Transform3D(
                translation=translation,
                mat3x3=rotation,
            ),
        )
        stream.log(
            f"world/est/ref_keyframe_{payload.keyframe_index:06d}/points",
            rr.Points3D(valid_points_xyz_camera),
        )

    return _write_loaded_recording(stream, tmp_path=tmp_path, filename="vista_style_ref.rrd")


def test_repo_owned_recording_matches_vista_style_world_point_placement_across_keyframes(tmp_path: Path) -> None:
    payloads = _synthetic_keyframe_payloads()
    repo_recording = _build_repo_owned_recording(tmp_path=tmp_path, payloads=payloads)
    vista_recording = _build_vista_style_reference_recording(tmp_path=tmp_path, payloads=payloads)

    previous_world_point: np.ndarray | None = None
    for payload in payloads:
        repo_live_world_points = _world_points_for(
            repo_recording,
            index_name="frame",
            index_value=payload.frame_index,
            points_entity="world/live/model/points",
        )
        repo_keyframe_row = _row_for_points_entity_any_frame(
            repo_recording,
            points_entity=f"world/keyframes/points/{payload.keyframe_index:06d}/points",
        )
        repo_keyframe_world_points = _world_points_for(
            repo_recording,
            index_name="frame",
            index_value=repo_keyframe_row["frame"],
            points_entity=f"world/keyframes/points/{payload.keyframe_index:06d}/points",
        )
        vista_frame_world_points = _world_points_for(
            vista_recording,
            index_name="frame",
            index_value=payload.frame_index,
            points_entity=f"world/est/ref_frame_{payload.frame_index:06d}/points",
        )
        vista_keyframe_row = _row_for_points_entity_any_frame(
            vista_recording,
            points_entity=f"world/est/ref_keyframe_{payload.keyframe_index:06d}/points",
        )
        vista_keyframe_world_points = _world_points_for(
            vista_recording,
            index_name="frame",
            index_value=vista_keyframe_row["frame"],
            points_entity=f"world/est/ref_keyframe_{payload.keyframe_index:06d}/points",
        )

        np.testing.assert_allclose(repo_live_world_points, vista_frame_world_points)
        np.testing.assert_allclose(repo_keyframe_world_points, vista_keyframe_world_points)
        if previous_world_point is not None:
            assert not np.allclose(repo_keyframe_world_points[0], previous_world_point)
        previous_world_point = repo_keyframe_world_points[0]


def test_repo_owned_recording_declares_neutral_root_world_with_rdf_view_coordinates(tmp_path: Path) -> None:
    recording = _build_repo_owned_recording(tmp_path=tmp_path, payloads=_synthetic_keyframe_payloads())

    world_columns = [column for column in _component_columns(recording) if column.entity_path == "/world"]
    assert any(column.component == "Transform3D:translation" and column.is_static for column in world_columns)
    assert any(column.component == "Transform3D:axis_length" and column.is_static for column in world_columns)
    assert any(
        "ViewCoordinates" in column.component or "ViewCoordinates" in column.archetype for column in world_columns
    )
    first_frame_row = _rows_for_frame(recording)[0]
    root_axis_length = float(np.asarray(first_frame_row["/world:Transform3D:axis_length"]).reshape(-1)[0])
    assert root_axis_length > 0.0


def test_repo_owned_recording_points_always_have_matching_parent_transform(tmp_path: Path) -> None:
    payloads = _synthetic_keyframe_payloads()
    recording = _build_repo_owned_recording(tmp_path=tmp_path, payloads=payloads)

    for payload in payloads:
        live_row = _row_for_points_entity(
            recording,
            index_name="frame",
            index_value=payload.frame_index,
            points_entity="world/live/model/points",
        )
        keyframe_row = _row_for_points_entity_any_frame(
            recording,
            points_entity=f"world/keyframes/points/{payload.keyframe_index:06d}/points",
        )

        assert _transform_matrix_from_row(live_row, entity_path="world/live/model") is not None
        assert (
            _transform_matrix_from_row(keyframe_row, entity_path=f"world/keyframes/points/{payload.keyframe_index:06d}")
            is not None
        )


def test_repo_owned_recording_keeps_transform_and_points_on_the_same_index(tmp_path: Path) -> None:
    payloads = _synthetic_keyframe_payloads()
    recording = _build_repo_owned_recording(tmp_path=tmp_path, payloads=payloads)

    for payload in payloads:
        live_row = _row_for_points_entity(
            recording,
            index_name="frame",
            index_value=payload.frame_index,
            points_entity="world/live/model/points",
        )
        keyframe_row = _row_for_points_entity_any_frame(
            recording,
            points_entity=f"world/keyframes/points/{payload.keyframe_index:06d}/points",
        )

        assert live_row["frame"] == payload.frame_index
        assert "/world/live/model:Transform3D:translation" in live_row
        assert "/world/live/model/points:Points3D:positions" in live_row
        assert keyframe_row["frame"] == payload.frame_index
        assert f"/world/keyframes/points/{payload.keyframe_index:06d}/points:Points3D:positions" in keyframe_row
        assert (
            _transform_matrix_from_row(keyframe_row, entity_path=f"world/keyframes/points/{payload.keyframe_index:06d}")
            is not None
        )


def test_repo_owned_recording_keeps_keyed_history_while_reusing_live_model_points_entity(tmp_path: Path) -> None:
    payloads = _synthetic_keyframe_payloads()
    recording = _build_repo_owned_recording(tmp_path=tmp_path, payloads=payloads)

    live_rows = [
        row
        for row in _rows_for_index(recording, index_name="frame")
        if "/world/live/model/points:Points3D:positions" in row
        and _points_array(row["/world/live/model/points:Points3D:positions"]).size > 0
    ]

    assert [row["frame"] for row in live_rows] == [payload.frame_index for payload in payloads]
    for payload in payloads:
        keyframe_row = _row_for_points_entity_any_frame(
            recording,
            points_entity=f"world/keyframes/points/{payload.keyframe_index:06d}/points",
        )
        assert keyframe_row["frame"] == payload.frame_index


def test_repo_owned_recording_separates_keyframe_camera_and_point_subtrees(tmp_path: Path) -> None:
    payloads = _synthetic_keyframe_payloads()
    recording = _build_repo_owned_recording(tmp_path=tmp_path, payloads=payloads)

    columns = _component_columns(recording)
    assert any(column.entity_path == "/world/keyframes/cameras/000003" for column in columns)
    assert any(column.entity_path == "/world/keyframes/points/000003" for column in columns)
