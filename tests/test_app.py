"""Focused app/controller tests for the refactored pipeline surface."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from prml_vslam.app.bootstrap import _PAGE_SPECS
from prml_vslam.app.models import AppPageId, AppState, ArtifactInspectorPageState, PipelineSourceId
from prml_vslam.app.pipeline_controller import (
    PipelinePageAction,
    action_from_page_state,
    build_pipeline_snapshot_render_model,
    build_request_from_action,
    request_support_error,
    sync_pipeline_page_state_from_template,
)
from prml_vslam.datasets.advio import AdvioServingConfig
from prml_vslam.interfaces import CameraIntrinsics, FramePacketProvenance, FrameTransform
from prml_vslam.interfaces.slam import KeyframeVisualizationReady
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts.events import BackendNoticeReceived, FramePacketSummary, RunStarted
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.provenance import StageManifest, StageStatus
from prml_vslam.pipeline.contracts.request import DatasetSourceSpec, SlamStageConfig, build_backend_spec
from prml_vslam.pipeline.contracts.runtime import RunState, StreamingRunSnapshot
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.utils import PathConfig


def test_artifact_page_is_registered_and_state_round_trips() -> None:
    assert any(
        page_id is AppPageId.ARTIFACTS and page_module == "artifacts" for page_id, _, page_module, _ in _PAGE_SPECS
    )

    state = AppState(
        artifacts=ArtifactInspectorPageState(
            selected_run_root=Path(".artifacts/demo/vista"),
            manual_run_root=".artifacts/manual/vista",
            use_manual_path=True,
            show_reconstruction_point_cloud=False,
            show_reconstruction_mesh=True,
            reconstruction_max_points=40_000,
            reconstruction_target_triangles=60_000,
            reconstruction_mesh_opacity=0.55,
            reconstruction_mesh_color="#7b1fa2",
        )
    )

    reloaded = AppState.model_validate(state.model_dump(mode="json"))

    assert reloaded.artifacts.selected_run_root == Path(".artifacts/demo/vista")
    assert reloaded.artifacts.manual_run_root == ".artifacts/manual/vista"
    assert reloaded.artifacts.use_manual_path is True
    assert reloaded.artifacts.show_reconstruction_point_cloud is False
    assert reloaded.artifacts.show_reconstruction_mesh is True
    assert reloaded.artifacts.reconstruction_max_points == 40_000
    assert reloaded.artifacts.reconstruction_target_triangles == 60_000
    assert reloaded.artifacts.reconstruction_mesh_opacity == 0.55
    assert reloaded.artifacts.reconstruction_mesh_color == "#7b1fa2"


def test_build_request_from_action_derives_backend_kind(tmp_path: Path) -> None:
    context = type(
        "Context",
        (),
        {
            "path_config": PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts"),
            "advio_service": type(
                "AdvioService",
                (),
                {"scene": lambda self, _sequence_id: type("Scene", (), {"sequence_slug": "advio-01"})()},
            )(),
        },
    )()
    action = PipelinePageAction(
        config_path=Path(".configs/pipelines/demo.toml"),
        experiment_name="demo",
        source_kind=PipelineSourceId.ADVIO,
        advio_sequence_id=1,
        mode=PipelineMode.OFFLINE,
        method=MethodId.VISTA,
        slam_max_frames=12,
        slam_backend_spec=None,
        emit_dense_points=True,
        emit_sparse_points=False,
        reference_enabled=False,
        trajectory_eval_enabled=False,
        evaluate_cloud=False,
        evaluate_efficiency=False,
        connect_live_viewer=False,
        export_viewer_rrd=False,
    )

    request, error = build_request_from_action(context, action)

    assert error is None
    assert isinstance(request, RunRequest)
    assert request.slam.backend.kind == "vista"
    assert request.slam.backend.kind == MethodId.VISTA.value


def test_build_request_from_action_accepts_stringified_vista_paths(tmp_path: Path) -> None:
    context = type(
        "Context",
        (),
        {
            "path_config": PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts"),
            "advio_service": type(
                "AdvioService",
                (),
                {"scene": lambda self, _sequence_id: type("Scene", (), {"sequence_slug": "advio-01"})()},
            )(),
        },
    )()
    action = PipelinePageAction(
        config_path=Path(".configs/pipelines/demo.toml"),
        experiment_name="demo",
        source_kind=PipelineSourceId.ADVIO,
        advio_sequence_id=1,
        mode=PipelineMode.OFFLINE,
        method=MethodId.VISTA,
        slam_max_frames=12,
        slam_backend_spec=build_backend_spec(
            method=MethodId.VISTA,
            overrides={
                "vista_slam_dir": Path("external/vista-slam"),
                "checkpoint_path": Path("external/vista-slam/pretrains/frontend_sta_weights.pth"),
                "vocab_path": Path("external/vista-slam/pretrains/ORBvoc.txt"),
            },
        ),
        pose_source="ground_truth",
        respect_video_rotation=True,
        connect_live_viewer=False,
        export_viewer_rrd=False,
    )

    request, error = build_request_from_action(context, action)

    assert error is None
    assert isinstance(request, RunRequest)
    assert request.source.dataset_serving == AdvioServingConfig(
        pose_source="ground_truth",
        pose_frame_mode="provider_world",
    )
    assert request.source.respect_video_rotation is True
    assert request.slam.backend.vista_slam_dir == Path("external/vista-slam")


def test_sync_pipeline_template_preserves_typed_vista_backend_spec(tmp_path: Path) -> None:
    class _Store:
        def save(self, state: AppState) -> None:
            self.payload = state.model_dump(mode="json")

    context = type(
        "Context",
        (),
        {
            "store": _Store(),
            "state": AppState(),
            "path_config": PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts"),
            "advio_service": type(
                "AdvioService",
                (),
                {"scene": lambda self, _sequence_id: type("Scene", (), {"sequence_slug": "advio-01"})()},
            )(),
        },
    )()
    request = RunRequest(
        experiment_name="vista-page",
        mode=PipelineMode.OFFLINE,
        output_dir=context.path_config.artifacts_dir,
        source=DatasetSourceSpec(
            dataset_id="advio",
            sequence_id="advio-01",
            dataset_serving={
                "dataset_id": "advio",
                "pose_source": "ground_truth",
                "pose_frame_mode": "provider_world",
            },
            respect_video_rotation=True,
        ),
        slam=SlamStageConfig(
            backend={
                "kind": "vista",
                "vista_slam_dir": Path("external/vista-slam"),
                "checkpoint_path": Path("external/vista-slam/pretrains/frontend_sta_weights.pth"),
                "vocab_path": Path("external/vista-slam/pretrains/ORBvoc.txt"),
            }
        ),
    )

    sync_pipeline_page_state_from_template(
        context=context,
        config_path=Path(".configs/pipelines/vista-full.toml"),
        request=request,
        statuses=[],
    )

    backend_spec = context.state.pipeline.slam_backend_spec
    assert backend_spec is not None
    assert backend_spec.kind == "vista"
    assert backend_spec.vista_slam_dir == Path("external/vista-slam")
    assert context.state.pipeline.pose_source.value == "ground_truth"
    assert context.state.pipeline.pose_frame_mode.value == "provider_world"
    assert context.state.pipeline.respect_video_rotation is True
    action = action_from_page_state(context.state.pipeline, Path(".configs/pipelines/vista-full.toml"))
    rebuilt_request, error = build_request_from_action(context, action)

    assert error is None
    assert isinstance(rebuilt_request, RunRequest)
    assert rebuilt_request.slam.backend.vista_slam_dir == Path("external/vista-slam")
    assert rebuilt_request.source.respect_video_rotation is True


def test_request_support_error_uses_stage_availability_reason(tmp_path: Path) -> None:
    path_config = PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest(
        experiment_name="placeholder",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source=DatasetSourceSpec(
            dataset_id="advio",
            sequence_id="advio-01",
            dataset_serving={"dataset_id": "advio", "pose_source": "ground_truth", "pose_frame_mode": "provider_world"},
        ),
        slam={"backend": {"kind": "mock"}},
        benchmark={"cloud": {"enabled": True}},
    )
    plan = request.build(path_config)

    error = request_support_error(request=request, plan=plan, previewable_statuses=[])

    assert error is not None
    assert "placeholder" in error


def test_pipeline_snapshot_render_model_shapes_streaming_payloads(tmp_path: Path) -> None:
    request = RunRequest(
        experiment_name="streaming-demo",
        mode=PipelineMode.STREAMING,
        output_dir=tmp_path / ".artifacts",
        source=DatasetSourceSpec(
            dataset_id="advio",
            sequence_id="advio-01",
            dataset_serving={"dataset_id": "advio", "pose_source": "ground_truth", "pose_frame_mode": "provider_world"},
        ),
        slam=SlamStageConfig(backend={"kind": "vista"}),
    )
    plan = RunPlan(
        run_id="streaming-demo",
        mode=PipelineMode.STREAMING,
        artifact_root=tmp_path / "streaming-demo",
        source=request.source,
    )
    snapshot = StreamingRunSnapshot(
        run_id="streaming-demo",
        state=RunState.RUNNING,
        plan=plan,
        latest_packet=FramePacketSummary(seq=4, timestamp_ns=44, provenance=FramePacketProvenance(source_id="demo")),
        latest_frame=ArrayHandle(handle_id="frame", shape=(2, 2, 3), dtype="uint8"),
        latest_preview=PreviewHandle(handle_id="preview", width=2, height=2, channels=3, dtype="uint8"),
        received_frames=4,
        measured_fps=20.0,
        accepted_keyframes=2,
        backend_fps=5.0,
        num_sparse_points=7,
        num_dense_points=9,
        trajectory_positions_xyz=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)],
        trajectory_timestamps_s=[0.0, 1.0],
        stage_manifests=[
            StageManifest(
                stage_id="slam",
                config_hash="cfg",
                input_fingerprint="inp",
                status=StageStatus.COMPLETED,
            )
        ],
    )
    notice_event = BackendNoticeReceived(
        event_id="2",
        run_id="streaming-demo",
        ts_ns=2,
        stage_key=StageKey.SLAM,
        notice=KeyframeVisualizationReady(
            seq=4,
            timestamp_ns=44,
            source_seq=4,
            source_timestamp_ns=44,
            keyframe_index=1,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.0, tz=0.0),
            camera_intrinsics=CameraIntrinsics(fx=2.0, fy=2.0, cx=1.0, cy=1.0, width_px=2, height_px=2),
        ),
    )

    class FakeRunService:
        def read_array(self, handle):
            if handle is None:
                return None
            return {
                "frame": np.ones((2, 2, 3), dtype=np.uint8),
                "preview": np.zeros((2, 2, 3), dtype=np.uint8),
            }[handle.handle_id]

        def tail_events(self, *, limit: int = 200, after_event_id: str | None = None):
            del limit, after_event_id
            return [
                RunStarted(event_id="1", run_id="streaming-demo", ts_ns=1),
                notice_event,
            ]

    model = build_pipeline_snapshot_render_model(
        snapshot, FakeRunService(), method=MethodId.VISTA, show_evo_preview=False
    )

    assert model.caption is not None
    assert "ViSTA-SLAM" in model.caption
    assert model.streaming is not None
    assert model.streaming.frame_image is not None
    assert model.streaming.preview_image is not None
    assert model.streaming.packet_metadata == {
        "seq": 4,
        "timestamp_ns": 44,
        "provenance": {"source_id": "demo"},
    }
    assert model.streaming.backend_notice is not None
    assert model.streaming.backend_notice.camera_intrinsics is not None
    assert model.stage_manifest_rows[0]["Stage"] == "slam"
    assert model.recent_events[-1]["kind"] == "backend.notice"


def test_pipeline_snapshot_render_model_shapes_vista_empty_states(tmp_path: Path) -> None:
    request = RunRequest(
        experiment_name="streaming-demo",
        mode=PipelineMode.STREAMING,
        output_dir=tmp_path / ".artifacts",
        source=DatasetSourceSpec(
            dataset_id="advio",
            sequence_id="advio-01",
            dataset_serving={"dataset_id": "advio", "pose_source": "ground_truth", "pose_frame_mode": "provider_world"},
        ),
        slam=SlamStageConfig(backend={"kind": "vista"}),
    )
    plan = RunPlan(
        run_id="streaming-demo",
        mode=PipelineMode.STREAMING,
        artifact_root=tmp_path / "streaming-demo",
        source=request.source,
    )
    snapshot = StreamingRunSnapshot(run_id="streaming-demo", state=RunState.RUNNING, plan=plan)

    class FakeRunService:
        def read_array(self, handle):
            del handle
            return None

        def tail_events(self, *, limit: int = 200, after_event_id: str | None = None):
            del limit, after_event_id
            return []

    model = build_pipeline_snapshot_render_model(
        snapshot, FakeRunService(), method=MethodId.VISTA, show_evo_preview=False
    )

    assert model.streaming is not None
    assert "ViSTA-SLAM has not produced" in model.streaming.preview_empty_message
    assert "ViSTA-SLAM has not accepted" in model.streaming.trajectory_empty_message


def test_pipeline_snapshot_render_model_only_resolves_evo_preview_when_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    request = RunRequest(
        experiment_name="streaming-demo",
        mode=PipelineMode.STREAMING,
        output_dir=tmp_path / ".artifacts",
        source=DatasetSourceSpec(
            dataset_id="advio",
            sequence_id="advio-01",
            dataset_serving={"dataset_id": "advio", "pose_source": "ground_truth", "pose_frame_mode": "provider_world"},
        ),
        slam=SlamStageConfig(backend={"kind": "mock"}),
    )
    plan = RunPlan(
        run_id="streaming-demo",
        mode=PipelineMode.STREAMING,
        artifact_root=tmp_path / "streaming-demo",
        source=request.source,
    )
    snapshot = StreamingRunSnapshot(run_id="streaming-demo", state=RunState.RUNNING, plan=plan)
    calls = {"count": 0}

    def fake_resolve_evo_preview(_snapshot):
        calls["count"] += 1
        return None, "preview boom"

    class FakeRunService:
        def read_array(self, handle):
            del handle
            return None

        def tail_events(self, *, limit: int = 200, after_event_id: str | None = None):
            del limit, after_event_id
            return []

    monkeypatch.setattr("prml_vslam.app.pipeline_controller.resolve_evo_preview", fake_resolve_evo_preview)

    disabled = build_pipeline_snapshot_render_model(
        snapshot, FakeRunService(), method=MethodId.MOCK, show_evo_preview=False
    )
    enabled = build_pipeline_snapshot_render_model(
        snapshot, FakeRunService(), method=MethodId.MOCK, show_evo_preview=True
    )

    assert disabled.streaming is not None
    assert disabled.streaming.evo_error is None
    assert enabled.streaming is not None
    assert enabled.streaming.evo_error == "preview boom"
    assert calls["count"] == 1
