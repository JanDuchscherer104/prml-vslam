"""Focused app/controller tests for the refactored pipeline surface."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
from evo.core import metrics

import prml_vslam.app.pipeline_controls as pipeline_controls
from prml_vslam.app.bootstrap import _PAGE_SPECS
from prml_vslam.app.live_session import render_live_action_slot
from prml_vslam.app.models import (
    AdvioPageState,
    AppPageId,
    AppState,
    ArtifactInspectorPageState,
    MetricsPageState,
    PipelinePageState,
    PipelineSourceId,
    PipelineTelemetryMetricId,
    PipelineTelemetryViewMode,
    Record3DDatasetPageState,
    Record3DDatasetPoseSource,
)
from prml_vslam.app.pipeline_controller import (
    build_pipeline_snapshot_render_model,
    build_pipeline_viewer_link_model,
    refreshed_pipeline_telemetry_history,
)
from prml_vslam.app.pipeline_controls import (
    PipelinePageAction,
    action_from_page_state,
    build_run_config_from_action,
    request_support_error,
    sync_pipeline_page_state_from_template,
)
from prml_vslam.eval.query import TrajectoryEvaluationQueryService
from prml_vslam.eval.trajectory_contracts import DiscoveredRun, TrajectoryEvaluationManifest
from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.config import RunConfig, build_backend_spec, build_run_config
from prml_vslam.pipeline.contracts.events import RunStarted, StageOutcome
from prml_vslam.pipeline.contracts.plan import PlannedSource, RunPlan, RunPlanStage
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageRuntimeStatus
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.sources.config import AdvioSourceConfig
from prml_vslam.sources.contracts import SequenceManifest
from prml_vslam.sources.datasets.advio import AdvioServingConfig
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.datasets.normalized_query import normalized_query_fingerprint
from prml_vslam.sources.record3d.record3d import Record3DTransportId
from prml_vslam.utils import PathConfig


def test_normalized_store_fingerprint_uses_shared_datastore_root(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    store_root = path_config.resolve_normalized_datastore_dir("record3d")
    entry_root = store_root / "synthetic" / "profile"
    entry_root.mkdir(parents=True)
    (entry_root / "entry.json").write_text("{}", encoding="utf-8")
    (entry_root / "sequence_manifest.json").write_text("{}", encoding="utf-8")
    (entry_root / "stats_long.csv").write_text(
        "dataset_id,sequence_id,profile_key,source_id,scope,subject,stat,value,unit\n", encoding="utf-8"
    )
    (entry_root / "metadata_long.csv").write_text(
        "dataset_id,sequence_id,profile_key,source_id,scope,key,value\n", encoding="utf-8"
    )
    old_root = path_config.resolve_dataset_dir("record3d") / ".normalized" / "synthetic" / "profile"
    old_root.mkdir(parents=True)
    (old_root / "entry.json").write_text("{}", encoding="utf-8")
    fingerprint = normalized_query_fingerprint(path_config, DatasetId.RECORD3D)

    assert [row[0] for row in fingerprint] == [
        "synthetic/profile/entry.json",
        "synthetic/profile/metadata_long.csv",
        "synthetic/profile/sequence_manifest.json",
        "synthetic/profile/stats_long.csv",
    ]


def test_metrics_page_state_preserves_persisted_view_fields() -> None:
    state = MetricsPageState()

    assert state.scope == "sequence"
    assert state.dataset_primary_metric == "ape/translation_part/rmse"


def test_advio_tum_dataset_state_round_trips_without_download_modality_fields() -> None:
    state = AppState.model_validate(
        {
            "advio": {"download_" + "preset": "offline", "selected_" + "modalities": ["iphone_video"]},
            "tum_rgbd": {"download_" + "preset": "offline", "selected_" + "modalities": ["rgb"]},
        }
    )

    dumped = state.model_dump(mode="json")

    assert "download_" + "preset" not in dumped["advio"]
    assert "selected_" + "modalities" not in dumped["advio"]
    assert "download_" + "preset" not in dumped["tum_rgbd"]
    assert "selected_" + "modalities" not in dumped["tum_rgbd"]


def test_render_live_action_slot_uses_stable_start_and_stop_keys(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_button(label: str, **kwargs: object) -> bool:
        calls.append({"label": label, **kwargs})
        return label.startswith("Start")

    monkeypatch.setattr("prml_vslam.app.live_session.st.button", fake_button)

    assert render_live_action_slot(
        is_active=False,
        start_label="Start demo",
        stop_label="Stop demo",
        key="demo-slot",
        start_disabled=True,
    ) == (True, False)
    assert calls[-1] == {
        "label": "Start demo",
        "key": "demo-slot:start",
        "type": "primary",
        "disabled": True,
        "use_container_width": True,
    }

    assert render_live_action_slot(
        is_active=True,
        start_label="Start demo",
        stop_label="Stop demo",
        key="demo-slot",
    ) == (False, False)
    assert calls[-1] == {
        "label": "Stop demo",
        "key": "demo-slot:stop",
        "use_container_width": True,
    }


def test_live_action_slot_call_sites_define_unique_stable_keys() -> None:
    page_paths = (
        Path("src/prml_vslam/app/pages/datasets.py"),
        Path("src/prml_vslam/app/pages/pipeline.py"),
        Path("src/prml_vslam/app/pages/record3d.py"),
    )
    keys: list[str] = []

    for page_path in page_paths:
        tree = ast.parse(page_path.read_text(encoding="utf-8"), filename=str(page_path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "render_live_action_slot":
                continue
            key_keywords = [keyword for keyword in node.keywords if keyword.arg == "key"]
            assert len(key_keywords) == 1, f"{page_path}:{node.lineno} must pass one key="
            key_value = key_keywords[0].value
            if isinstance(key_value, ast.Constant) and isinstance(key_value.value, str):
                keys.append(key_value.value)
                continue
            if isinstance(key_value, ast.Name) and key_value.id == "action_key_prefix":
                keys.extend(_literal_keywords_for_calls(tree, "_render_loop_preview_impl", "action_key_prefix"))
                continue
            raise AssertionError(f"{page_path}:{node.lineno} must use a stable literal key prefix")

    assert keys
    assert len(keys) == len(set(keys))


def _literal_keywords_for_calls(tree: ast.AST, function_name: str, keyword_name: str) -> list[str]:
    values: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != function_name:
            continue
        keyword_values = [keyword.value for keyword in node.keywords if keyword.arg == keyword_name]
        assert len(keyword_values) == 1, f"{function_name}() must pass one {keyword_name}="
        keyword_value = keyword_values[0]
        assert isinstance(keyword_value, ast.Constant) and isinstance(keyword_value.value, str)
        values.append(keyword_value.value)
    return values


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
            comparison_show_slam_cloud=False,
            comparison_show_reference_cloud=True,
            comparison_show_reference_mesh=False,
            comparison_show_trajectories=True,
            comparison_slam_max_points=30_000,
            comparison_reference_max_points=20_000,
            comparison_target_triangles=10_000,
            rerun_validation_max_keyed_clouds=7,
            rerun_validation_max_render_points=8_000,
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
    assert reloaded.artifacts.comparison_show_slam_cloud is False
    assert reloaded.artifacts.comparison_show_reference_cloud is True
    assert reloaded.artifacts.comparison_show_reference_mesh is False
    assert reloaded.artifacts.comparison_show_trajectories is True
    assert reloaded.artifacts.comparison_slam_max_points == 30_000
    assert reloaded.artifacts.comparison_reference_max_points == 20_000
    assert reloaded.artifacts.comparison_target_triangles == 10_000
    assert reloaded.artifacts.rerun_validation_max_keyed_clouds == 7
    assert reloaded.artifacts.rerun_validation_max_render_points == 8_000


def test_record3d_dataset_state_round_trips_separately_from_live_state() -> None:
    state = AppState(
        record3d_dataset=Record3DDatasetPageState(
            selected_sequence_ids=[1, 3],
            overwrite_existing=True,
            explorer_sequence_id="2026-06-03--18-26-32",
            preview_sequence_id="2026-06-03--18-29-08",
            preview_pose_source=Record3DDatasetPoseSource.ARKIT,
            preview_include_depth=False,
            preview_is_running=True,
        )
    )
    state.record3d.transport = Record3DTransportId.WIFI
    state.record3d.wifi_device_address = "record3d.local"
    state.record3d.is_running = True

    reloaded = AppState.model_validate(state.model_dump(mode="json"))

    assert reloaded.record3d.transport is Record3DTransportId.WIFI
    assert reloaded.record3d.wifi_device_address == "record3d.local"
    assert reloaded.record3d.is_running is True
    assert reloaded.record3d_dataset.selected_sequence_ids == [1, 3]
    assert reloaded.record3d_dataset.overwrite_existing is True
    assert reloaded.record3d_dataset.explorer_sequence_id == "2026-06-03--18-26-32"
    assert reloaded.record3d_dataset.preview_sequence_id == "2026-06-03--18-29-08"
    assert reloaded.record3d_dataset.preview_pose_source is Record3DDatasetPoseSource.ARKIT
    assert reloaded.record3d_dataset.preview_include_depth is False
    assert reloaded.record3d_dataset.preview_is_running is True


def test_advio_dataset_explorer_state_uses_normalized_sequence_slug() -> None:
    state = AppState(
        advio=AdvioPageState(
            selected_sequence_ids=[21],
            overwrite_existing=True,
            explorer_sequence_id="advio-21",
            preview_sequence_id=21,
        )
    )

    reloaded = AppState.model_validate(state.model_dump(mode="json"))

    assert reloaded.advio.selected_sequence_ids == [21]
    assert reloaded.advio.overwrite_existing is True
    assert reloaded.advio.explorer_sequence_id == "advio-21"
    assert reloaded.advio.preview_sequence_id == 21


def test_build_run_config_from_action_derives_backend_kind(tmp_path: Path) -> None:
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
        reconstruction_enabled=False,
        trajectory_eval_enabled=False,
        evaluate_cloud=False,
        connect_live_viewer=False,
        export_viewer_rrd=False,
    )

    run_config, error = build_run_config_from_action(context, action)

    assert error is None
    assert isinstance(run_config, RunConfig)
    assert run_config.stages.slam.backend.kind == "vista"
    assert run_config.stages.slam.backend.kind == MethodId.VISTA.value


def test_build_run_config_from_action_coerces_mast3r_sparse_output(tmp_path: Path) -> None:
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
        experiment_name="mast3r-app",
        source_kind=PipelineSourceId.ADVIO,
        advio_sequence_id=1,
        mode=PipelineMode.OFFLINE,
        method=MethodId.MAST3R,
        emit_dense_points=True,
        emit_sparse_points=True,
        reconstruction_enabled=False,
        trajectory_eval_enabled=False,
        evaluate_cloud=False,
        connect_live_viewer=False,
        export_viewer_rrd=False,
    )

    run_config, error = build_run_config_from_action(context, action)

    assert error is None
    assert isinstance(run_config, RunConfig)
    assert run_config.stages.slam.outputs.emit_sparse_points is False
    plan = run_config.compile_plan(context.path_config, fail_on_unavailable=True)
    slam_stage = next(stage for stage in plan.stages if stage.key is StageKey.SLAM)
    assert slam_stage.available is True
    assert [path.name for path in slam_stage.outputs] == ["trajectory.tum", "dense_points.ply"]


def test_build_run_config_from_action_accepts_stringified_vista_paths(tmp_path: Path) -> None:
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
        connect_live_viewer=False,
        export_viewer_rrd=False,
    )

    run_config, error = build_run_config_from_action(context, action)

    assert error is None
    assert isinstance(run_config, RunConfig)
    assert run_config.stages.source.backend.dataset_serving == AdvioServingConfig(
        pose_source="ground_truth",
        pose_frame_mode="fixedpoint_common_start_local",
    )
    assert run_config.stages.slam.backend.vista_slam_dir == Path("external/vista-slam")


def test_build_run_config_from_action_round_trips_console_stage_visualization_and_backend_fields(
    tmp_path: Path,
) -> None:
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
        experiment_name="console",
        source_kind=PipelineSourceId.ADVIO,
        advio_sequence_id=1,
        mode=PipelineMode.STREAMING,
        method=MethodId.VISTA,
        slam_max_frames=20,
        slam_backend_spec=build_backend_spec(
            method=MethodId.VISTA,
            max_frames=20,
            overrides={"device": "cpu", "flow_thres": -1.0, "random_seed": 99},
        ),
        emit_dense_points=True,
        emit_sparse_points=False,
        ground_alignment_enabled=True,
        reconstruction_enabled=True,
        trajectory_eval_enabled=True,
        evaluate_cloud=False,
        connect_live_viewer=True,
        export_viewer_rrd=True,
        grpc_url="rerun+http://127.0.0.1:9876/proxy",
        viewer_blueprint_path=Path(".configs/visualization/vista_blueprint.rbl"),
        preserve_native_rerun=False,
        frusta_history_window_offline=12,
        show_tracking_trajectory=False,
        log_source_rgb=True,
        log_diagnostic_preview=True,
        log_camera_image_rgb=True,
    )

    run_config, error = build_run_config_from_action(context, action)

    assert error is None
    assert isinstance(run_config, RunConfig)
    assert run_config.stages.align_ground.enabled is True
    assert run_config.stages.reconstruction.enabled is True
    assert run_config.stages.evaluate_trajectory.enabled is True
    assert run_config.stages.slam.outputs.emit_sparse_points is False
    assert run_config.stages.slam.backend.max_frames == 20
    assert run_config.stages.slam.backend.device == "cpu"
    assert run_config.stages.slam.backend.flow_thres == -1.0
    assert run_config.stages.slam.backend.random_seed == 99
    assert run_config.visualization.connect_live_viewer is True
    assert run_config.visualization.export_viewer_rrd is True
    assert run_config.visualization.viewer_blueprint_path == Path(".configs/visualization/vista_blueprint.rbl")
    assert run_config.visualization.preserve_native_rerun is False
    assert run_config.visualization.frusta_history_window_offline == 12
    assert run_config.visualization.show_tracking_trajectory is False
    assert run_config.visualization.log_source_rgb is True
    assert run_config.visualization.log_diagnostic_preview is True
    assert run_config.visualization.log_camera_image_rgb is True


def test_build_run_config_from_action_uses_record3d_frame_timeout(tmp_path: Path) -> None:
    context = type(
        "Context",
        (),
        {
            "path_config": PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts"),
            "advio_service": object(),
        },
    )()
    action = PipelinePageAction(
        config_path=Path(".configs/pipelines/demo.toml"),
        experiment_name="record3d-console",
        source_kind=PipelineSourceId.RECORD3D,
        mode=PipelineMode.STREAMING,
        method=MethodId.VISTA,
        record3d_transport=Record3DTransportId.WIFI,
        record3d_wifi_device_address="192.168.1.22",
        record3d_frame_timeout_seconds=2.5,
    )

    run_config, error = build_run_config_from_action(context, action)

    assert error is None
    assert isinstance(run_config, RunConfig)
    assert run_config.stages.source.backend.source_id == "record3d"
    assert run_config.stages.source.backend.transport.value == Record3DTransportId.WIFI.value
    assert run_config.stages.source.backend.device_address == "192.168.1.22"
    assert run_config.stages.source.backend.frame_timeout_seconds == 2.5


def test_sync_pipeline_template_preserves_typed_vista_backend_spec(tmp_path: Path, monkeypatch) -> None:
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
    run_config = build_run_config(
        experiment_name="vista-page",
        mode=PipelineMode.OFFLINE,
        output_dir=context.path_config.artifacts_dir,
        source_backend=AdvioSourceConfig(
            sequence_id="advio-01",
            target_fps=15.0,
            dataset_serving={
                "pose_source": "ground_truth",
                "pose_frame_mode": "provider_world",
            },
        ),
        method=MethodId.VISTA,
        backend_overrides={
            "vista_slam_dir": Path("external/vista-slam"),
            "checkpoint_path": Path("external/vista-slam/pretrains/frontend_sta_weights.pth"),
            "vocab_path": Path("external/vista-slam/pretrains/ORBvoc.txt"),
        },
    )
    monkeypatch.setattr(
        pipeline_controls,
        "resolve_normalized_advio_sequence_id",
        lambda **_kwargs: (1, None),
    )

    sync_pipeline_page_state_from_template(
        context=context,
        config_path=Path(".configs/pipelines/vista-full.toml"),
        run_config=run_config,
    )

    backend_spec = context.state.pipeline.slam_backend_spec
    assert backend_spec is not None
    assert backend_spec.kind == "vista"
    assert backend_spec.vista_slam_dir == Path("external/vista-slam")
    assert context.state.pipeline.pose_source.value == "ground_truth"
    assert context.state.pipeline.pose_frame_mode.value == "fixedpoint_common_start_local"
    assert context.state.pipeline.dataset_target_fps == 15.0
    assert context.state.pipeline.dataset_frame_stride == 1
    action = action_from_page_state(context.state.pipeline, Path(".configs/pipelines/vista-full.toml"))
    rebuilt_run_config, error = build_run_config_from_action(context, action)

    assert error is None
    assert isinstance(rebuilt_run_config, RunConfig)
    assert rebuilt_run_config.stages.slam.backend.vista_slam_dir == Path("external/vista-slam")
    assert rebuilt_run_config.stages.source.backend.target_fps == 15.0


def test_cloud_evaluation_stage_is_supported_by_request_preview(tmp_path: Path) -> None:
    path_config = PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts")
    run_config = build_run_config(
        experiment_name="placeholder",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source_backend=AdvioSourceConfig(
            sequence_id="advio-01",
            dataset_serving={"pose_source": "ground_truth", "pose_frame_mode": "fixedpoint_common_start_local"},
        ),
        method=MethodId.VISTA,
        evaluate_cloud=True,
    )
    plan = run_config.compile_plan(path_config)

    error = request_support_error(request=run_config, plan=plan, path_config=path_config)

    assert error is None


def test_pipeline_snapshot_render_model_shapes_streaming_payloads(tmp_path: Path) -> None:
    plan = RunPlan(
        run_id="streaming-demo",
        mode=PipelineMode.STREAMING,
        artifact_root=tmp_path / "streaming-demo",
        source=PlannedSource(source_id="advio", sequence_id="advio-01"),
    )
    frame_ref = TransientPayloadRef(handle_id="frame-ref", payload_kind="image", shape=(2, 2, 3), dtype="uint8")
    preview_ref = TransientPayloadRef(handle_id="preview-ref", payload_kind="image", shape=(2, 2, 3), dtype="uint8")
    snapshot = RunSnapshot(
        run_id="streaming-demo",
        state=RunState.RUNNING,
        plan=plan,
        stage_runtime_status={
            StageKey.SLAM: StageRuntimeStatus(
                stage_key=StageKey.SLAM,
                lifecycle_state=StageStatus.RUNNING,
                processed_items=4,
                fps=20.0,
                throughput=5.0,
                updated_at_ns=44,
            )
        },
        live_refs={
            StageKey.SLAM: {
                "model_rgb:image": frame_ref,
                "model_preview:image": preview_ref,
            }
        },
        stage_outcomes={
            StageKey.SLAM: StageOutcome(
                stage_key=StageKey.SLAM,
                status=StageStatus.COMPLETED,
                config_hash="cfg",
                input_fingerprint="inp",
            )
        },
    )

    class FakeRunService:
        def read_payload(self, ref: TransientPayloadRef | None):
            if ref is None:
                return None
            return {
                "frame-ref": np.ones((2, 2, 3), dtype=np.uint8),
                "preview-ref": np.zeros((2, 2, 3), dtype=np.uint8),
            }[ref.handle_id]

        def tail_events(self, *, limit: int = 200, after_event_id: str | None = None):
            del limit, after_event_id
            return [
                RunStarted(event_id="1", run_id="streaming-demo", ts_ns=1),
            ]

    model = build_pipeline_snapshot_render_model(
        snapshot, FakeRunService(), method=MethodId.VISTA, show_evo_preview=False
    )

    assert model["caption"] is not None
    assert "ViSTA-SLAM" in model["caption"]
    assert model["streaming"] is not None
    assert model["streaming"]["frame_image"] is not None
    assert model["streaming"]["preview_image"] is not None
    assert model["streaming"]["packet_metadata"] == {
        "stage": "slam",
        "processed_items": 4,
        "fps": 20.0,
        "throughput": 5.0,
        "updated_at_ns": 44,
    }
    assert model["streaming"]["backend_notice"] is None
    assert model["stage_outcome_rows"][0]["Stage"] == "slam"
    assert model["recent_events"][-1]["kind"] == "run.started"


def test_pipeline_snapshot_render_model_builds_stage_status_rows(tmp_path: Path) -> None:
    plan = RunPlan(
        run_id="status-demo",
        mode=PipelineMode.STREAMING,
        artifact_root=tmp_path / "status-demo",
        source=PlannedSource(source_id="advio", sequence_id="advio-01"),
        stages=[
            RunPlanStage(key=StageKey.SOURCE),
            RunPlanStage(key=StageKey.SLAM),
            RunPlanStage(
                key=StageKey.CLOUD_EVALUATION,
                available=False,
                availability_reason="Dense-cloud evaluation is planned but no runtime is registered yet.",
            ),
        ],
    )
    snapshot = RunSnapshot(
        run_id="status-demo",
        state=RunState.RUNNING,
        plan=plan,
        stage_runtime_status={
            StageKey.SOURCE: StageRuntimeStatus(
                stage_key=StageKey.SOURCE,
                lifecycle_state=StageStatus.RUNNING,
                progress_message="received 4 frames",
                completed_steps=4,
                progress_unit="frames",
                processed_items=4,
                fps=30.0,
                throughput=29.5,
                throughput_unit="frames/s",
                latency_ms=4.2,
                queue_depth=1,
                backlog_count=2,
                submitted_count=4,
                completed_count=3,
                in_flight_count=1,
                updated_at_ns=1_000_000_000,
            )
        },
        stage_outcomes={
            StageKey.SLAM: StageOutcome(
                stage_key=StageKey.SLAM,
                status=StageStatus.COMPLETED,
                config_hash="cfg",
                input_fingerprint="inp",
            )
        },
    )

    class FakeRunService:
        def read_payload(self, ref: TransientPayloadRef | None):
            del ref
            return None

        def tail_events(self, *, limit: int = 200, after_event_id: str | None = None):
            del limit, after_event_id
            return []

    model = build_pipeline_snapshot_render_model(
        snapshot,
        FakeRunService(),
        method=MethodId.VISTA,
        show_evo_preview=False,
        now_ns=2_000_000_000,
    )
    rows = {row["Id"]: row for row in model["stage_status_rows"]}

    assert rows["source"]["State"] == "running"
    assert rows["source"]["Progress"] == "4 frames"
    assert rows["source"]["FPS"] == "30.00"
    assert rows["source"]["Throughput"] == "29.50 frames/s"
    assert rows["source"]["Latency"] == "4.2 ms"
    assert rows["source"]["Queue"] == "q 1 / back 2"
    assert rows["source"]["Tasks"] == "4 submitted / 3 done / 0 failed / 1 in flight"
    assert rows["source"]["Updated"] == "1 s"
    assert rows["slam"]["State"] == "completed"
    assert rows["evaluate.cloud"]["State"] == "unavailable"
    assert rows["evaluate.cloud"]["Message"] == "Dense-cloud evaluation is planned but no runtime is registered yet."


def test_pipeline_telemetry_history_resets_deduplicates_and_trims() -> None:
    page_state = PipelinePageState(telemetry_max_samples=2)
    first_snapshot = RunSnapshot(
        run_id="run-1",
        stage_runtime_status={
            StageKey.SOURCE: StageRuntimeStatus(
                stage_key=StageKey.SOURCE,
                lifecycle_state=StageStatus.RUNNING,
                processed_items=1,
                fps=10.0,
                updated_at_ns=1,
            ),
            StageKey.SLAM: StageRuntimeStatus(
                stage_key=StageKey.SLAM,
                lifecycle_state=StageStatus.RUNNING,
                processed_items=1,
                fps=5.0,
                updated_at_ns=2,
            ),
        },
    )

    run_id, history, changed = refreshed_pipeline_telemetry_history(page_state, first_snapshot)
    assert run_id == "run-1"
    assert changed is True
    assert [(sample.stage_key, sample.updated_at_ns) for sample in history] == [
        (StageKey.SOURCE, 1),
        (StageKey.SLAM, 2),
    ]

    page_state.telemetry_history_run_id = run_id
    page_state.telemetry_history = history
    _, deduped_history, changed = refreshed_pipeline_telemetry_history(page_state, first_snapshot)
    assert changed is False
    assert deduped_history == history

    second_snapshot = RunSnapshot(
        run_id="run-1",
        stage_runtime_status={
            StageKey.SOURCE: StageRuntimeStatus(
                stage_key=StageKey.SOURCE,
                lifecycle_state=StageStatus.RUNNING,
                processed_items=2,
                fps=11.0,
                updated_at_ns=3,
            )
        },
    )
    _, trimmed_history, changed = refreshed_pipeline_telemetry_history(page_state, second_snapshot)
    assert changed is True
    assert [(sample.stage_key, sample.updated_at_ns) for sample in trimmed_history] == [
        (StageKey.SLAM, 2),
        (StageKey.SOURCE, 3),
    ]

    page_state.telemetry_history_run_id = "run-1"
    page_state.telemetry_history = trimmed_history
    new_run_snapshot = RunSnapshot(
        run_id="run-2",
        stage_runtime_status={
            StageKey.SOURCE: StageRuntimeStatus(stage_key=StageKey.SOURCE, updated_at_ns=4),
        },
    )
    run_id, reset_history, changed = refreshed_pipeline_telemetry_history(page_state, new_run_snapshot)
    assert run_id == "run-2"
    assert changed is True
    assert [(sample.stage_key, sample.updated_at_ns) for sample in reset_history] == [(StageKey.SOURCE, 4)]


def test_pipeline_snapshot_render_model_builds_rolling_telemetry_chart(tmp_path: Path) -> None:
    plan = RunPlan(
        run_id="telemetry-demo",
        mode=PipelineMode.STREAMING,
        artifact_root=tmp_path / "telemetry-demo",
        source=PlannedSource(source_id="advio", sequence_id="advio-01"),
        stages=[RunPlanStage(key=StageKey.SOURCE), RunPlanStage(key=StageKey.SLAM)],
    )
    snapshot = RunSnapshot(run_id="telemetry-demo", state=RunState.RUNNING, plan=plan)
    history = [
        StageRuntimeStatus(stage_key=StageKey.SOURCE, updated_at_ns=1, fps=10.0),
        StageRuntimeStatus(stage_key=StageKey.SLAM, updated_at_ns=2, fps=5.0),
        StageRuntimeStatus(stage_key=StageKey.SOURCE, updated_at_ns=3, fps=12.0),
    ]

    class FakeRunService:
        def read_payload(self, ref: TransientPayloadRef | None):
            del ref
            return None

        def tail_events(self, *, limit: int = 200, after_event_id: str | None = None):
            del limit, after_event_id
            return []

    model = build_pipeline_snapshot_render_model(
        snapshot,
        FakeRunService(),
        method=MethodId.VISTA,
        show_evo_preview=False,
        telemetry_history=history,
        telemetry_visible=True,
        telemetry_view_mode=PipelineTelemetryViewMode.ROLLING,
        telemetry_selected_stage_key=StageKey.SOURCE,
        telemetry_selected_metric=PipelineTelemetryMetricId.FPS,
    )

    assert model["telemetry_chart"] is not None
    assert model["telemetry_chart"]["metric_label"] == "FPS"
    assert [row["value"] for row in model["telemetry_chart"]["rows"]] == [10.0, 12.0]


def test_pipeline_viewer_link_model_disabled_without_live_viewer() -> None:
    model = build_pipeline_viewer_link_model(
        connect_live_viewer=False,
        grpc_url="rerun+http://127.0.0.1:9876/proxy",
    )

    assert model["enabled"] is False
    assert model["web_url"] is None
    assert model["grpc_url"] == "rerun+http://127.0.0.1:9876/proxy"
    assert "disabled" in model["status_message"]


def test_pipeline_viewer_link_model_encodes_default_grpc_url() -> None:
    model = build_pipeline_viewer_link_model(
        connect_live_viewer=True,
        grpc_url="rerun+http://127.0.0.1:9876/proxy",
    )

    assert model["enabled"] is True
    assert model["web_url"] == "http://127.0.0.1:9090/?url=rerun%2Bhttp%3A%2F%2F127.0.0.1%3A9876%2Fproxy"


def test_pipeline_viewer_link_model_encodes_custom_grpc_url() -> None:
    model = build_pipeline_viewer_link_model(
        connect_live_viewer=True,
        grpc_url="rerun+http://localhost:9877/proxy?recording=run 1",
    )

    assert model["enabled"] is True
    assert (
        model["web_url"]
        == "http://127.0.0.1:9090/?url=rerun%2Bhttp%3A%2F%2Flocalhost%3A9877%2Fproxy%3Frecording%3Drun%201"
    )


def test_pipeline_viewer_link_model_requires_non_empty_grpc_url() -> None:
    model = build_pipeline_viewer_link_model(connect_live_viewer=True, grpc_url="  ")

    assert model["enabled"] is False
    assert model["web_url"] is None
    assert model["grpc_url"] == ""
    assert "no gRPC URL" in model["status_message"]


def test_pipeline_snapshot_render_model_prefers_target_live_refs(tmp_path: Path) -> None:
    plan = RunPlan(
        run_id="streaming-demo",
        mode=PipelineMode.STREAMING,
        artifact_root=tmp_path / "streaming-demo",
        source=PlannedSource(source_id="advio", sequence_id="advio-01"),
    )
    frame_ref = TransientPayloadRef(handle_id="frame-ref", payload_kind="image", shape=(2, 2, 3), dtype="uint8")
    preview_ref = TransientPayloadRef(handle_id="preview-ref", payload_kind="image", shape=(2, 2, 3), dtype="uint8")
    snapshot = RunSnapshot(
        run_id="streaming-demo",
        state=RunState.RUNNING,
        plan=plan,
        stage_runtime_status={
            StageKey.SLAM: StageRuntimeStatus(
                stage_key=StageKey.SLAM,
                lifecycle_state=StageStatus.RUNNING,
                processed_items=3,
                fps=12.5,
                throughput=2.5,
            )
        },
        live_refs={
            StageKey.SLAM: {
                "model_rgb:image": frame_ref,
                "model_preview:image": preview_ref,
            }
        },
    )

    class FakeRunService:
        def read_payload(self, ref: TransientPayloadRef | None):
            if ref is None:
                return None
            return {
                "frame-ref": np.ones((2, 2, 3), dtype=np.uint8),
                "preview-ref": np.zeros((2, 2, 3), dtype=np.uint8),
            }[ref.handle_id]

        def tail_events(self, *, limit: int = 200, after_event_id: str | None = None):
            del limit, after_event_id
            return []

    model = build_pipeline_snapshot_render_model(
        snapshot, FakeRunService(), method=MethodId.VISTA, show_evo_preview=False
    )

    assert model["streaming"] is not None
    assert model["streaming"]["frame_image"] is not None
    assert model["streaming"]["preview_image"] is not None
    assert model["streaming"]["preview_status_message"] == "Current keyframe artifact."
    assert ("Received Frames", "3") in model["metrics"]
    assert ("Packet FPS", "12.50 fps") in model["metrics"]
    assert ("Keyframe FPS", "2.50 fps") in model["metrics"]


def test_pipeline_snapshot_render_model_shapes_vista_empty_states(tmp_path: Path) -> None:
    plan = RunPlan(
        run_id="streaming-demo",
        mode=PipelineMode.STREAMING,
        artifact_root=tmp_path / "streaming-demo",
        source=PlannedSource(source_id="advio", sequence_id="advio-01"),
    )
    snapshot = RunSnapshot(run_id="streaming-demo", state=RunState.RUNNING, plan=plan)

    class FakeRunService:
        def read_payload(self, ref: TransientPayloadRef | None):
            del ref
            return None

        def tail_events(self, *, limit: int = 200, after_event_id: str | None = None):
            del limit, after_event_id
            return []

    model = build_pipeline_snapshot_render_model(
        snapshot, FakeRunService(), method=MethodId.VISTA, show_evo_preview=False
    )

    assert model["streaming"] is not None
    assert "ViSTA-SLAM has not produced" in model["streaming"]["preview_empty_message"]
    assert "ViSTA-SLAM has not accepted" in model["streaming"]["trajectory_empty_message"]


def test_pipeline_snapshot_render_model_links_persisted_trajectory_evaluation_artifact(tmp_path: Path) -> None:
    plan = RunPlan(
        run_id="streaming-demo",
        mode=PipelineMode.STREAMING,
        artifact_root=tmp_path / "streaming-demo",
        source=PlannedSource(source_id="advio", sequence_id="advio-01"),
    )
    snapshot = RunSnapshot(run_id="streaming-demo", state=RunState.RUNNING, plan=plan)

    class FakeRunService:
        def read_payload(self, ref: TransientPayloadRef | None):
            del ref
            return None

        def tail_events(self, *, limit: int = 200, after_event_id: str | None = None):
            del limit, after_event_id
            return []

    snapshot.artifacts["trajectory_evaluation_manifest"] = ArtifactRef(
        path=plan.artifact_root / "evaluation" / "trajectory" / "manifest.json",
        kind="json",
        fingerprint="manifest",
    )

    model = build_pipeline_snapshot_render_model(
        snapshot, FakeRunService(), method=MethodId.VISTA, show_evo_preview=False
    )

    assert model["streaming"] is not None
    assert (
        model["streaming"]["trajectory_evaluation_artifact"]
        == (plan.artifact_root / "evaluation" / "trajectory" / "manifest.json").as_posix()
    )


def test_trajectory_evaluation_query_loads_pipeline_manifest(tmp_path: Path) -> None:
    artifact_root = tmp_path / "run"
    manifest_path = artifact_root / "evaluation" / "trajectory" / "manifest.json"
    metrics_long_path = artifact_root / "evaluation" / "trajectory" / "metrics_long.csv"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        TrajectoryEvaluationManifest(
            artifact_root=artifact_root,
            sequence_id="test-sequence",
            run_id="run",
        ).model_dump_json(),
        encoding="utf-8",
    )
    metrics_long_path.write_text(
        "\n".join(
            [
                "run_id,sequence_id,reference_source,estimate_source,metric_family,pose_relation,statistic,value,unit,matched_pairs,delta,delta_unit,error_series_path",
                "run,test-sequence,ground_truth,vslam,ape,translation part,rmse,0.05,m,4,,,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    service = TrajectoryEvaluationQueryService(PathConfig(root=tmp_path, artifacts_dir=tmp_path))
    loaded = service.load_run_evaluation(
        DiscoveredRun(
            artifact_root=artifact_root,
            estimate_path=artifact_root / "slam" / "trajectory.tum",
            label="test",
        )
    )

    assert loaded.manifest is not None
    assert len(loaded.metric_rows) == 1
    assert loaded.metric_rows[0].statistic == "rmse"
    assert loaded.metric_rows[0].value == 0.05
    assert loaded.metric_rows[0].pose_relation is metrics.PoseRelation.translation_part


def test_trajectory_evaluation_query_discovers_runs_by_sequence_manifest(tmp_path: Path) -> None:
    artifact_root = tmp_path / "vista-tum-cabinet-full" / "vista"
    _write_discoverable_run(
        artifact_root,
        SequenceManifest(sequence_id="freiburg3_large_cabinet", dataset_id=DatasetId.TUM_RGBD),
    )
    service = TrajectoryEvaluationQueryService(PathConfig(root=tmp_path, artifacts_dir=tmp_path))

    runs = service.discover_runs("freiburg3_large_cabinet", dataset=DatasetId.TUM_RGBD)

    assert len(runs) == 1
    assert runs[0].artifact_root == artifact_root
    assert runs[0].estimate_path == artifact_root / "slam" / "trajectory.tum"
    assert runs[0].method == MethodId.VISTA.value


def test_trajectory_evaluation_query_excludes_mismatched_dataset(tmp_path: Path) -> None:
    artifact_root = tmp_path / "vista-tum-cabinet-full" / "vista"
    _write_discoverable_run(
        artifact_root,
        SequenceManifest(sequence_id="freiburg3_large_cabinet", dataset_id=DatasetId.ADVIO),
    )
    service = TrajectoryEvaluationQueryService(PathConfig(root=tmp_path, artifacts_dir=tmp_path))

    assert service.discover_runs("freiburg3_large_cabinet", dataset=DatasetId.TUM_RGBD) == []


def test_trajectory_evaluation_query_excludes_runs_without_sequence_manifest(tmp_path: Path) -> None:
    artifact_root = tmp_path / "vista-tum-cabinet-full" / "vista"
    (artifact_root / "slam").mkdir(parents=True)
    (artifact_root / "slam" / "trajectory.tum").write_text("", encoding="utf-8")
    service = TrajectoryEvaluationQueryService(PathConfig(root=tmp_path, artifacts_dir=tmp_path))

    assert service.discover_runs("freiburg3_large_cabinet", dataset=DatasetId.TUM_RGBD) == []


def test_trajectory_evaluation_query_reports_missing_canonical_manifest(tmp_path: Path) -> None:
    artifact_root = tmp_path / "vista-tum-cabinet-full" / "vista"
    _write_discoverable_run(
        artifact_root,
        SequenceManifest(sequence_id="freiburg3_large_cabinet", dataset_id=DatasetId.TUM_RGBD),
    )
    service = TrajectoryEvaluationQueryService(PathConfig(root=tmp_path, artifacts_dir=tmp_path))
    runs = service.discover_runs("freiburg3_large_cabinet", dataset=DatasetId.TUM_RGBD)

    loaded = service.load_run_evaluation(runs[0])

    assert loaded.manifest is None
    assert loaded.metric_rows == []
    assert loaded.load_error is None


def test_trajectory_evaluation_query_ignores_legacy_metrics_json(tmp_path: Path) -> None:
    artifact_root = tmp_path / "vista-tum-cabinet-full" / "vista"
    _write_discoverable_run(
        artifact_root,
        SequenceManifest(sequence_id="freiburg3_large_cabinet", dataset_id=DatasetId.TUM_RGBD),
    )
    legacy_path = artifact_root / "evaluation" / "trajectory_metrics.json"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text('{"rmse": 0.1}', encoding="utf-8")
    service = TrajectoryEvaluationQueryService(PathConfig(root=tmp_path, artifacts_dir=tmp_path))
    runs = service.discover_runs("freiburg3_large_cabinet", dataset=DatasetId.TUM_RGBD)

    loaded = service.load_run_evaluation(runs[0])

    assert loaded.manifest is None
    assert loaded.metric_rows == []


def _write_discoverable_run(artifact_root: Path, sequence_manifest: SequenceManifest) -> None:
    trajectory_path = artifact_root / "slam" / "trajectory.tum"
    manifest_path = artifact_root / "input" / "sequence_manifest.json"
    trajectory_path.parent.mkdir(parents=True)
    manifest_path.parent.mkdir(parents=True)
    trajectory_path.write_text("", encoding="utf-8")
    manifest_path.write_text(sequence_manifest.model_dump_json(), encoding="utf-8")
