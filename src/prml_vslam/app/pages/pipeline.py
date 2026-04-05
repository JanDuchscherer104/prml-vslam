"""Streamlit page describing and exercising the typed pipeline planning surface."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import (
    BenchmarkEvaluationConfig,
    CloudMetrics,
    DenseArtifacts,
    DenseConfig,
    EfficiencyMetrics,
    LiveSourceSpec,
    PipelineMode,
    ReferenceArtifacts,
    ReferenceConfig,
    RunPlan,
    RunRequest,
    RunSummary,
    SequenceManifest,
    StageManifest,
    TrackingArtifacts,
    TrackingConfig,
    TrajectoryMetrics,
    VideoSourceSpec,
)
from prml_vslam.pipeline.contracts import ArtifactRef, RunPlanStageId, StageExecutionStatus
from prml_vslam.utils import PathConfig

from ..camera_display import format_camera_intrinsics_latex
from ..pipeline_controller import (
    PipelineDemoFormData,
    handle_pipeline_demo_action,
    sync_pipeline_demo_state,
)
from ..pipeline_runtime import PipelineDemoSnapshot, PipelineDemoState
from ..plotting import build_live_trajectory_figure
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


@dataclass(slots=True, frozen=True)
class PipelineExample:
    """One static example shown in the pipeline guidance page."""

    title: str
    summary: str
    request: RunRequest
    code: str


@dataclass(slots=True, frozen=True)
class MockRunDossier:
    """One typed mock run used to demonstrate pipeline outputs."""

    request: RunRequest
    plan: RunPlan
    sequence: SequenceManifest
    tracking: TrackingArtifacts
    dense: DenseArtifacts
    reference: ReferenceArtifacts
    trajectory_metrics: TrajectoryMetrics
    cloud_metrics: CloudMetrics
    efficiency_metrics: EfficiencyMetrics
    stage_manifests: list[StageManifest]
    summary: RunSummary


_MOCK_STAGE_STATUS_OVERRIDES = {
    RunPlanStageId.INGEST: StageExecutionStatus.HIT,
    RunPlanStageId.REFERENCE_RECONSTRUCTION: StageExecutionStatus.HIT,
}


def render(context: AppContext) -> None:
    """Render planning guidance plus the interactive minimal pipeline demo."""
    render_page_intro(
        eyebrow="Planning Surface",
        title="Pipeline Planning",
        body=(
            "Review the typed run-planning API, the direct request shape used to compose stages, "
            "and the exact stage rows produced by one benchmark-style request."
        ),
    )
    sync_pipeline_demo_state(context)
    st.info(
        "The upper sections stay descriptive. The runner below executes a minimal ADVIO -> mock tracking pipeline and streams its status back into this page."
    )
    examples = _build_examples(context.path_config)
    mock_run = _build_mock_run(context.path_config)
    with st.container(border=True):
        st.subheader("Example Pipelines")
        for column, example in zip(st.columns(len(examples), gap="large"), examples, strict=True):
            plan = example.request.build(context.path_config)
            with column:
                st.markdown(f"**{example.title}**")
                st.write(example.summary)
                st.caption("Stages")
                st.markdown("\n".join(f"- `{stage.id.value}`" for stage in plan.stages))
    with st.container(border=True):
        st.subheader("Design Pattern")
        st.markdown(
            "\n".join(
                [
                    "- `RunRequest(...)` owns the normalized source, the output root, the tracking config, and the stage toggles.",
                    "- `DenseConfig`, `ReferenceConfig`, and `BenchmarkEvaluationConfig` make enabled stages explicit in one typed payload.",
                    "- `.build(path_config)` materializes a typed `RunPlan` with ordered `RunPlanStage` rows and canonical artifact paths.",
                ]
            )
        )
    with st.container(border=True):
        st.subheader("How To Use It")
        st.code(examples[1].code, language="python")
    with st.container(border=True):
        st.subheader("Request Shape")
        request_tab, config_tab, output_tab = st.tabs(["Direct Request", "Config Serialization", "Output Aliases"])
        with request_tab:
            st.caption("The request stays explicit: stages only exist when their nested config toggles are enabled.")
            st.code(_request_shape_code(), language="python")
        with config_tab:
            st.caption(
                "`RunRequest` inherits `BaseConfig`, so JSON-friendly and TOML-friendly views are already available."
            )
            left, right = st.columns(2, gap="large")
            left.code(_json_dump(mock_run.request.model_dump_jsonable()), language="json")
            right.code(mock_run.request.to_toml(), language="toml")
        with output_tab:
            st.caption(
                "Artifact and metric wrappers keep their public dump keys even though storage shapes are shared."
            )
            left, right = st.columns(2, gap="large")
            left.code(_json_dump(mock_run.dense.model_dump(mode="json")), language="json")
            right.code(_json_dump(mock_run.trajectory_metrics.model_dump(mode="json")), language="json")
    with st.container(border=True):
        st.subheader("Generated Plan")
        st.caption("Rows below come from the benchmark example above and show what the executor would receive.")
        st.dataframe(_stage_rows(examples[1].request.build(context.path_config)), hide_index=True, width="stretch")
    _render_pipeline_demo(context)
    with st.container(border=True):
        st.subheader("Mock Run")
        st.caption(
            "This mock dossier shows what a completed benchmark run could look like after planning and execution."
        )
        overview_tab, outputs_tab, execution_tab = st.tabs(["Overview", "Outputs", "Execution"])
        with overview_tab:
            metrics = st.columns(4, gap="small")
            metrics[0].metric("Run Id", mock_run.plan.run_id)
            metrics[1].metric("Method", mock_run.plan.method.display_name)
            metrics[2].metric("Stages", str(len(mock_run.plan.stages)))
            metrics[3].metric("Artifact Root", mock_run.plan.artifact_root.name)
            st.dataframe(_stage_rows(mock_run.plan), hide_index=True, width="stretch")
        with outputs_tab:
            st.dataframe(_output_rows(mock_run), hide_index=True, width="stretch")
            left, right = st.columns(2, gap="large")
            left.code(_json_dump(mock_run.sequence.model_dump(mode="json")), language="json")
            right.code(_json_dump(mock_run.tracking.model_dump(mode="json")), language="json")
        with execution_tab:
            st.dataframe(_stage_manifest_rows(mock_run.stage_manifests), hide_index=True, width="stretch")
            st.code(_json_dump(mock_run.summary.model_dump(mode="json")), language="json")


def _build_examples(path_config: PathConfig) -> list[PipelineExample]:
    output_dir = path_config.artifacts_dir
    disabled_eval = BenchmarkEvaluationConfig(
        compare_to_arcore=False,
        evaluate_cloud=False,
        evaluate_efficiency=False,
    )
    return [
        PipelineExample(
            title="Tracking Only",
            summary="A narrow offline plan that only normalizes input, runs tracking, and writes a summary.",
            request=RunRequest(
                experiment_name="tracking-only-demo",
                output_dir=output_dir,
                source=VideoSourceSpec(video_path=path_config.captures_dir / "tracking-only.mp4"),
                tracking=TrackingConfig(method=MethodId.VISTA, max_frames=300),
                dense=DenseConfig(enabled=False),
                evaluation=disabled_eval.model_copy(deep=True),
            ),
            code=_tracking_only_code(),
        ),
        PipelineExample(
            title="Benchmark",
            summary="An explicit request that opts into dense export, reference reconstruction, and evaluation.",
            request=RunRequest(
                experiment_name="benchmark-demo",
                output_dir=output_dir,
                source=VideoSourceSpec(video_path=path_config.captures_dir / "lobby.mp4", frame_stride=2),
                tracking=TrackingConfig(method=MethodId.VISTA),
                dense=DenseConfig(enabled=True),
                reference=ReferenceConfig(enabled=True),
                evaluation=BenchmarkEvaluationConfig(
                    compare_to_arcore=True,
                    evaluate_cloud=True,
                    evaluate_efficiency=True,
                ),
            ),
            code=_benchmark_code(),
        ),
        PipelineExample(
            title="Live Capture",
            summary="A streaming plan that captures a live source, tracks it, and keeps optional offline stages disabled.",
            request=RunRequest(
                experiment_name="live-capture-demo",
                mode=PipelineMode.STREAMING,
                output_dir=output_dir,
                source=LiveSourceSpec(source_id="record3d_usb", persist_capture=True),
                tracking=TrackingConfig(method=MethodId.MSTR),
                dense=DenseConfig(enabled=False),
                evaluation=disabled_eval.model_copy(deep=True),
            ),
            code=_live_capture_code(),
        ),
    ]


def _build_mock_run(path_config: PathConfig) -> MockRunDossier:
    request = RunRequest(
        experiment_name="mock-lobby-benchmark",
        output_dir=path_config.artifacts_dir,
        source=VideoSourceSpec(video_path=path_config.captures_dir / "lobby.mp4", frame_stride=2),
        tracking=TrackingConfig(method=MethodId.VISTA),
        dense=DenseConfig(enabled=True),
        reference=ReferenceConfig(enabled=True),
        evaluation=BenchmarkEvaluationConfig(
            compare_to_arcore=True,
            evaluate_cloud=True,
            evaluate_efficiency=True,
        ),
    )
    plan = request.build(path_config)
    run_paths = path_config.plan_run_paths(
        experiment_name=request.experiment_name,
        method_slug=plan.method.artifact_slug,
        output_dir=request.output_dir,
    )
    sequence = SequenceManifest(
        sequence_id="lobby-demo",
        video_path=request.source.video_path if isinstance(request.source, VideoSourceSpec) else None,
        rgb_dir=run_paths.input_frames_dir,
        timestamps_path=run_paths.capture_manifest_path,
        intrinsics_path=run_paths.capture_manifest_path.with_name("camera_intrinsics.json"),
        reference_tum_path=run_paths.reference_cloud_path.with_suffix(".tum"),
        arcore_tum_path=run_paths.arcore_alignment_path.with_suffix(".tum"),
    )
    tracking = TrackingArtifacts(
        trajectory_tum=_artifact(run_paths.trajectory_path, kind="tum", fingerprint="track-trajectory-v1"),
        sparse_points_ply=_artifact(run_paths.sparse_points_path, kind="ply", fingerprint="track-sparse-v1"),
        preview_log_jsonl=_artifact(
            run_paths.artifact_root / "slam" / "preview_log.jsonl", kind="jsonl", fingerprint="preview-log-v1"
        ),
    )
    dense = DenseArtifacts(
        dense_points_ply=_artifact(run_paths.dense_points_path, kind="ply", fingerprint="dense-points-v1")
    )
    reference = ReferenceArtifacts(
        reference_cloud_ply=_artifact(run_paths.reference_cloud_path, kind="ply", fingerprint="reference-cloud-v1")
    )
    trajectory_metrics = TrajectoryMetrics(
        metrics_json=_artifact(run_paths.trajectory_metrics_path, kind="json", fingerprint="trajectory-metrics-v1")
    )
    cloud_metrics = CloudMetrics(
        metrics_json=_artifact(run_paths.cloud_metrics_path, kind="json", fingerprint="cloud-metrics-v1")
    )
    efficiency_metrics = EfficiencyMetrics(
        metrics_json=_artifact(run_paths.efficiency_metrics_path, kind="json", fingerprint="efficiency-metrics-v1")
    )
    stage_status = _mock_stage_statuses(plan)
    stage_manifests = [
        StageManifest(
            stage_id=stage.id,
            config_hash=f"cfg-{stage.id.value}-v1",
            input_fingerprint=f"inputs-{stage.id.value}-v1",
            output_paths={path.stem: path for path in stage.outputs},
            status=stage_status[stage.id],
        )
        for stage in plan.stages
    ]
    summary = RunSummary(run_id=plan.run_id, artifact_root=plan.artifact_root, stage_status=stage_status)
    return MockRunDossier(
        request=request,
        plan=plan,
        sequence=sequence,
        tracking=tracking,
        dense=dense,
        reference=reference,
        trajectory_metrics=trajectory_metrics,
        cloud_metrics=cloud_metrics,
        efficiency_metrics=efficiency_metrics,
        stage_manifests=stage_manifests,
        summary=summary,
    )


def _mock_stage_statuses(plan: RunPlan) -> dict[RunPlanStageId, StageExecutionStatus]:
    return {stage.id: _MOCK_STAGE_STATUS_OVERRIDES.get(stage.id, StageExecutionStatus.RAN) for stage in plan.stages}


def _render_pipeline_demo(context: AppContext) -> None:
    statuses = context.advio_service.local_scene_statuses()
    previewable_ids = [status.scene.sequence_id for status in statuses if status.replay_ready]
    with st.container(border=True):
        st.subheader("Minimal ADVIO Runner")
        st.caption(
            "Run a replay-ready ADVIO scene through the repository-local mock tracker. Offline mode plays one pass, while streaming mode keeps looping the replay."
        )
        if not previewable_ids:
            st.info(
                "Download the ADVIO streaming bundle for at least one scene to unlock the interactive pipeline demo."
            )
            return
        page_state = context.state.pipeline
        selected_sequence_id = (
            page_state.sequence_id if page_state.sequence_id in previewable_ids else previewable_ids[0]
        )
        with st.form("pipeline_demo_form", border=False):
            selected_sequence_id = st.selectbox(
                "ADVIO Scene",
                options=previewable_ids,
                index=previewable_ids.index(selected_sequence_id),
                format_func=lambda sequence_id: context.advio_service.scene(sequence_id).display_name,
            )
            left, right = st.columns(2, gap="large")
            with left:
                mode = st.selectbox(
                    "Mode",
                    options=list(PipelineMode),
                    index=list(PipelineMode).index(page_state.mode),
                    format_func=_pipeline_mode_label,
                )
                method = st.selectbox(
                    "Mock Method",
                    options=list(MethodId),
                    index=list(MethodId).index(page_state.method),
                    format_func=lambda item: item.display_name,
                )
            with right:
                pose_source = st.selectbox(
                    "Pose Source",
                    options=list(AdvioPoseSource),
                    index=list(AdvioPoseSource).index(page_state.pose_source),
                    format_func=_pose_source_label,
                )
                respect_video_rotation = st.toggle(
                    "Respect video rotation metadata",
                    value=page_state.respect_video_rotation,
                )
            start_requested = st.form_submit_button(
                "Start run" if not page_state.is_running else "Restart run",
                type="primary",
                use_container_width=True,
            )
        stop_requested = st.button("Stop run", disabled=not page_state.is_running, use_container_width=True)
        error_message = handle_pipeline_demo_action(
            context,
            PipelineDemoFormData(
                sequence_id=selected_sequence_id,
                mode=mode,
                method=method,
                pose_source=pose_source,
                respect_video_rotation=respect_video_rotation,
                start_requested=start_requested,
                stop_requested=stop_requested,
            ),
        )
        if error_message:
            st.error(error_message)

        @st.fragment(run_every=0.2 if context.state.pipeline.is_running else None)
        def _render_fragment() -> None:
            _render_pipeline_demo_snapshot(sync_pipeline_demo_state(context))

        _render_fragment()


def _render_pipeline_demo_snapshot(snapshot: PipelineDemoSnapshot) -> None:
    _render_pipeline_demo_notice(snapshot)
    metrics = (
        ("Status", snapshot.state.value.upper()),
        ("Mode", "Idle" if snapshot.mode is None else _pipeline_mode_label(snapshot.mode)),
        ("Received Frames", str(snapshot.received_frames)),
        ("Frame Rate", f"{snapshot.measured_fps:.2f} fps"),
        ("Map Points", str(snapshot.num_map_points)),
    )
    for column, (label, value) in zip(st.columns(5, gap="small"), metrics, strict=True):
        column.metric(label, value)
    if snapshot.plan is not None:
        st.caption(
            f"Run Id: `{snapshot.plan.run_id}` · Artifact Root: `{snapshot.plan.artifact_root}` · Method: {snapshot.plan.method.display_name}"
        )
    packet = snapshot.latest_packet
    tabs = st.tabs(["Frames", "Trajectory", "Plan", "Artifacts"])
    with tabs[0]:
        if packet is None:
            st.info("No frame has been processed yet.")
        else:
            left, right = st.columns((1.1, 0.9), gap="large")
            with left:
                st.markdown("**RGB Frame**")
                st.image(packet.rgb, channels="RGB", clamp=True)
            with right:
                st.markdown("**Tracking Update**")
                if snapshot.latest_update is None:
                    st.info("No tracking update is available yet.")
                else:
                    st.json(snapshot.latest_update.model_dump(mode="json"), expanded=False)
                st.markdown("**Frame Metadata**")
                st.json(
                    {
                        "seq": packet.seq,
                        "timestamp_ns": packet.timestamp_ns,
                        "metadata": packet.metadata,
                    },
                    expanded=False,
                )
                st.markdown("**Camera Intrinsics**")
                if packet.intrinsics is None:
                    st.info("Camera intrinsics are not available for the current packet.")
                else:
                    st.latex(
                        format_camera_intrinsics_latex(
                            fx=packet.intrinsics.fx,
                            fy=packet.intrinsics.fy,
                            cx=packet.intrinsics.cx,
                            cy=packet.intrinsics.cy,
                        )
                    )
    with tabs[1]:
        if len(snapshot.trajectory_positions_xyz) == 0:
            st.info("The mock tracker has not produced any trajectory points yet.")
        else:
            st.plotly_chart(
                build_live_trajectory_figure(
                    snapshot.trajectory_positions_xyz,
                    snapshot.trajectory_timestamps_s if len(snapshot.trajectory_timestamps_s) else None,
                ),
                width="stretch",
            )
    with tabs[2]:
        if snapshot.plan is None:
            st.info("Start a run to inspect the generated plan and execution records.")
        else:
            left, right = st.columns(2, gap="large")
            with left:
                st.markdown("**Planned Stages**")
                st.dataframe(_stage_rows(snapshot.plan), hide_index=True, width="stretch")
            with right:
                st.markdown("**Stage Manifests**")
                if snapshot.stage_manifests:
                    st.dataframe(_stage_manifest_rows(snapshot.stage_manifests), hide_index=True, width="stretch")
                else:
                    st.info("Stage manifests will appear once the run starts writing outputs.")
    with tabs[3]:
        if snapshot.sequence_manifest is None and snapshot.tracking is None and snapshot.summary is None:
            st.info("Run the demo to inspect the materialized manifest, tracking artifacts, and run summary.")
        else:
            left, right = st.columns(2, gap="large")
            with left:
                if snapshot.sequence_manifest is not None:
                    st.markdown("**Sequence Manifest**")
                    st.code(_json_dump(snapshot.sequence_manifest.model_dump(mode="json")), language="json")
                if snapshot.summary is not None:
                    st.markdown("**Run Summary**")
                    st.code(_json_dump(snapshot.summary.model_dump(mode="json")), language="json")
            with right:
                if snapshot.tracking is not None:
                    st.markdown("**Tracking Artifacts**")
                    st.code(_json_dump(snapshot.tracking.model_dump(mode="json")), language="json")


def _render_pipeline_demo_notice(snapshot: PipelineDemoSnapshot) -> None:
    match snapshot.state:
        case PipelineDemoState.IDLE:
            st.info("Select a replay-ready ADVIO scene and start the minimal pipeline demo.")
        case PipelineDemoState.CONNECTING:
            st.info("Preparing the sequence manifest and starting the mock tracking runtime.")
        case PipelineDemoState.RUNNING:
            st.success("Processing ADVIO frames through the mock tracking runtime.")
        case PipelineDemoState.COMPLETED:
            st.success("The offline demo finished and wrote mock tracking artifacts.")
        case PipelineDemoState.STOPPED:
            st.warning("The demo stopped. The last frame, trajectory, and written artifacts remain visible below.")
        case PipelineDemoState.FAILED:
            st.error(snapshot.error_message or "The pipeline demo failed.")


def _pipeline_mode_label(mode: PipelineMode) -> str:
    return {
        PipelineMode.OFFLINE: "Offline (single pass)",
        PipelineMode.STREAMING: "Streaming (looped replay)",
    }[mode]


def _pose_source_label(pose_source: AdvioPoseSource) -> str:
    return {
        AdvioPoseSource.GROUND_TRUTH: "Ground Truth",
        AdvioPoseSource.ARCORE: "ARCore",
        AdvioPoseSource.ARKIT: "ARKit",
        AdvioPoseSource.NONE: "No Pose Overlay",
    }[pose_source]


def _stage_rows(plan: RunPlan) -> list[dict[str, str]]:
    return [
        {
            "Stage": stage.title,
            "Id": stage.id.value,
            "Outputs": ", ".join(path.name for path in stage.outputs),
        }
        for stage in plan.stages
    ]


def _output_rows(mock_run: MockRunDossier) -> list[dict[str, str]]:
    return [
        {
            "Contract": "SequenceManifest",
            "Primary Output": mock_run.sequence.rgb_dir.name if mock_run.sequence.rgb_dir is not None else "None",
            "Serialized Keys": ", ".join(mock_run.sequence.model_dump(mode="json").keys()),
        },
        {
            "Contract": "TrackingArtifacts",
            "Primary Output": mock_run.tracking.trajectory_tum.path.name,
            "Serialized Keys": ", ".join(mock_run.tracking.model_dump(mode="json").keys()),
        },
        {
            "Contract": "DenseArtifacts",
            "Primary Output": mock_run.dense.dense_points_ply.path.name,
            "Serialized Keys": ", ".join(mock_run.dense.model_dump(mode="json").keys()),
        },
        {
            "Contract": "ReferenceArtifacts",
            "Primary Output": mock_run.reference.reference_cloud_ply.path.name,
            "Serialized Keys": ", ".join(mock_run.reference.model_dump(mode="json").keys()),
        },
        {
            "Contract": "TrajectoryMetrics",
            "Primary Output": mock_run.trajectory_metrics.metrics_json.path.name,
            "Serialized Keys": ", ".join(mock_run.trajectory_metrics.model_dump(mode="json").keys()),
        },
        {
            "Contract": "CloudMetrics",
            "Primary Output": mock_run.cloud_metrics.metrics_json.path.name,
            "Serialized Keys": ", ".join(mock_run.cloud_metrics.model_dump(mode="json").keys()),
        },
        {
            "Contract": "EfficiencyMetrics",
            "Primary Output": mock_run.efficiency_metrics.metrics_json.path.name,
            "Serialized Keys": ", ".join(mock_run.efficiency_metrics.model_dump(mode="json").keys()),
        },
    ]


def _stage_manifest_rows(stage_manifests: list[StageManifest]) -> list[dict[str, str]]:
    return [
        {
            "Stage": manifest.stage_id.value,
            "Status": manifest.status.value,
            "Config Hash": manifest.config_hash,
            "Outputs": ", ".join(path.name for path in manifest.output_paths.values()),
        }
        for manifest in stage_manifests
    ]


def _artifact(path: Path, *, kind: str, fingerprint: str) -> ArtifactRef:
    return ArtifactRef(path=path, kind=kind, fingerprint=fingerprint)


def _json_dump(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _request_shape_code() -> str:
    return """request = RunRequest(
    ...,
    tracking=TrackingConfig(...),
    dense=DenseConfig(enabled=True),
    reference=ReferenceConfig(enabled=False),
    evaluation=BenchmarkEvaluationConfig(
        compare_to_arcore=True,
        evaluate_cloud=False,
        evaluate_efficiency=True,
    ),
)

plan = request.build(path_config)
request.inspect(show_docs=True)
request.model_dump_jsonable()
request.to_toml()"""


def _tracking_only_code() -> str:
    return """from pathlib import Path

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import BenchmarkEvaluationConfig, DenseConfig, RunRequest, TrackingConfig, VideoSourceSpec

plan = RunRequest(
    experiment_name="tracking-only-demo",
    output_dir=Path("artifacts"),
    source=VideoSourceSpec(video_path=Path("captures/tracking-only.mp4")),
    tracking=TrackingConfig(method=MethodId.VISTA, max_frames=300),
    dense=DenseConfig(enabled=False),
    evaluation=BenchmarkEvaluationConfig(
        compare_to_arcore=False,
        evaluate_cloud=False,
        evaluate_efficiency=False,
    ),
).build(path_config)"""


def _benchmark_code() -> str:
    return """from pathlib import Path

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import BenchmarkEvaluationConfig, DenseConfig, ReferenceConfig, RunRequest, TrackingConfig, VideoSourceSpec

plan = RunRequest(
    experiment_name="benchmark-demo",
    output_dir=Path("artifacts"),
    source=VideoSourceSpec(video_path=Path("captures/lobby.mp4"), frame_stride=2),
    tracking=TrackingConfig(method=MethodId.VISTA),
    dense=DenseConfig(enabled=True),
    reference=ReferenceConfig(enabled=True),
    evaluation=BenchmarkEvaluationConfig(
        compare_to_arcore=True,
        evaluate_cloud=True,
        evaluate_efficiency=True,
    ),
).build(path_config)"""


def _live_capture_code() -> str:
    return """from pathlib import Path

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import BenchmarkEvaluationConfig, DenseConfig, LiveSourceSpec, PipelineMode, RunRequest, TrackingConfig

plan = RunRequest(
    experiment_name="live-capture-demo",
    mode=PipelineMode.STREAMING,
    output_dir=Path("artifacts"),
    source=LiveSourceSpec(source_id="record3d_usb", persist_capture=True),
    tracking=TrackingConfig(method=MethodId.MSTR),
    dense=DenseConfig(enabled=False),
    evaluation=BenchmarkEvaluationConfig(
        compare_to_arcore=False,
        evaluate_cloud=False,
        evaluate_efficiency=False,
    ),
).build(path_config)"""


__all__ = ["render"]
