"""Tests for repo-owned visualization helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import open3d as o3d
import pytest
from pydantic import ValidationError

# Import pipeline first to keep visualization and curated pipeline exports initialized
# in the same order used by the app.
import prml_vslam.pipeline  # noqa: F401
from prml_vslam.eval.contracts import TrajectoryAlignmentArtifact
from prml_vslam.interfaces import FrameTransform
from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.methods.stage.visualization import COLORS_REF, POINTMAP_REF, ROLE_MODEL_POINTMAP
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageRuntimeUpdate, VisualizationIntent, VisualizationItem
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.reconstruction.stage.visualization import (
    MESH_ARTIFACT,
    POINT_CLOUD_ARTIFACT,
    ROLE_RECONSTRUCTION_MESH,
    ROLE_RECONSTRUCTION_POINT_CLOUD,
)
from prml_vslam.sources.stage.visualization import (
    METADATA_ARTIFACT as SOURCE_METADATA_ARTIFACT,
)
from prml_vslam.sources.stage.visualization import (
    POINT_CLOUD_ARTIFACT as SOURCE_POINT_CLOUD_ARTIFACT,
)
from prml_vslam.sources.stage.visualization import (
    ROLE_SOURCE_REFERENCE_POINT_CLOUD,
    ROLE_SOURCE_REFERENCE_TRAJECTORY,
    TRAJECTORY_ARTIFACT,
)
from prml_vslam.utils.geometry import write_tum_trajectory
from prml_vslam.visualization import rerun as rerun_helpers
from prml_vslam.visualization.artifacts import (
    ROLE_SLAM_ICP_ALIGNED_POINT_CLOUD,
    ROLE_SLAM_SIM3_ALIGNED_POINT_CLOUD,
    ROLE_SLAM_SIM3_ALIGNED_TRAJECTORY,
    artifact_visualizations,
)
from prml_vslam.visualization.contracts import VisualizationConfig
from prml_vslam.visualization.rerun_policy import RerunLoggingPolicy
from prml_vslam.visualization.rerun_sink import ExportRerunEventSink, LiveRerunEventSink


def test_visualization_config_serializes_optional_viewer_blueprint_path() -> None:
    config = VisualizationConfig(
        connect_live_viewer=True,
        viewer_blueprint_path=Path(".configs/visualization/vista_blueprint.rbl"),
        point_cloud_decimation_keep_ratio=0.25,
        reference_point_cloud_decimation_keep_ratio=0.75,
        mesh_decimation_keep_ratio=0.5,
        decimation_random_seed=99,
    )

    rendered = config.to_toml()
    reloaded = VisualizationConfig.from_toml(rendered)

    assert 'viewer_blueprint_path = ".configs/visualization/vista_blueprint.rbl"' in rendered
    assert "point_cloud_decimation_keep_ratio = 0.25" in rendered
    assert "reference_point_cloud_decimation_keep_ratio = 0.75" in rendered
    assert "mesh_decimation_keep_ratio = 0.5" in rendered
    assert "decimation_random_seed = 99" in rendered
    assert reloaded.viewer_blueprint_path == Path(".configs/visualization/vista_blueprint.rbl")
    assert reloaded.log_source_rgb is False
    assert reloaded.log_diagnostic_preview is False
    assert reloaded.log_camera_image_rgb is True
    assert reloaded.trajectory_pose_axis_length == 0.0
    assert reloaded.point_cloud_decimation_keep_ratio == 0.25
    assert reloaded.reference_point_cloud_decimation_keep_ratio == 0.75
    assert reloaded.mesh_decimation_keep_ratio == 0.5
    assert reloaded.decimation_random_seed == 99


def test_visualization_config_rejects_invalid_decimation_values() -> None:
    with pytest.raises(ValidationError):
        VisualizationConfig(point_cloud_decimation_keep_ratio=0.0)
    with pytest.raises(ValidationError):
        VisualizationConfig(reference_point_cloud_decimation_keep_ratio=0.0)
    with pytest.raises(ValidationError):
        VisualizationConfig(mesh_decimation_keep_ratio=1.1)
    with pytest.raises(ValidationError):
        VisualizationConfig(decimation_random_seed=-1)
    with pytest.raises(ValidationError):
        VisualizationConfig(view_coordinates="RUB")


def test_attach_recording_sinks_configures_grpc_and_file_together(
    tmp_path: Path,
    monkeypatch,
) -> None:
    configured_sinks: tuple[object, ...] = ()

    class FakeGrpcSink:
        def __init__(self, url: str) -> None:
            self.url = url

    class FakeFileSink:
        def __init__(self, path: str) -> None:
            self.path = path

    class FakeRecordingStream:
        def set_sinks(self, *sinks: object) -> None:
            nonlocal configured_sinks
            configured_sinks = sinks

    monkeypatch.setattr(rerun_helpers, "rr", SimpleNamespace(GrpcSink=FakeGrpcSink, FileSink=FakeFileSink))

    rerun_helpers.attach_recording_sinks(
        FakeRecordingStream(),
        grpc_url="rerun+http://127.0.0.1:9876/proxy",
        target_path=tmp_path / "viewer_recording.rrd",
    )

    assert len(configured_sinks) == 2
    assert isinstance(configured_sinks[0], FakeGrpcSink)
    assert configured_sinks[0].url == "rerun+http://127.0.0.1:9876/proxy"
    assert isinstance(configured_sinks[1], FakeFileSink)
    assert configured_sinks[1].path == str(tmp_path / "viewer_recording.rrd")


def test_attach_recording_sinks_replaces_stale_rrd_file(tmp_path: Path, monkeypatch) -> None:
    stale_path = tmp_path / "viewer_recording.rrd"
    stale_path.write_bytes(b"stale")

    class FakeFileSink:
        def __init__(self, path: str) -> None:
            self.path = path

    class FakeRecordingStream:
        def set_sinks(self, *sinks: object) -> None:
            del sinks

    monkeypatch.setattr(rerun_helpers, "rr", SimpleNamespace(FileSink=FakeFileSink))

    rerun_helpers.attach_recording_sinks(FakeRecordingStream(), target_path=stale_path)

    assert not stale_path.exists()


def test_create_recording_stream_uses_keyed_history_default_blueprint(monkeypatch) -> None:
    sent_blueprints: list[object] = []
    logged_entities: list[tuple[str, object, bool]] = []

    class FakeRecordingStream:
        def __init__(self, *, application_id: str, recording_id: str | None) -> None:
            self.application_id = application_id
            self.recording_id = recording_id

        def send_blueprint(self, blueprint: object) -> None:
            sent_blueprints.append(blueprint)

        def log(self, entity_path: str, payload: object, *extra: object, static: bool = False) -> None:
            del extra
            logged_entities.append((entity_path, payload, static))

    class FakeSpatial3DView:
        def __init__(self, *, origin: str, contents=None, name: str) -> None:
            self.origin = origin
            self.contents = contents
            self.name = name

    class FakeSpatial2DView:
        def __init__(self, *, origin: str, contents=None, name: str) -> None:
            self.origin = origin
            self.contents = contents
            self.name = name

    class FakeHorizontal:
        def __init__(self, *views: object) -> None:
            self.views = views

    class FakeTabs:
        def __init__(self, *views: object, name: str | None = None) -> None:
            self.views = views
            self.name = name

    class FakeBlueprint:
        def __init__(self, layout: object) -> None:
            self.layout = layout

    class FakeTransform3D:
        def __init__(self, *, axis_length: float) -> None:
            self.identity = True
            self.axis_length = axis_length

    class FakeViewCoordinates:
        RDF = "rdf"
        RFU = "rfu"

    monkeypatch.setattr(
        rerun_helpers,
        "rr",
        SimpleNamespace(
            RecordingStream=FakeRecordingStream,
            Transform3D=FakeTransform3D,
            ViewCoordinates=FakeViewCoordinates,
        ),
    )
    monkeypatch.setattr(
        rerun_helpers,
        "rrb",
        SimpleNamespace(
            Blueprint=FakeBlueprint,
            Horizontal=FakeHorizontal,
            Spatial3DView=FakeSpatial3DView,
            Spatial2DView=FakeSpatial2DView,
            Tabs=FakeTabs,
        ),
    )

    stream = rerun_helpers.create_recording_stream(app_id="prml-vslam", recording_id="demo")

    assert isinstance(stream, FakeRecordingStream)
    assert len(sent_blueprints) == 1
    layout = sent_blueprints[0].layout
    assert layout.views[0].origin == "world"
    assert layout.views[0].contents == list(rerun_helpers.DEFAULT_3D_SCENE_CONTENTS)
    assert "+ world/reference/trajectory/**" in layout.views[0].contents
    assert "+ world/reference/points/*/aligned/**" in layout.views[0].contents
    assert "+ world/aligned/**" in layout.views[0].contents
    assert "+ world/overlays/**" not in layout.views[0].contents
    assert "+ world/slam" in layout.views[0].contents
    assert "+ world/slam/**" not in layout.views[0].contents
    assert "+ world/slam/point_cloud/raw" in layout.views[0].contents
    assert "+ world/slam/keyframes/points/**" in layout.views[0].contents
    assert "- world/slam/live/model/points/**" in layout.views[0].contents
    assert "+ world/live/source/camera" in layout.views[0].contents
    assert layout.views[1].name == "2D Views"
    assert [view.origin for view in layout.views[1].views] == [
        rerun_helpers.MODEL_RGB_2D_ENTITY_PATH,
        "world/slam/live/model/camera/image",
    ]
    assert len(logged_entities) == 3
    entity_path, payload, static = logged_entities[0]
    assert entity_path == rerun_helpers.ROOT_WORLD_ENTITY_PATH
    assert isinstance(payload, FakeTransform3D)
    assert payload.axis_length == rerun_helpers.ROOT_WORLD_AXIS_LENGTH
    assert static is True
    entity_path, payload, static = logged_entities[1]
    assert entity_path == rerun_helpers.ROOT_WORLD_ENTITY_PATH
    assert payload == FakeViewCoordinates.RDF
    assert static is True
    entity_path, payload, static = logged_entities[2]
    assert entity_path == rerun_helpers.SLAM_WORLD_ENTITY_PATH
    assert isinstance(payload, FakeTransform3D)
    assert payload.axis_length == rerun_helpers.SLAM_WORLD_AXIS_LENGTH
    assert static is True


def test_log_transform_uses_parent_from_child_relation(monkeypatch) -> None:
    logged: list[object] = []

    class FakeQuaternion:
        def __init__(self, *, xyzw: list[float]) -> None:
            self.xyzw = xyzw

    class FakeTransform3D:
        def __init__(self, *, translation, quaternion, relation, axis_length) -> None:
            self.translation = translation
            self.quaternion = quaternion
            self.relation = relation
            self.axis_length = axis_length

    class FakeTransformRelation:
        ParentFromChild = "parent-from-child"

    class FakeRecordingStream:
        def log(self, entity_path: str, payload: object, *, static: bool = False) -> None:
            del static
            logged.append((entity_path, payload))

    monkeypatch.setattr(
        rerun_helpers,
        "rr",
        SimpleNamespace(
            Quaternion=FakeQuaternion,
            Transform3D=FakeTransform3D,
            TransformRelation=FakeTransformRelation,
        ),
    )

    transform = FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0)
    rerun_helpers.log_transform(FakeRecordingStream(), entity_path="world/live/camera", transform=transform)

    assert len(logged) == 1
    entity_path, payload = logged[0]
    assert entity_path == "world/live/camera"
    assert payload.relation == FakeTransformRelation.ParentFromChild
    world_point = transform.as_matrix() @ np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float64)
    assert np.allclose(world_point[:3], np.array([1.0, 2.0, 4.0], dtype=np.float64))


def test_log_transform_axes_rejects_ambiguous_rotation(monkeypatch) -> None:
    monkeypatch.setattr(
        rerun_helpers,
        "rr",
        SimpleNamespace(Quaternion=lambda *, xyzw: xyzw, Transform3D=lambda **kwargs: kwargs),
    )

    with pytest.raises(ValueError, match="either quaternion_xyzw or rotation_matrix"):
        rerun_helpers.log_transform_axes(
            object(),
            entity_path="world/pose",
            quaternion_xyzw=[0.0, 0.0, 0.0, 1.0],
            rotation_matrix=np.eye(3),
        )


def test_log_line_strip3d_logs_one_strip(monkeypatch) -> None:
    logged: list[tuple[str, object]] = []

    class FakeLineStrips3D:
        def __init__(self, strips, radii, colors=None) -> None:
            self.strips = strips
            self.radii = radii
            self.colors = colors

    class FakeRecordingStream:
        def log(self, entity_path: str, payload: object, *, static: bool = False) -> None:
            del static
            logged.append((entity_path, payload))

    monkeypatch.setattr(rerun_helpers, "rr", SimpleNamespace(LineStrips3D=FakeLineStrips3D))

    rerun_helpers.log_line_strip3d(
        FakeRecordingStream(),
        entity_path="world/slam/trajectory/raw",
        positions_xyz=np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]], dtype=np.float32),
    )

    assert len(logged) == 1
    entity_path, payload = logged[0]
    assert entity_path == "world/slam/trajectory/raw"
    assert len(payload.strips) == 1
    assert np.array_equal(payload.strips[0], np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]], dtype=np.float32))


def test_log_pointcloud_decimation_is_deterministic_and_keeps_color_alignment(monkeypatch) -> None:
    logged: list[tuple[np.ndarray, np.ndarray | None]] = []

    class FakePoints3D:
        def __init__(self, *, positions, colors, radii) -> None:
            del radii
            self.positions = np.asarray(positions)
            self.colors = None if colors is None else np.asarray(colors)

    class FakeRecordingStream:
        def log(self, entity_path: str, payload: object) -> None:
            del entity_path
            logged.append((payload.positions, payload.colors))

    monkeypatch.setattr(rerun_helpers, "rr", SimpleNamespace(Points3D=FakePoints3D))

    points_xyz = np.array(
        [
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [2.0, 0.0, 1.0],
            [3.0, 0.0, 1.0],
            [4.0, 0.0, 1.0],
            [5.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )
    colors = np.array([[index, index + 10, index + 20] for index in range(len(points_xyz))], dtype=np.uint8)

    for _ in range(2):
        rerun_helpers.log_pointcloud(
            FakeRecordingStream(),
            entity_path="world/slam/live/model/points",
            pointmap=points_xyz,
            colors=colors,
            decimation_keep_ratio=0.5,
            decimation_seed=1234,
        )

    first_positions, first_colors = logged[0]
    second_positions, second_colors = logged[1]
    assert first_positions.shape == (3, 3)
    assert np.array_equal(first_positions, second_positions)
    assert np.array_equal(first_colors, second_colors)
    for position, color in zip(first_positions, first_colors, strict=True):
        source_index = int(position[0])
        assert np.array_equal(color, colors[source_index])


def test_log_pointcloud_decimation_ratio_one_keeps_valid_rows_in_order(monkeypatch) -> None:
    logged: list[np.ndarray] = []

    class FakePoints3D:
        def __init__(self, *, positions, colors, radii) -> None:
            del colors, radii
            self.positions = np.asarray(positions)

    class FakeRecordingStream:
        def log(self, entity_path: str, payload: object) -> None:
            del entity_path
            logged.append(payload.positions)

    monkeypatch.setattr(rerun_helpers, "rr", SimpleNamespace(Points3D=FakePoints3D))

    rerun_helpers.log_pointcloud(
        FakeRecordingStream(),
        entity_path="world/slam/live/model/points",
        pointmap=np.array(
            [
                [0.0, 0.0, 1.0],
                [9.0, 9.0, -1.0],
                [1.0, 0.0, 2.0],
                [8.0, 8.0, np.inf],
                [2.0, 0.0, 3.0],
            ],
            dtype=np.float32,
        ),
        decimation_keep_ratio=1.0,
    )

    assert np.array_equal(
        logged[0],
        np.array(
            [
                [0.0, 0.0, 1.0],
                [1.0, 0.0, 2.0],
                [2.0, 0.0, 3.0],
            ],
            dtype=np.float32,
        ),
    )


def test_rerun_policy_logs_trajectory_artifact_as_line_and_pose_transforms(
    tmp_path: Path,
    monkeypatch,
) -> None:
    trajectory_path = write_tum_trajectory(
        tmp_path / "trajectory.tum",
        [
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0),
        ],
        [0.0, 1.0],
    )
    line_calls: list[tuple[str, bool]] = []
    pose_calls: list[tuple[str, float | None, bool, FrameTransform]] = []
    monkeypatch.setattr(
        rerun_helpers,
        "log_line_strip3d",
        lambda stream, *, entity_path, positions_xyz, static=False, **kwargs: line_calls.append((entity_path, static)),
    )
    monkeypatch.setattr(
        rerun_helpers,
        "log_transform",
        lambda stream, *, entity_path, transform, axis_length=None, static=False: pose_calls.append(
            (entity_path, axis_length, static, transform)
        ),
    )
    policy = RerunLoggingPolicy(
        trajectory_pose_axis_length=0.25,
    )
    update = StageRuntimeUpdate(
        stage_key=StageKey.SOURCE,
        timestamp_ns=1,
        visualizations=[
            VisualizationItem(
                intent=VisualizationIntent.TRAJECTORY,
                role=ROLE_SOURCE_REFERENCE_TRAJECTORY,
                artifact_refs={
                    TRAJECTORY_ARTIFACT: ArtifactRef(path=trajectory_path, kind="tum", fingerprint="trajectory")
                },
                metadata={
                    "reference_source": "ground_truth",
                    "coordinate_status": "aligned",
                    "target_frame": "advio_gt_world",
                },
            )
        ],
    )

    policy.observe_update(object(), update)

    assert line_calls == [("world/reference/trajectory/ground_truth/aligned", True)]
    assert [call[0] for call in pose_calls] == [
        "world/reference/trajectory/ground_truth/aligned/start",
        "world/reference/trajectory/ground_truth/aligned/poses/000000",
        "world/reference/trajectory/ground_truth/aligned/poses/000001",
    ]
    assert pose_calls[0][1] == rerun_helpers.TRAJECTORY_START_AXIS_LENGTH
    assert pose_calls[0][2] is True
    assert pose_calls[0][3].tx == 0.0
    assert all(axis_length == 0.25 and static is True for _, axis_length, static, _ in pose_calls[1:])
    assert pose_calls[2][3].target_frame == "advio_gt_world"
    assert pose_calls[2][3].tx == 1.0


def test_rerun_policy_logs_aligned_slam_artifacts_under_target_frame_namespace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    trajectory_path = write_tum_trajectory(
        tmp_path / "trajectory_sim3_aligned.tum",
        [
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.0, tz=0.0),
        ],
        [0.0, 1.0],
    )
    sim3_cloud_path = tmp_path / "point_cloud_sim3_aligned.ply"
    icp_cloud_path = tmp_path / "point_cloud_sim3_icp_aligned.ply"
    line_calls: list[str] = []
    pointcloud_ply_calls: list[str] = []
    monkeypatch.setattr(
        rerun_helpers,
        "log_pointcloud_ply",
        lambda stream, *, entity_path, path, **kwargs: pointcloud_ply_calls.append(entity_path),
    )
    monkeypatch.setattr(
        rerun_helpers,
        "log_line_strip3d",
        lambda stream, *, entity_path, positions_xyz, **kwargs: line_calls.append(entity_path),
    )
    monkeypatch.setattr(rerun_helpers, "log_transform", lambda *args, **kwargs: None)
    policy = RerunLoggingPolicy()
    update = StageRuntimeUpdate(
        stage_key=StageKey.TRAJECTORY_ALIGNMENT,
        timestamp_ns=1,
        visualizations=[
            VisualizationItem(
                intent=VisualizationIntent.TRAJECTORY,
                role=ROLE_SLAM_SIM3_ALIGNED_TRAJECTORY,
                artifact_refs={TRAJECTORY_ARTIFACT: ArtifactRef(path=trajectory_path, kind="tum", fingerprint="traj")},
                metadata={"target_frame": "advio_gt_world"},
            ),
            VisualizationItem(
                intent=VisualizationIntent.POINT_CLOUD,
                role=ROLE_SLAM_SIM3_ALIGNED_POINT_CLOUD,
                artifact_refs={POINT_CLOUD_ARTIFACT: ArtifactRef(path=sim3_cloud_path, kind="ply", fingerprint="sim3")},
                metadata={"target_frame": "advio_gt_world"},
            ),
            VisualizationItem(
                intent=VisualizationIntent.POINT_CLOUD,
                role=ROLE_SLAM_ICP_ALIGNED_POINT_CLOUD,
                artifact_refs={POINT_CLOUD_ARTIFACT: ArtifactRef(path=icp_cloud_path, kind="ply", fingerprint="icp")},
                metadata={"target_frame": "advio_gt_world"},
            ),
        ],
    )

    policy.observe_update(object(), update)

    assert line_calls[0] == "world/aligned/advio_gt_world/slam/sim3/trajectory"
    assert pointcloud_ply_calls == [
        "world/aligned/advio_gt_world/slam/sim3/point_cloud",
        "world/aligned/advio_gt_world/slam/icp/point_cloud",
    ]
    assert all("world/overlays" not in entity_path for entity_path in [*line_calls, *pointcloud_ply_calls])


def test_artifact_visualizations_include_sim3_and_icp_cloud_alignment_outputs(tmp_path: Path) -> None:
    cloud_alignment_path = tmp_path / "cloud_alignment.json"
    cloud_alignment_path.write_text('{"target_frame": "advio_gt_world"}', encoding="utf-8")
    sim3_cloud_path = tmp_path / "point_cloud_sim3_aligned.ply"
    icp_cloud_path = tmp_path / "point_cloud_sim3_icp_aligned.ply"

    items = artifact_visualizations(
        {
            "cloud_alignment": ArtifactRef(path=cloud_alignment_path, kind="json", fingerprint="alignment"),
            "sim3_aligned_point_cloud_ply": ArtifactRef(path=sim3_cloud_path, kind="ply", fingerprint="sim3"),
            "icp_aligned_point_cloud_ply": ArtifactRef(path=icp_cloud_path, kind="ply", fingerprint="icp"),
        }
    )

    assert [(item.role, item.space, item.metadata["coordinate_status"]) for item in items] == [
        (ROLE_SLAM_SIM3_ALIGNED_POINT_CLOUD, "advio_gt_world", "sim3_aligned"),
        (ROLE_SLAM_ICP_ALIGNED_POINT_CLOUD, "advio_gt_world", "icp_aligned"),
    ]


def test_rerun_policy_logs_sim3_alignment_marker_without_moving_raw_slam_root(monkeypatch) -> None:
    sim3_calls: list[tuple[str, float, bool]] = []
    monkeypatch.setattr(
        rerun_helpers,
        "log_sim3_transform",
        lambda stream, *, entity_path, scale, static, **kwargs: sim3_calls.append((entity_path, scale, static)),
    )
    policy = RerunLoggingPolicy()
    alignment = TrajectoryAlignmentArtifact(
        source_frame="vista_slam_world",
        target_frame="advio_gt_world",
        scale=1.25,
        rotation=np.eye(3).tolist(),
        translation=[1.0, 2.0, 3.0],
        matched_pairs=12,
        rms_error_m=0.5,
        reference_source="ground_truth",
        sync_max_diff_s=0.01,
    )

    policy.observe_update(
        object(),
        StageRuntimeUpdate(stage_key=StageKey.TRAJECTORY_ALIGNMENT, timestamp_ns=1, semantic_events=[alignment]),
    )

    assert sim3_calls == [("world/aligned/advio_gt_world/slam/sim3/source_to_target", 1.25, True)]
    assert sim3_calls[0][0] != rerun_helpers.SLAM_WORLD_ENTITY_PATH


def test_rerun_policy_skips_trajectory_pose_transforms_when_axis_length_is_zero(
    tmp_path: Path,
    monkeypatch,
) -> None:
    trajectory_path = write_tum_trajectory(
        tmp_path / "trajectory.tum",
        [
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0),
        ],
        [0.0, 1.0],
    )
    line_calls: list[tuple[str, bool]] = []
    pose_calls: list[str] = []
    monkeypatch.setattr(
        rerun_helpers,
        "log_line_strip3d",
        lambda stream, *, entity_path, positions_xyz, static=False, **kwargs: line_calls.append((entity_path, static)),
    )
    monkeypatch.setattr(
        rerun_helpers,
        "log_transform",
        lambda stream, *, entity_path, transform, axis_length=None, static=False: pose_calls.append(entity_path),
    )
    policy = RerunLoggingPolicy()
    update = StageRuntimeUpdate(
        stage_key=StageKey.SOURCE,
        timestamp_ns=1,
        visualizations=[
            VisualizationItem(
                intent=VisualizationIntent.TRAJECTORY,
                role=ROLE_SOURCE_REFERENCE_TRAJECTORY,
                artifact_refs={
                    TRAJECTORY_ARTIFACT: ArtifactRef(path=trajectory_path, kind="tum", fingerprint="trajectory")
                },
                metadata={
                    "reference_source": "ground_truth",
                    "coordinate_status": "aligned",
                    "target_frame": "advio_gt_world",
                },
            )
        ],
    )

    policy.observe_update(object(), update)

    assert line_calls == [("world/reference/trajectory/ground_truth/aligned", True)]
    assert pose_calls == ["world/reference/trajectory/ground_truth/aligned/start"]


def test_rerun_policy_passes_decimation_to_geometry_loggers(tmp_path: Path, monkeypatch) -> None:
    pointcloud_calls: list[tuple[str, float, int]] = []
    pointcloud_ply_calls: list[tuple[str, Path, float, int]] = []
    mesh_ply_calls: list[tuple[str, Path, float]] = []

    def capture_pointcloud(
        stream,
        *,
        entity_path,
        pointmap,
        colors,
        decimation_keep_ratio,
        decimation_seed,
        **kwargs,
    ) -> None:
        del stream, pointmap, colors, kwargs
        pointcloud_calls.append((entity_path, decimation_keep_ratio, decimation_seed))

    def capture_pointcloud_ply(
        stream,
        *,
        entity_path,
        path,
        decimation_keep_ratio,
        decimation_seed,
    ) -> None:
        del stream
        pointcloud_ply_calls.append((entity_path, path, decimation_keep_ratio, decimation_seed))

    def capture_mesh_ply(stream, *, entity_path, path, decimation_keep_ratio) -> None:
        del stream
        mesh_ply_calls.append((entity_path, path, decimation_keep_ratio))

    monkeypatch.setattr(rerun_helpers, "log_pointcloud", capture_pointcloud)
    monkeypatch.setattr(rerun_helpers, "log_pointcloud_ply", capture_pointcloud_ply)
    monkeypatch.setattr(rerun_helpers, "log_mesh_ply", capture_mesh_ply)
    monkeypatch.setattr(rerun_helpers, "log_line_strip3d", lambda *args, **kwargs: None)
    monkeypatch.setattr(rerun_helpers, "log_transform", lambda *args, **kwargs: None)
    policy = RerunLoggingPolicy(
        point_cloud_decimation_keep_ratio=0.25,
        reference_point_cloud_decimation_keep_ratio=1.0,
        mesh_decimation_keep_ratio=0.5,
        decimation_random_seed=123,
    )
    cloud_path = tmp_path / "reference_cloud.ply"
    source_cloud_metadata_path = tmp_path / "reference_cloud.metadata.json"
    source_cloud_metadata_path.write_text('{"point_count": 4, "skipped_out_of_range_payloads": 0}', encoding="utf-8")
    mesh_path = tmp_path / "reference_mesh.ply"
    update = StageRuntimeUpdate(
        stage_key=StageKey.RECONSTRUCTION,
        timestamp_ns=1,
        visualizations=[
            VisualizationItem(
                intent=VisualizationIntent.POINT_CLOUD,
                role=ROLE_MODEL_POINTMAP,
                payload_refs={
                    POINTMAP_REF: TransientPayloadRef(
                        handle_id="pointmap",
                        payload_kind="point_cloud",
                        shape=(4, 3),
                        dtype="float32",
                    ),
                    COLORS_REF: TransientPayloadRef(
                        handle_id="colors",
                        payload_kind="image",
                        shape=(4, 3),
                        dtype="uint8",
                    ),
                },
            ),
            VisualizationItem(
                intent=VisualizationIntent.POINT_CLOUD,
                role=ROLE_RECONSTRUCTION_POINT_CLOUD,
                artifact_refs={POINT_CLOUD_ARTIFACT: ArtifactRef(path=cloud_path, kind="ply", fingerprint="cloud")},
                metadata={"reconstruction_id": "reference"},
            ),
            VisualizationItem(
                intent=VisualizationIntent.MESH,
                role=ROLE_RECONSTRUCTION_MESH,
                artifact_refs={MESH_ARTIFACT: ArtifactRef(path=mesh_path, kind="ply", fingerprint="mesh")},
                metadata={"reconstruction_id": "reference"},
            ),
            VisualizationItem(
                intent=VisualizationIntent.POINT_CLOUD,
                role=ROLE_SOURCE_REFERENCE_POINT_CLOUD,
                artifact_refs={
                    SOURCE_POINT_CLOUD_ARTIFACT: ArtifactRef(path=cloud_path, kind="ply", fingerprint="source-cloud"),
                    SOURCE_METADATA_ARTIFACT: ArtifactRef(
                        path=source_cloud_metadata_path, kind="json", fingerprint="source-cloud-metadata"
                    ),
                },
                metadata={"reference_source": "tango_raw", "coordinate_status": "aligned"},
            ),
        ],
    )

    policy.observe_update(
        object(),
        update,
        payloads={
            "pointmap": np.ones((4, 3), dtype=np.float32),
            "colors": np.zeros((4, 3), dtype=np.uint8),
        },
    )

    assert pointcloud_calls == [("world/slam/live/model/points", 0.25, pointcloud_calls[0][2])]
    assert isinstance(pointcloud_calls[0][2], int)
    assert pointcloud_ply_calls == [
        ("world/reconstruction/reference/point_cloud", cloud_path, 0.25, pointcloud_ply_calls[0][3]),
        (
            "world/reference/points/tango_raw/aligned/points_4_skipped_0/point_cloud",
            cloud_path,
            1.0,
            pointcloud_ply_calls[1][3],
        ),
    ]
    assert isinstance(pointcloud_ply_calls[0][3], int)
    assert isinstance(pointcloud_ply_calls[1][3], int)
    assert mesh_ply_calls == [("world/reconstruction/reference/mesh", mesh_path, 0.5)]


def test_rerun_event_sink_builds_live_and_export_policies_with_decimation(tmp_path: Path) -> None:
    export_sink = ExportRerunEventSink(
        target_path=tmp_path / "viewer.rrd",
        point_cloud_decimation_keep_ratio=0.2,
        reference_point_cloud_decimation_keep_ratio=0.9,
        mesh_decimation_keep_ratio=0.4,
        decimation_random_seed=77,
    )
    live_sink = LiveRerunEventSink(
        grpc_url="rerun+http://127.0.0.1:9876/proxy",
        point_cloud_decimation_keep_ratio=0.2,
        reference_point_cloud_decimation_keep_ratio=0.9,
        mesh_decimation_keep_ratio=0.4,
        decimation_random_seed=77,
    )

    for sink in (live_sink, export_sink):
        assert sink._policy.point_cloud_decimation_keep_ratio == 0.2
        assert sink._policy.reference_point_cloud_decimation_keep_ratio == 0.9
        assert sink._policy.mesh_decimation_keep_ratio == 0.4
        assert sink._policy.decimation_random_seed == 77


def test_log_mesh3d_logs_one_mesh(monkeypatch) -> None:
    logged: list[tuple[str, object]] = []

    class FakeMesh3D:
        def __init__(self, *, vertex_positions, triangle_indices, vertex_colors) -> None:
            self.vertex_positions = vertex_positions
            self.triangle_indices = triangle_indices
            self.vertex_colors = vertex_colors

    class FakeRecordingStream:
        def log(self, entity_path: str, payload: object, *, static: bool = False) -> None:
            del static
            logged.append((entity_path, payload))

    monkeypatch.setattr(rerun_helpers, "rr", SimpleNamespace(Mesh3D=FakeMesh3D))

    rerun_helpers.log_mesh3d(
        FakeRecordingStream(),
        entity_path="world/alignment/ground_plane/fill",
        vertex_positions_xyz=np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 0.0, 1.0], [0.0, 0.0, 1.0]],
            dtype=np.float32,
        ),
        triangle_indices=np.array([[0, 1, 2], [0, 2, 3]], dtype=np.uint32),
    )

    assert len(logged) == 1
    entity_path, payload = logged[0]
    assert entity_path == "world/alignment/ground_plane/fill"
    assert payload.vertex_positions.shape == (4, 3)
    assert payload.triangle_indices.shape == (2, 3)


def test_log_mesh_ply_simplifies_with_open3d_backend(tmp_path: Path, monkeypatch) -> None:
    logged: list[tuple[str, object, bool]] = []

    class FakeMesh3D:
        def __init__(self, *, vertex_positions, triangle_indices, vertex_colors) -> None:
            self.vertex_positions = np.asarray(vertex_positions)
            self.triangle_indices = np.asarray(triangle_indices)
            self.vertex_colors = vertex_colors

    class FakeRecordingStream:
        def log(self, entity_path: str, payload: object, *, static: bool = False) -> None:
            logged.append((entity_path, payload, static))

    monkeypatch.setattr(rerun_helpers, "rr", SimpleNamespace(Mesh3D=FakeMesh3D))
    mesh = o3d.geometry.TriangleMesh.create_sphere(resolution=8)
    mesh_path = tmp_path / "mesh.ply"
    assert o3d.io.write_triangle_mesh(str(mesh_path), mesh, write_ascii=True)
    original_triangle_count = len(mesh.triangles)

    rerun_helpers.log_mesh_ply(
        FakeRecordingStream(),
        entity_path="world/reconstruction/reference/mesh",
        path=mesh_path,
        decimation_keep_ratio=0.25,
    )

    assert len(logged) == 1
    entity_path, payload, static = logged[0]
    assert entity_path == "world/reconstruction/reference/mesh"
    assert static is True
    assert payload.vertex_positions.ndim == 2
    assert payload.vertex_positions.shape[1] == 3
    assert payload.triangle_indices.ndim == 2
    assert payload.triangle_indices.shape[1] == 3
    assert 0 < len(payload.triangle_indices) < original_triangle_count
    assert int(np.max(payload.triangle_indices)) < len(payload.vertex_positions)


def test_log_ground_plane_patch_logs_fill_and_outline(monkeypatch) -> None:
    logged: list[tuple[str, object]] = []

    class FakeMesh3D:
        def __init__(self, *, vertex_positions, triangle_indices, vertex_colors) -> None:
            self.vertex_positions = vertex_positions
            self.triangle_indices = triangle_indices
            self.vertex_colors = vertex_colors

    class FakeLineStrips3D:
        def __init__(self, strips, *, radii, colors) -> None:
            self.strips = strips
            self.radii = radii
            self.colors = colors

    class FakeRecordingStream:
        def log(self, entity_path: str, payload: object, *, static: bool = False) -> None:
            del static
            logged.append((entity_path, payload))

    class FakeArrows3D:
        def __init__(self, *, origins, vectors, colors, radii) -> None:
            self.origins = origins
            self.vectors = vectors
            self.colors = colors
            self.radii = radii

    monkeypatch.setattr(
        rerun_helpers,
        "rr",
        SimpleNamespace(
            Mesh3D=FakeMesh3D,
            LineStrips3D=FakeLineStrips3D,
            Arrows3D=FakeArrows3D,
        ),
    )

    rerun_helpers.log_ground_plane_patch(
        FakeRecordingStream(),
        metadata=SimpleNamespace(
            visualization=SimpleNamespace(
                corners_xyz_world=[
                    (0.0, 0.0, 0.0),
                    (0.0, 0.0, 1.0),
                    (1.0, 0.0, 1.0),
                    (1.0, 0.0, 0.0),
                ]
            ),
            ground_plane_world=SimpleNamespace(normal_xyz_world=(0.0, 1.0, 0.0)),
        ),
    )

    assert [entity for entity, _ in logged] == [
        "world/slam/alignment/ground_plane/fill",
        "world/slam/alignment/ground_plane/outline",
        "world/slam/alignment/ground_plane/normal",
    ]


def test_log_clear_logs_recursive_clear(monkeypatch) -> None:
    logged: list[tuple[str, object]] = []

    class FakeClear:
        def __init__(self, *, recursive: bool) -> None:
            self.recursive = recursive

    class FakeRecordingStream:
        def log(self, entity_path: str, payload: object) -> None:
            logged.append((entity_path, payload))

    monkeypatch.setattr(rerun_helpers, "rr", SimpleNamespace(Clear=FakeClear))

    rerun_helpers.log_clear(
        FakeRecordingStream(),
        entity_path="world/keyframes/cameras/000001",
        recursive=True,
    )

    assert len(logged) == 1
    entity_path, payload = logged[0]
    assert entity_path == "world/keyframes/cameras/000001"
    assert payload.recursive is True
