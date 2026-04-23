"""Focused app/controller tests for the refactored pipeline surface."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from prml_vslam.app.bootstrap import _PAGE_SPECS
from prml_vslam.app.models import AppPageId, AppState, ArtifactInspectorPageState, PipelineSourceId
from prml_vslam.app.pages.graphify import (
    GraphifyFilterOptions,
    GraphifySourceScope,
    GraphifyViewerFilter,
    filter_graphify_graph,
    load_graphify_graph,
    load_graphify_summary,
    render_filtered_graph_html,
    resolve_graphify_artifacts,
)
from prml_vslam.app.pipeline_controller import (
    PipelinePageAction,
    action_from_page_state,
    build_pipeline_snapshot_render_model,
    build_run_config_from_action,
    request_support_error,
    sync_pipeline_page_state_from_template,
)
from prml_vslam.datasets.advio import AdvioServingConfig
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.config import RunConfig, build_backend_spec
from prml_vslam.pipeline.contracts.events import RunStarted, StageOutcome
from prml_vslam.pipeline.contracts.plan import PlannedSource, RunPlan
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.request import DatasetSourceSpec, RunRequest, SlamStageConfig
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageRuntimeStatus
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.utils import PathConfig

from .pipeline_legacy import run_config_from_request


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


def test_graphify_page_is_registered() -> None:
    assert any(
        page_id is AppPageId.GRAPHIFY and page_module == "graphify" for page_id, _, page_module, _ in _PAGE_SPECS
    )


def test_graphify_artifact_summary_loads_generated_counts(tmp_path: Path) -> None:
    graphify_root = tmp_path / "graphify-out"
    graphify_root.mkdir()
    (graphify_root / "GRAPH_REPORT.md").write_text(
        "\n".join(
            [
                "# Graph Report - demo  (2026-04-22)",
                "",
                "## Summary",
                "- 2 nodes · 1 edges · 1 communities detected",
            ]
        ),
        encoding="utf-8",
    )
    (graphify_root / "graph.json").write_text(
        '{"nodes": [{"id": "a"}, {"id": "b"}], "links": [{"source": "a", "target": "b"}]}',
        encoding="utf-8",
    )
    (graphify_root / "graph.html").write_text("<html></html>", encoding="utf-8")

    artifacts = resolve_graphify_artifacts(tmp_path)
    summary = load_graphify_summary(artifacts)

    assert artifacts.all_present is True
    assert summary.report_title == "# Graph Report - demo  (2026-04-22)"
    assert summary.graph_date == "2026-04-22"
    assert summary.nodes == 2
    assert summary.links == 1
    assert summary.communities == 1


def test_graphify_viewer_filters_graph_nodes(tmp_path: Path) -> None:
    graphify_root = tmp_path / "graphify-out"
    graphify_root.mkdir()
    (graphify_root / "graph.json").write_text(
        """{
          "directed": false,
          "multigraph": false,
          "graph": {},
          "nodes": [
            {"id": "pkg", "label": "Package", "source_file": "src/prml_vslam/app/bootstrap.py", "file_type": "code", "community": 0},
            {"id": "pkg_reason", "label": "Package rationale", "source_file": "src/prml_vslam/app/bootstrap.py", "file_type": "rationale", "community": 0},
            {"id": "test", "label": "Test", "source_file": "tests/test_app.py", "file_type": "code", "community": 1},
            {"id": "script", "label": "Script", "source_file": "scripts/tool.py", "file_type": "code", "community": 2}
          ],
          "links": [
            {"source": "pkg", "target": "pkg_reason", "relation": "rationale_for", "confidence": "EXTRACTED"},
            {"source": "pkg", "target": "test", "relation": "tested_by", "confidence": "INFERRED"}
          ]
        }""",
        encoding="utf-8",
    )
    graph = load_graphify_graph(resolve_graphify_artifacts(tmp_path))

    package_graph = filter_graphify_graph(
        graph,
        GraphifyFilterOptions(
            source_scope=GraphifySourceScope.PRML_VSLAM,
            include_rationale_nodes=False,
            minimum_degree=1,
        ),
    )
    no_tests_graph = filter_graphify_graph(
        graph,
        GraphifyFilterOptions(source_scope=GraphifySourceScope.EXCLUDE_TESTS, minimum_degree=1),
    )

    assert set(package_graph.nodes) == {"pkg"}
    assert set(no_tests_graph.nodes) == {"pkg", "pkg_reason"}


def test_graphify_filter_options_resolve_multiselect_chips() -> None:
    package_options = GraphifyFilterOptions.from_selected_filters(
        [GraphifyViewerFilter.ONLY_PRML_VSLAM, GraphifyViewerFilter.CODE_ONLY],
        minimum_degree=2,
    )
    tests_options = GraphifyFilterOptions.from_selected_filters(
        [GraphifyViewerFilter.EXCLUDE_TESTS, GraphifyViewerFilter.ONLY_TESTS],
    )

    assert package_options.source_scope is GraphifySourceScope.PRML_VSLAM
    assert package_options.include_rationale_nodes is False
    assert package_options.minimum_degree == 2
    assert tests_options.source_scope is GraphifySourceScope.TESTS_ONLY


def test_filtered_graph_html_uses_graphify_exporter(tmp_path: Path) -> None:
    graphify_root = tmp_path / "graphify-out"
    graphify_root.mkdir()
    (graphify_root / "graph.json").write_text(
        """{
          "directed": false,
          "multigraph": false,
          "graph": {},
          "nodes": [
            {"id": "a", "label": "A", "source_file": "src/prml_vslam/a.py", "file_type": "code", "community": 0},
            {"id": "b", "label": "B", "source_file": "src/prml_vslam/b.py", "file_type": "code", "community": 0}
          ],
          "links": [
            {"source": "a", "target": "b", "relation": "uses", "confidence": "EXTRACTED"}
          ]
        }""",
        encoding="utf-8",
    )
    graph = load_graphify_graph(resolve_graphify_artifacts(tmp_path))

    html = render_filtered_graph_html(graph)

    assert "vis-network" in html
    assert "A" in html
    assert "B" in html


def test_graphify_artifacts_report_missing_standard_files(tmp_path: Path) -> None:
    artifacts = resolve_graphify_artifacts(tmp_path)

    assert artifacts.all_present is False
    assert artifacts.report == tmp_path / "graphify-out" / "GRAPH_REPORT.md"


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
        reference_enabled=False,
        trajectory_eval_enabled=False,
        evaluate_cloud=False,
        evaluate_efficiency=False,
        connect_live_viewer=False,
        export_viewer_rrd=False,
    )

    run_config, error = build_run_config_from_action(context, action)

    assert error is None
    assert isinstance(run_config, RunConfig)
    assert run_config.stages.slam.backend.kind == "vista"
    assert run_config.stages.slam.backend.kind == MethodId.VISTA.value


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
        respect_video_rotation=True,
        connect_live_viewer=False,
        export_viewer_rrd=False,
    )

    run_config, error = build_run_config_from_action(context, action)

    assert error is None
    assert isinstance(run_config, RunConfig)
    assert run_config.stages.source.backend.dataset_serving == AdvioServingConfig(
        pose_source="ground_truth",
        pose_frame_mode="provider_world",
    )
    assert run_config.stages.source.backend.respect_video_rotation is True
    assert run_config.stages.slam.backend.vista_slam_dir == Path("external/vista-slam")


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
        run_config=run_config_from_request(request),
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
    rebuilt_run_config, error = build_run_config_from_action(context, action)

    assert error is None
    assert isinstance(rebuilt_run_config, RunConfig)
    assert rebuilt_run_config.stages.slam.backend.vista_slam_dir == Path("external/vista-slam")
    assert rebuilt_run_config.stages.source.backend.respect_video_rotation is True


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
    run_config = run_config_from_request(request)
    plan = run_config.compile_plan(path_config)

    error = request_support_error(request=run_config, plan=plan, previewable_statuses=[])

    assert error is not None
    assert "placeholder" in error


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

    assert model.caption is not None
    assert "ViSTA-SLAM" in model.caption
    assert model.streaming is not None
    assert model.streaming.frame_image is not None
    assert model.streaming.preview_image is not None
    assert model.streaming.packet_metadata == {
        "stage": "slam",
        "processed_items": 4,
        "fps": 20.0,
        "throughput": 5.0,
        "updated_at_ns": 44,
    }
    assert model.streaming.backend_notice is None
    assert model.stage_outcome_rows[0]["Stage"] == "slam"
    assert model.recent_events[-1]["kind"] == "run.started"


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

    assert model.streaming is not None
    assert model.streaming.frame_image is not None
    assert model.streaming.preview_image is not None
    assert model.streaming.preview_status_message == "Current keyframe artifact."
    assert ("Received Frames", "3") in model.metrics
    assert ("Packet FPS", "12.50 fps") in model.metrics
    assert ("Keyframe FPS", "2.50 fps") in model.metrics


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

    assert model.streaming is not None
    assert "ViSTA-SLAM has not produced" in model.streaming.preview_empty_message
    assert "ViSTA-SLAM has not accepted" in model.streaming.trajectory_empty_message


def test_pipeline_snapshot_render_model_only_resolves_evo_preview_when_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plan = RunPlan(
        run_id="streaming-demo",
        mode=PipelineMode.STREAMING,
        artifact_root=tmp_path / "streaming-demo",
        source=PlannedSource(source_id="advio", sequence_id="advio-01"),
    )
    snapshot = RunSnapshot(run_id="streaming-demo", state=RunState.RUNNING, plan=plan)
    calls = {"count": 0}

    def fake_resolve_evo_preview(_snapshot):
        calls["count"] += 1
        return None, "preview boom"

    class FakeRunService:
        def read_payload(self, ref: TransientPayloadRef | None):
            del ref
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
