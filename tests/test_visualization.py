"""Tests for repo-owned visualization helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

# Import pipeline first to keep visualization and curated pipeline exports initialized
# in the same order used by the app.
import prml_vslam.pipeline  # noqa: F401
from prml_vslam.interfaces import FrameTransform
from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageRuntimeUpdate, VisualizationIntent, VisualizationItem
from prml_vslam.sources.stage.visualization import ROLE_SOURCE_REFERENCE_TRAJECTORY, TRAJECTORY_ARTIFACT
from prml_vslam.utils.geometry import write_tum_trajectory
from prml_vslam.visualization import rerun as rerun_helpers
from prml_vslam.visualization.contracts import VisualizationConfig
from prml_vslam.visualization.rerun_policy import RerunLoggingPolicy


def test_visualization_config_serializes_optional_viewer_blueprint_path() -> None:
    config = VisualizationConfig(
        connect_live_viewer=True,
        viewer_blueprint_path=Path(".configs/visualization/vista_blueprint.rbl"),
    )

    rendered = config.to_toml()
    reloaded = VisualizationConfig.from_toml(rendered)

    assert 'viewer_blueprint_path = ".configs/visualization/vista_blueprint.rbl"' in rendered
    assert reloaded.viewer_blueprint_path == Path(".configs/visualization/vista_blueprint.rbl")
    assert reloaded.log_source_rgb is False
    assert reloaded.log_diagnostic_preview is False
    assert reloaded.log_camera_image_rgb is False
    assert reloaded.trajectory_pose_axis_length == 0.0


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
    assert all(not query.startswith("- ") for query in layout.views[0].contents)
    assert "+ world/reference/trajectory/*/aligned/**" in layout.views[0].contents
    assert "+ world/reference/points/*/aligned/**" in layout.views[0].contents
    assert "+ world/keyframes/cameras/*" in layout.views[0].contents
    assert "- world/live/model/camera/image/**" not in layout.views[0].contents
    assert "- world/reference/**/source_native/**" not in layout.views[0].contents
    assert layout.views[1].name == "2D Views"
    assert [view.origin for view in layout.views[1].views] == [
        rerun_helpers.MODEL_RGB_2D_ENTITY_PATH,
        "world/live/model/camera/image",
    ]
    assert len(logged_entities) == 2
    entity_path, payload, static = logged_entities[0]
    assert entity_path == rerun_helpers.ROOT_WORLD_ENTITY_PATH
    assert isinstance(payload, FakeTransform3D)
    assert payload.axis_length == rerun_helpers.ROOT_WORLD_AXIS_LENGTH
    assert static is True
    entity_path, payload, static = logged_entities[1]
    assert entity_path == rerun_helpers.ROOT_WORLD_ENTITY_PATH
    assert payload == FakeViewCoordinates.RDF
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


def test_log_line_strip3d_logs_one_strip(monkeypatch) -> None:
    logged: list[tuple[str, object]] = []

    class FakeLineStrips3D:
        def __init__(self, strips, radii) -> None:
            self.strips = strips
            self.radii = radii

    class FakeRecordingStream:
        def log(self, entity_path: str, payload: object, *, static: bool = False) -> None:
            del static
            logged.append((entity_path, payload))

    monkeypatch.setattr(rerun_helpers, "rr", SimpleNamespace(LineStrips3D=FakeLineStrips3D))

    rerun_helpers.log_line_strip3d(
        FakeRecordingStream(),
        entity_path="world/slam/vista_slam_world/trajectory/raw",
        positions_xyz=np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]], dtype=np.float32),
    )

    assert len(logged) == 1
    entity_path, payload = logged[0]
    assert entity_path == "world/slam/vista_slam_world/trajectory/raw"
    assert len(payload.strips) == 1
    assert np.array_equal(payload.strips[0], np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]], dtype=np.float32))


def test_rerun_policy_logs_trajectory_artifact_as_line_and_pose_transforms(tmp_path: Path) -> None:
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
    policy = RerunLoggingPolicy(
        log_pinhole=lambda *args, **kwargs: None,
        log_pointcloud=lambda *args, **kwargs: None,
        log_pointcloud_ply=lambda *args, **kwargs: None,
        log_mesh_ply=lambda *args, **kwargs: None,
        log_line_strip3d=lambda stream, *, entity_path, positions_xyz, static=False: line_calls.append(
            (entity_path, static)
        ),
        log_clear=lambda *args, **kwargs: None,
        log_depth_image=lambda *args, **kwargs: None,
        log_ground_plane_patch=lambda *args, **kwargs: None,
        log_rgb_image=lambda *args, **kwargs: None,
        log_transform=lambda stream, *, entity_path, transform, axis_length=None, static=False: pose_calls.append(
            (entity_path, axis_length, static, transform)
        ),
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
        "world/reference/trajectory/ground_truth/aligned/poses/000000",
        "world/reference/trajectory/ground_truth/aligned/poses/000001",
    ]
    assert all(axis_length == 0.25 and static is True for _, axis_length, static, _ in pose_calls)
    assert pose_calls[1][3].target_frame == "advio_gt_world"
    assert pose_calls[1][3].tx == 1.0


def test_rerun_policy_skips_trajectory_pose_transforms_when_axis_length_is_zero(tmp_path: Path) -> None:
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
    policy = RerunLoggingPolicy(
        log_pinhole=lambda *args, **kwargs: None,
        log_pointcloud=lambda *args, **kwargs: None,
        log_pointcloud_ply=lambda *args, **kwargs: None,
        log_mesh_ply=lambda *args, **kwargs: None,
        log_line_strip3d=lambda stream, *, entity_path, positions_xyz, static=False: line_calls.append(
            (entity_path, static)
        ),
        log_clear=lambda *args, **kwargs: None,
        log_depth_image=lambda *args, **kwargs: None,
        log_ground_plane_patch=lambda *args, **kwargs: None,
        log_rgb_image=lambda *args, **kwargs: None,
        log_transform=lambda stream, *, entity_path, transform, axis_length=None, static=False: pose_calls.append(
            entity_path
        ),
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
    assert pose_calls == []


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

    monkeypatch.setattr(
        rerun_helpers,
        "rr",
        SimpleNamespace(
            Mesh3D=FakeMesh3D,
            LineStrips3D=FakeLineStrips3D,
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
        "world/alignment/ground_plane/fill",
        "world/alignment/ground_plane/outline",
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
