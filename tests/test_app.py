"""Focused app/controller tests for the refactored pipeline surface."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.app.models import AppState, PipelineSourceId
from prml_vslam.app.pipeline_controller import (
    PipelinePageAction,
    action_from_page_state,
    build_request_from_action,
    request_support_error,
    sync_pipeline_page_state_from_template,
)
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts.request import DatasetSourceSpec, SlamStageConfig, build_backend_spec
from prml_vslam.utils import PathConfig


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
    assert request.source.pose_source.value == "ground_truth"
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
            pose_source="ground_truth",
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
        source=DatasetSourceSpec(dataset_id="advio", sequence_id="advio-01"),
        slam={"backend": {"kind": "mock"}},
        benchmark={"cloud": {"enabled": True}},
    )
    plan = request.build(path_config)

    error = request_support_error(request=request, plan=plan, previewable_statuses=[])

    assert error is not None
    assert "placeholder" in error
