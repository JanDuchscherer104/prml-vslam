"""Tests for repo-owned visualization helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

# Import pipeline first to avoid the known package-init cycle between
# `visualization.contracts` and `pipeline.contracts.request` during test collection.
import prml_vslam.pipeline  # noqa: F401
from prml_vslam.interfaces import FrameTransform
from prml_vslam.visualization import rerun as rerun_helpers


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


def test_create_recording_stream_uses_world_based_default_blueprint(monkeypatch) -> None:
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
        def __init__(self, *, origin: str, name: str) -> None:
            self.origin = origin
            self.name = name

    class FakeSpatial2DView:
        def __init__(self, *, origin: str, name: str) -> None:
            self.origin = origin
            self.name = name

    class FakeHorizontal:
        def __init__(self, *views: object) -> None:
            self.views = views

    class FakeBlueprint:
        def __init__(self, layout: object) -> None:
            self.layout = layout

    monkeypatch.setattr(
        rerun_helpers,
        "rr",
        SimpleNamespace(RecordingStream=FakeRecordingStream, ViewCoordinates=SimpleNamespace(RDF="rdf")),
    )
    monkeypatch.setattr(
        rerun_helpers,
        "rrb",
        SimpleNamespace(
            Blueprint=FakeBlueprint,
            Horizontal=FakeHorizontal,
            Spatial3DView=FakeSpatial3DView,
            Spatial2DView=FakeSpatial2DView,
        ),
    )

    stream = rerun_helpers.create_recording_stream(app_id="prml-vslam", recording_id="demo")

    assert isinstance(stream, FakeRecordingStream)
    assert len(sent_blueprints) == 1
    layout = sent_blueprints[0].layout
    assert layout.views[0].origin == "world"
    assert layout.views[1].origin == "world/live/camera/cam"
    assert logged_entities == [("world", "rdf", True)]


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
        def log(self, entity_path: str, payload: object) -> None:
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
