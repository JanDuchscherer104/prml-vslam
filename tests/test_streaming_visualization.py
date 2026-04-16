"""Tests for streaming viewer logging semantics."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest

from prml_vslam.benchmark import (
    PreparedBenchmarkInputs,
    ReferenceCloudCoordinateStatus,
    ReferenceCloudRef,
    ReferenceCloudSource,
)
from prml_vslam.datasets import DatasetId
from prml_vslam.interfaces import CameraIntrinsics, FramePacket, FrameTransform
from prml_vslam.methods import MethodId
from prml_vslam.methods.contracts import SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.pipeline import PipelineMode, RunRequest, SequenceManifest
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.contracts.request import DatasetSourceSpec, SlamStageConfig
from prml_vslam.pipeline.state import RunState, StreamingRunSnapshot
from prml_vslam.pipeline.streaming import StreamingRunner, _viewer_pose_from_update
from prml_vslam.utils import PathConfig
from prml_vslam.utils.geometry import write_point_cloud_ply


def test_streaming_runner_logs_live_pointmaps_under_posed_keyframe_entities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = RunRequest(
        experiment_name="advio-streaming-vista",
        mode=PipelineMode.STREAMING,
        output_dir=path_config.artifacts_dir,
        source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id="advio-15"),
        slam=SlamStageConfig(method=MethodId.VISTA),
    )
    request.visualization.connect_live_viewer = True
    plan = request.build(path_config)
    source = _FakeStreamingSource(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        stream=_FinitePacketStream(
            [
                _make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0),
                _make_packet(seq=1, timestamp_ns=2_000_000_000, tx=0.1),
                _make_packet(seq=2, timestamp_ns=3_000_000_000, tx=0.2),
            ]
        ),
    )
    recording = object()
    time_events: list[tuple[str, int]] = []
    transform_events: list[tuple[str, np.ndarray, np.ndarray]] = []
    pointcloud_paths: list[str] = []
    reference_paths: list[str] = []
    preview_paths: list[str] = []
    coordinates_paths: list[str] = []

    monkeypatch.setattr("prml_vslam.pipeline.streaming.VIEWER_HOOKS.create_recording_stream", lambda **_: recording)
    monkeypatch.setattr("prml_vslam.pipeline.streaming.VIEWER_HOOKS.attach_recording_sinks", lambda *_, **__: None)
    monkeypatch.setattr(
        "prml_vslam.pipeline.streaming.VIEWER_HOOKS.log_y_up_view_coordinates",
        lambda _recording, *, entity_path: coordinates_paths.append(entity_path),
    )
    monkeypatch.setattr(
        "prml_vslam.pipeline.streaming.VIEWER_HOOKS.set_time_sequence",
        lambda _recording, *, timeline, sequence: time_events.append((timeline, sequence)),
    )
    monkeypatch.setattr(
        "prml_vslam.pipeline.streaming.VIEWER_HOOKS.log_transform",
        lambda _recording, *, entity_path, transform: transform_events.append(
            (entity_path, transform.translation_xyz(), transform.as_matrix()[:3, :3])
        ),
    )
    monkeypatch.setattr(
        "prml_vslam.pipeline.streaming.VIEWER_HOOKS.log_pointcloud",
        lambda _recording, *, entity_path, pointmap, colors=None: pointcloud_paths.append(entity_path),
    )
    monkeypatch.setattr(
        "prml_vslam.pipeline.streaming.VIEWER_HOOKS.log_points3d",
        lambda _recording, *, entity_path, points_xyz, **kwargs: reference_paths.append(entity_path),
    )
    monkeypatch.setattr(
        "prml_vslam.pipeline.streaming.VIEWER_HOOKS.log_preview_image",
        lambda _recording, *, entity_path, image_rgb: preview_paths.append(entity_path),
    )
    runner = StreamingRunner(frame_timeout_seconds=0.01)

    runner.start(request=request, plan=plan, source=source, slam_backend=_KeyframeStreamingBackend())
    snapshot = _wait_for_terminal_snapshot(runner)

    assert snapshot.state is RunState.COMPLETED
    assert coordinates_paths == ["world"]
    assert reference_paths == []
    assert time_events == [("keyframe", 0), ("keyframe", 1)]
    assert pointcloud_paths == ["world/est/cam_000000/points", "world/est/cam_000001/points"]
    assert "camera/pointcloud" not in pointcloud_paths
    assert [path for path, _, _ in transform_events] == [
        "world/live_camera",
        "world/est/cam_000000",
        "world/live_camera",
        "world/est/cam_000001",
    ]
    viewer_basis = np.diag([1.0, -1.0, -1.0])
    assert all(np.allclose(rotation, viewer_basis) for _, _, rotation in transform_events)
    assert np.allclose(transform_events[-1][1], np.array([0.2, 0.0, 0.0]))
    assert preview_paths == [
        "world/live_camera/preview",
        "world/est/cam_000000/preview",
        "world/live_camera/preview",
        "world/est/cam_000001/preview",
    ]


def test_streaming_runner_logs_only_aligned_reference_clouds_under_explicit_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = RunRequest(
        experiment_name="advio-streaming-vista",
        mode=PipelineMode.STREAMING,
        output_dir=path_config.artifacts_dir,
        source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id="advio-15"),
        slam=SlamStageConfig(method=MethodId.VISTA),
    )
    request.visualization.connect_live_viewer = True
    plan = request.build(path_config)
    aligned_cloud_path = write_point_cloud_ply(tmp_path / "aligned.ply", np.array([[1.0, 2.0, 3.0]]))
    source_native_path = write_point_cloud_ply(tmp_path / "source_native.ply", np.array([[9.0, 9.0, 9.0]]))
    metadata_path = tmp_path / "cloud.metadata.json"
    metadata_path.write_text("{}", encoding="utf-8")
    source = _FakeStreamingSource(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        benchmark_inputs=PreparedBenchmarkInputs(
            reference_clouds=[
                ReferenceCloudRef(
                    source=ReferenceCloudSource.TANGO_AREA_LEARNING,
                    path=source_native_path,
                    metadata_path=metadata_path,
                    target_frame="advio_tango_area_learning_world",
                    coordinate_status=ReferenceCloudCoordinateStatus.SOURCE_NATIVE,
                ),
                ReferenceCloudRef(
                    source=ReferenceCloudSource.TANGO_AREA_LEARNING,
                    path=aligned_cloud_path,
                    metadata_path=metadata_path,
                    target_frame="advio_gt_world",
                    coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
                ),
            ]
        ),
        stream=_FinitePacketStream([_make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0)]),
    )
    reference_paths: list[str] = []

    monkeypatch.setattr("prml_vslam.pipeline.streaming.VIEWER_HOOKS.create_recording_stream", lambda **_: object())
    monkeypatch.setattr("prml_vslam.pipeline.streaming.VIEWER_HOOKS.attach_recording_sinks", lambda *_, **__: None)
    monkeypatch.setattr("prml_vslam.pipeline.streaming.VIEWER_HOOKS.log_y_up_view_coordinates", lambda *_, **__: None)
    monkeypatch.setattr("prml_vslam.pipeline.streaming.VIEWER_HOOKS.log_transform", lambda *_, **__: None)
    monkeypatch.setattr("prml_vslam.pipeline.streaming.VIEWER_HOOKS.log_pointcloud", lambda *_, **__: None)
    monkeypatch.setattr("prml_vslam.pipeline.streaming.VIEWER_HOOKS.log_preview_image", lambda *_, **__: None)
    monkeypatch.setattr("prml_vslam.pipeline.streaming.VIEWER_HOOKS.set_time_sequence", lambda *_, **__: None)
    monkeypatch.setattr(
        "prml_vslam.pipeline.streaming.VIEWER_HOOKS.log_points3d",
        lambda _recording, *, entity_path, points_xyz, **kwargs: reference_paths.append(entity_path),
    )

    runner = StreamingRunner(frame_timeout_seconds=0.01)
    runner.start(request=request, plan=plan, source=source, slam_backend=_KeyframeStreamingBackend())
    snapshot = _wait_for_terminal_snapshot(runner)

    assert snapshot.state is RunState.COMPLETED
    assert reference_paths == ["world/reference/aligned_gt_world/tango_area_learning"]


def test_streaming_runner_warns_and_continues_when_one_aligned_reference_cloud_is_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = RunRequest(
        experiment_name="advio-streaming-vista",
        mode=PipelineMode.STREAMING,
        output_dir=path_config.artifacts_dir,
        source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id="advio-15"),
        slam=SlamStageConfig(method=MethodId.VISTA),
    )
    request.visualization.connect_live_viewer = True
    plan = request.build(path_config)
    missing_cloud_path = tmp_path / "missing-aligned.ply"
    aligned_cloud_path = write_point_cloud_ply(tmp_path / "aligned.ply", np.array([[1.0, 2.0, 3.0]]))
    metadata_path = tmp_path / "cloud.metadata.json"
    metadata_path.write_text("{}", encoding="utf-8")
    source = _FakeStreamingSource(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        benchmark_inputs=PreparedBenchmarkInputs(
            reference_clouds=[
                ReferenceCloudRef(
                    source=ReferenceCloudSource.TANGO_AREA_LEARNING,
                    path=missing_cloud_path,
                    metadata_path=metadata_path,
                    target_frame="advio_gt_world",
                    coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
                ),
                ReferenceCloudRef(
                    source=ReferenceCloudSource.TANGO_AREA_LEARNING,
                    path=aligned_cloud_path,
                    metadata_path=metadata_path,
                    target_frame="advio_gt_world",
                    coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
                ),
            ]
        ),
        stream=_FinitePacketStream([_make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0)]),
    )
    reference_paths: list[str] = []
    warnings: list[str] = []

    monkeypatch.setattr("prml_vslam.pipeline.streaming.VIEWER_HOOKS.create_recording_stream", lambda **_: object())
    monkeypatch.setattr("prml_vslam.pipeline.streaming.VIEWER_HOOKS.attach_recording_sinks", lambda *_, **__: None)
    monkeypatch.setattr("prml_vslam.pipeline.streaming.VIEWER_HOOKS.log_y_up_view_coordinates", lambda *_, **__: None)
    monkeypatch.setattr("prml_vslam.pipeline.streaming.VIEWER_HOOKS.log_transform", lambda *_, **__: None)
    monkeypatch.setattr("prml_vslam.pipeline.streaming.VIEWER_HOOKS.log_pointcloud", lambda *_, **__: None)
    monkeypatch.setattr("prml_vslam.pipeline.streaming.VIEWER_HOOKS.log_preview_image", lambda *_, **__: None)
    monkeypatch.setattr("prml_vslam.pipeline.streaming.VIEWER_HOOKS.set_time_sequence", lambda *_, **__: None)
    monkeypatch.setattr(
        "prml_vslam.pipeline.streaming.VIEWER_HOOKS.log_points3d",
        lambda _recording, *, entity_path, points_xyz, **kwargs: reference_paths.append(entity_path),
    )
    runner = StreamingRunner(frame_timeout_seconds=0.01)
    monkeypatch.setattr(runner._console, "warning", lambda message: warnings.append(message))

    runner.start(request=request, plan=plan, source=source, slam_backend=_KeyframeStreamingBackend())
    snapshot = _wait_for_terminal_snapshot(runner)

    assert snapshot.state is RunState.COMPLETED
    assert reference_paths == ["world/reference/aligned_gt_world/tango_area_learning"]
    assert len(warnings) == 1
    assert "Skipping aligned reference cloud" in warnings[0]
    assert str(missing_cloud_path) in warnings[0]


def test_vista_viewer_pose_maps_rdf_world_to_advio_y_up_world() -> None:
    update = SlamUpdate(
        seq=0,
        timestamp_ns=0,
        pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0),
    )

    viewer_pose = _viewer_pose_from_update(update, method_id=MethodId.VISTA)

    assert np.allclose(viewer_pose.translation_xyz(), np.array([1.0, -2.0, -3.0]))
    assert np.allclose(viewer_pose.as_matrix()[:3, :3], np.diag([1.0, -1.0, -1.0]))


class _KeyframeStreamingBackend:
    method_id = MethodId.VISTA

    def start_session(
        self,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> object:
        del backend_config, output_policy
        return _KeyframeStreamingSession(artifact_root=artifact_root)


class _KeyframeStreamingSession:
    def __init__(self, *, artifact_root: Path) -> None:
        self._artifact_root = artifact_root
        self._updates = iter(
            [
                SlamUpdate(
                    seq=0,
                    timestamp_ns=1_000_000_000,
                    pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
                    is_keyframe=True,
                    keyframe_index=0,
                    preview_rgb=np.zeros((2, 2, 3), dtype=np.uint8),
                    pointmap=np.zeros((2, 2, 3), dtype=np.float32),
                ),
                SlamUpdate(seq=1, timestamp_ns=2_000_000_000, is_keyframe=False),
                SlamUpdate(
                    seq=2,
                    timestamp_ns=3_000_000_000,
                    pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.2, ty=0.0, tz=0.0),
                    is_keyframe=True,
                    keyframe_index=1,
                    preview_rgb=np.ones((2, 2, 3), dtype=np.uint8),
                    pointmap=np.zeros((2, 2, 3), dtype=np.float32),
                ),
            ]
        )
        self._pending: list[SlamUpdate] = []

    def step(self, frame: FramePacket) -> None:
        del frame
        self._pending.append(next(self._updates))

    def try_get_updates(self) -> list[SlamUpdate]:
        updates = self._pending
        self._pending = []
        return updates

    def close(self) -> SlamArtifacts:
        trajectory_path = self._artifact_root / "slam" / "trajectory.tum"
        trajectory_path.parent.mkdir(parents=True, exist_ok=True)
        trajectory_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
        return SlamArtifacts(
            trajectory_tum=ArtifactRef(path=trajectory_path, kind="tum", fingerprint="keyframe-streaming"),
        )


class _FakeStreamingSource:
    def __init__(
        self,
        *,
        sequence_manifest: SequenceManifest,
        stream: object,
        benchmark_inputs: PreparedBenchmarkInputs | None = None,
    ) -> None:
        self.sequence_manifest = sequence_manifest
        self.stream = stream
        self.benchmark_inputs = benchmark_inputs

    @property
    def label(self) -> str:
        return "fake-streaming"

    def prepare_sequence_manifest(self, _output_dir: Path) -> SequenceManifest:
        return self.sequence_manifest

    def prepare_benchmark_inputs(self, _output_dir: Path) -> PreparedBenchmarkInputs | None:
        return self.benchmark_inputs

    def open_stream(self, *, loop: bool = False) -> object:
        del loop
        return self.stream


class _FinitePacketStream:
    def __init__(self, packets: list[FramePacket]) -> None:
        self.packets = iter(packets)

    def connect(self) -> None:
        return None

    def wait_for_packet(self, timeout_seconds: float) -> FramePacket:
        del timeout_seconds
        try:
            return next(self.packets)
        except StopIteration:
            raise EOFError from None

    def disconnect(self) -> None:
        pass


def _make_packet(*, seq: int, timestamp_ns: int, tx: float) -> FramePacket:
    return FramePacket(
        seq=seq,
        timestamp_ns=timestamp_ns,
        rgb=np.zeros((4, 4, 3), dtype=np.uint8),
        intrinsics=CameraIntrinsics(fx=200.0, fy=200.0, cx=1.5, cy=1.5, width_px=4, height_px=4),
        pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=tx, ty=0.0, tz=0.0),
    )


def _wait_for_terminal_snapshot(runner: StreamingRunner, *, timeout_seconds: float = 2.5) -> StreamingRunSnapshot:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        snapshot = runner.snapshot()
        if snapshot.state in (RunState.COMPLETED, RunState.FAILED, RunState.STOPPED):
            return snapshot
        time.sleep(0.05)
    raise TimeoutError("Pipeline runner did not reach a terminal state.")
