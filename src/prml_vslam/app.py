"""Streamlit workbench for the PRML VSLAM benchmark scaffold."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
from pydantic import ValidationError

from prml_vslam.pipeline import (
    CaptureMetadataConfig,
    Envelope,
    InsightTone,
    MaterializedWorkspace,
    MessageKind,
    MethodId,
    PipelineMode,
    PipelinePlannerService,
    RunPlan,
    RunPlanInsight,
    RunPlanRequest,
    RunPlanStage,
    SessionManager,
    TimestampSource,
    WorkspaceMaterializerService,
    make_envelope,
)

WORKSPACE_STATE_KEY = "_prml_vslam_materialized_workspace"


def run_app() -> None:
    """Render the PRML VSLAM workbench."""
    st.set_page_config(
        page_title="PRML VSLAM Workbench",
        page_icon=":material/route:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_styles()

    planner = PipelinePlannerService()
    materializer = WorkspaceMaterializerService(planner=planner)

    request, materialize_requested, clear_requested = _render_sidebar_controls()
    _render_hero()
    if request is None:
        st.error("The current inputs are invalid. Fix the highlighted values in the control rail and try again.")
        return

    plan = planner.build_plan(request)
    insights = planner.interpret_plan(request, plan)
    workspace = _load_workspace()

    if clear_requested:
        st.session_state.pop(WORKSPACE_STATE_KEY, None)
        workspace = None

    if materialize_requested:
        try:
            workspace = materializer.materialize(request)
            _save_workspace(workspace)
            st.success(f"Materialized workspace at {workspace.artifact_root}.")
        except FileExistsError as exc:
            st.error(str(exc))

    _render_summary_metrics(plan=plan, workspace=workspace)
    tab_plan, tab_interpretation, tab_artifacts, tab_contracts, tab_runtime = st.tabs(
        ["Plan", "Interpretation", "Artifacts", "Raw Contracts", "Runtime Demo"]
    )

    with tab_plan:
        _render_plan_tab(plan)

    with tab_interpretation:
        _render_interpretation_tab(insights)

    with tab_artifacts:
        _render_artifacts_tab(plan=plan, workspace=workspace)

    with tab_contracts:
        _render_contracts_tab(request=request, plan=plan, workspace=workspace)

    with tab_runtime:
        _render_runtime_demo_tab()


def _render_sidebar_controls() -> tuple[RunPlanRequest | None, bool, bool]:
    st.sidebar.markdown("### Run Setup")
    st.sidebar.caption("Batch-first planning, materialization, and artifact inspection for the benchmark scaffold.")

    experiment_name = st.sidebar.text_input("Experiment name", value="Lobby Sweep 01")
    video_path = st.sidebar.text_input("Video path", value="captures/lobby.mp4")
    output_dir = st.sidebar.text_input("Output directory", value="artifacts")

    primary_col, secondary_col = st.sidebar.columns(2)
    mode = primary_col.radio(
        "Mode",
        options=list(PipelineMode),
        index=list(PipelineMode).index(PipelineMode.BATCH),
        format_func=lambda item: item.value.title(),
    )
    method = secondary_col.selectbox(
        "Method",
        options=list(MethodId),
        index=list(MethodId).index(MethodId.VISTA_SLAM),
        format_func=lambda item: item.value.replace("_", " ").upper(),
    )

    frame_stride = st.sidebar.slider("Frame stride", min_value=1, max_value=12, value=1)
    enable_dense_mapping = st.sidebar.toggle("Enable dense mapping", value=True)
    compare_to_arcore = st.sidebar.toggle("Reserve ARCore comparison", value=True)
    build_ground_truth_cloud = st.sidebar.toggle("Reserve reference reconstruction", value=True)

    with st.sidebar.expander("Capture metadata", expanded=True):
        device_label = st.text_input("Device label", value="Pixel 8 Pro")
        frame_rate_hz = st.number_input("Nominal frame rate (Hz)", min_value=1.0, max_value=240.0, value=30.0, step=0.5)
        timestamp_source = st.selectbox(
            "Timestamp source",
            options=list(TimestampSource),
            index=list(TimestampSource).index(TimestampSource.CAPTURE),
            format_func=lambda item: item.value.replace("_", " ").title(),
        )
        arcore_log_path = st.text_input("ARCore log path", value="captures/lobby-arcore.json")
        calibration_hint_path = st.text_input("Calibration hint path", value="")
        notes = st.text_area("Operator notes", value="Indoor walkthrough with gentle turns.", height=120)

    materialize_requested = st.sidebar.button(
        "Materialize workspace",
        type="primary",
        width="stretch",
    )
    clear_requested = st.sidebar.button(
        "Clear saved workspace",
        width="stretch",
    )

    try:
        request = RunPlanRequest(
            experiment_name=experiment_name,
            video_path=Path(video_path),
            output_dir=Path(output_dir),
            mode=mode,
            method=method,
            frame_stride=frame_stride,
            enable_dense_mapping=enable_dense_mapping,
            compare_to_arcore=compare_to_arcore,
            build_ground_truth_cloud=build_ground_truth_cloud,
            capture=CaptureMetadataConfig(
                device_label=device_label or None,
                frame_rate_hz=frame_rate_hz,
                timestamp_source=timestamp_source,
                arcore_log_path=Path(arcore_log_path) if arcore_log_path.strip() else None,
                calibration_hint_path=Path(calibration_hint_path) if calibration_hint_path.strip() else None,
                notes=notes or None,
            ),
        )
        return request, materialize_requested, clear_requested
    except ValidationError as exc:
        st.sidebar.error("Invalid run configuration.")
        st.sidebar.code(str(exc))
        return None, materialize_requested, clear_requested


def _render_hero() -> None:
    st.markdown(
        """
        <section class="hero-card">
          <p class="eyebrow">Batch-first planning</p>
          <h1>PRML VSLAM Workbench</h1>
          <p class="hero-copy">
            Plan the run, materialize the workspace, and inspect the artifact contract before any
            heavyweight SLAM wrapper or rendering stage enters the picture.
          </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_summary_metrics(*, plan: RunPlan, workspace: MaterializedWorkspace | None) -> None:
    metric_mode, metric_method, metric_stages, metric_artifacts = st.columns(4)
    metric_mode.metric("Mode", plan.mode.value.title())
    metric_method.metric("Method", plan.method.value.replace("_", " ").upper())
    metric_stages.metric("Planned stages", len(plan.stages))
    metric_artifacts.metric("Current artifacts", len(workspace.artifacts) if workspace is not None else 0)
    st.caption(f"Artifact root: `{plan.artifact_root}`")


def _render_plan_tab(plan: RunPlan) -> None:
    chart_col, detail_col = st.columns([1.1, 0.9], gap="large")

    with chart_col:
        st.markdown("### Planned stage flow")
        st.plotly_chart(_build_stage_figure(plan), width="stretch", config={"displayModeBar": False})

    with detail_col:
        st.markdown("### Stage reading")
        for index, stage in enumerate(plan.stages, start=1):
            _render_stage_card(stage=stage, index=index)


def _render_interpretation_tab(insights: list[RunPlanInsight]) -> None:
    st.markdown("### Interpretation")
    st.caption(
        "The workbench translates the plan into explicit design consequences so the batch scaffold stays legible."
    )
    columns = st.columns(2, gap="large")
    for index, insight in enumerate(insights):
        with columns[index % len(columns)]:
            _render_insight_card(insight)


def _render_artifacts_tab(*, plan: RunPlan, workspace: MaterializedWorkspace | None) -> None:
    st.markdown("### Materialized artifacts")
    if workspace is None:
        st.info("No workspace has been materialized yet. Use the control rail to create the planned directory tree.")
        return

    if workspace.artifact_root != plan.artifact_root:
        st.warning(
            "The saved workspace belongs to a different artifact root than the current draft. "
            "Materialize again to refresh the on-disk preview."
        )

    chart_col, table_col = st.columns([0.8, 1.2], gap="large")
    with chart_col:
        st.plotly_chart(_build_artifact_figure(workspace), width="stretch", config={"displayModeBar": False})
    with table_col:
        table_rows = [
            {
                "stage": artifact.stage_id.value,
                "label": artifact.label,
                "kind": artifact.kind,
                "placeholder": artifact.is_placeholder,
                "path": artifact.path.as_posix(),
            }
            for artifact in workspace.artifacts
        ]
        st.dataframe(table_rows, width="stretch", hide_index=True)

    preview_col_manifest, preview_col_plan = st.columns(2, gap="large")
    with preview_col_manifest:
        st.markdown("#### Capture manifest")
        st.code(workspace.capture_manifest_path.read_text(encoding="utf-8"), language="json")
    with preview_col_plan:
        st.markdown("#### Run plan snapshot")
        st.code(workspace.run_plan_path.read_text(encoding="utf-8"), language="toml")


def _render_contracts_tab(*, request: RunPlanRequest, plan: RunPlan, workspace: MaterializedWorkspace | None) -> None:
    st.markdown("### Raw contracts")
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("#### Run request")
        st.json(request.model_dump(mode="json"))
        st.markdown("#### Run plan")
        st.json(plan.model_dump(mode="json"))
    with right:
        if workspace is not None:
            st.markdown("#### Materialized workspace")
            st.json(workspace.model_dump(mode="json"))
        else:
            st.markdown("#### Materialized workspace")
            st.info("No workspace summary is available yet.")


def _build_stage_figure(plan: RunPlan) -> go.Figure:
    stage_titles = [f"{index}. {stage.title}" for index, stage in enumerate(plan.stages, start=1)]
    artifact_counts = [max(1, len(stage.outputs)) for stage in plan.stages]
    colors = [_stage_color(stage) for stage in plan.stages]

    figure = go.Figure(
        go.Bar(
            x=list(reversed(artifact_counts)),
            y=list(reversed(stage_titles)),
            orientation="h",
            text=[stage.id.value.replace("_", " ") for stage in reversed(plan.stages)],
            textposition="outside",
            marker=dict(color=list(reversed(colors)), line=dict(color="#0f172a", width=1.0)),
            hovertemplate="<b>%{y}</b><br>Planned outputs: %{x}<extra></extra>",
        )
    )
    figure.update_layout(
        height=max(420, 70 * len(plan.stages)),
        margin=dict(l=0, r=24, t=8, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Planned outputs", gridcolor="rgba(15,23,42,0.08)", zeroline=False),
        yaxis=dict(title="", automargin=True),
        font=dict(family="Georgia, 'Times New Roman', serif", color="#0f172a"),
    )
    return figure


def _build_artifact_figure(workspace: MaterializedWorkspace) -> go.Figure:
    counts = Counter(artifact.kind for artifact in workspace.artifacts)
    labels = list(counts.keys())
    values = list(counts.values())
    figure = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.58,
            marker=dict(colors=["#1d4ed8", "#0f766e", "#f59e0b", "#9333ea", "#334155", "#ef4444"]),
            sort=False,
        )
    )
    figure.update_layout(
        height=360,
        margin=dict(l=0, r=0, t=12, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Georgia, 'Times New Roman', serif", color="#0f172a"),
        annotations=[dict(text="Artifacts", x=0.5, y=0.5, showarrow=False, font=dict(size=18))],
    )
    return figure


def _render_stage_card(*, stage: RunPlanStage, index: int) -> None:
    outputs = "".join(f"<li><code>{output.as_posix()}</code></li>" for output in stage.outputs)
    st.markdown(
        f"""
        <div class="stage-card">
          <p class="stage-kicker">Stage {index:02d} · {stage.id.value.replace("_", " ")}</p>
          <h3>{stage.title}</h3>
          <p>{stage.summary}</p>
          <ul>{outputs}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_insight_card(insight: RunPlanInsight) -> None:
    tone_class = {
        InsightTone.ACCENT: "tone-accent",
        InsightTone.INFO: "tone-info",
        InsightTone.WARNING: "tone-warning",
    }[insight.tone]
    st.markdown(
        f"""
        <div class="insight-card {tone_class}">
          <h3>{insight.title}</h3>
          <p>{insight.detail}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _stage_color(stage: RunPlanStage) -> str:
    if "normalization" in stage.id.value:
        return "#0f766e"
    if "reference" in stage.id.value or "visualization" in stage.id.value:
        return "#f59e0b"
    if "slam" in stage.id.value or "tracking" in stage.id.value:
        return "#1d4ed8"
    return "#334155"


def _load_workspace() -> MaterializedWorkspace | None:
    raw_workspace = st.session_state.get(WORKSPACE_STATE_KEY)
    if raw_workspace is None:
        return None
    return MaterializedWorkspace.model_validate(raw_workspace)


def _save_workspace(workspace: MaterializedWorkspace) -> None:
    st.session_state[WORKSPACE_STATE_KEY] = workspace.model_dump(mode="json")


def _render_runtime_demo_tab() -> None:
    """Interactive streaming pipeline demo with live trajectory visualization."""
    st.markdown("### Pipeline Runtime Demo")
    st.caption(
        "Push synthetic frames through the pipeline runtime and observe per-frame pose updates. "
        "Uses mock SLAM adapters (no GPU required)."
    )

    ctrl_col, vis_col = st.columns([0.35, 0.65], gap="large")

    with ctrl_col:
        demo_method = st.selectbox(
            "Method backend",
            options=list(MethodId),
            index=0,
            format_func=lambda m: m.value.replace("_", " ").upper(),
            key="runtime_demo_method",
        )
        demo_frames = st.slider("Number of frames", min_value=10, max_value=200, value=60, key="runtime_demo_frames")
        run_demo = st.button("Run streaming demo", type="primary", key="runtime_demo_run")

    if run_demo:
        mgr = SessionManager()
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_root = Path(tmpdir) / "demo" / "streaming" / demo_method.value
            sess = mgr.create_session(
                mode="streaming",
                method=demo_method,
                artifact_root=artifact_root,
            )

            poses: list[dict[str, float]] = []
            all_outputs: list[Envelope] = []

            progress = ctrl_col.progress(0, text="Pushing frames...")
            for i in range(demo_frames):
                envelope = make_envelope(
                    session_id=sess.session_id,
                    seq=i,
                    kind=MessageKind.FRAME,
                    payload={"width": 640, "height": 480, "frame_index": i},
                    ts_ns=int(i * (1 / 30) * 1e9),
                )
                outputs = mgr.push(sess.session_id, [envelope])
                all_outputs.extend(outputs)

                for o in outputs:
                    if o.kind == MessageKind.POSE_UPDATE:
                        t = o.payload.get("t_world_camera", [[1, 0, 0, 0]] * 4)
                        poses.append({"x": t[0][3], "y": t[1][3], "z": t[2][3], "frame": i})

                progress.progress((i + 1) / demo_frames, text=f"Frame {i + 1}/{demo_frames}")

            final = mgr.close_session(sess.session_id)
            all_outputs.extend(final)
            progress.empty()

            # Summary metrics
            pose_count = sum(1 for o in all_outputs if o.kind == MessageKind.POSE_UPDATE)
            preview_count = sum(1 for o in all_outputs if o.kind == MessageKind.PREVIEW)
            map_count = sum(1 for o in all_outputs if o.kind == MessageKind.MAP_UPDATE)

            m1, m2, m3 = ctrl_col.columns(3)
            m1.metric("Poses", pose_count)
            m2.metric("Previews", preview_count)
            m3.metric("Map updates", map_count)

            # Trajectory visualization
            with vis_col:
                if poses:
                    xs = [p["x"] for p in poses]
                    ys = [p["y"] for p in poses]
                    zs = [p["z"] for p in poses]
                    frames = [p["frame"] for p in poses]

                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter3d(
                            x=xs,
                            y=ys,
                            z=zs,
                            mode="lines+markers",
                            marker=dict(
                                size=3, color=frames, colorscale="Viridis", showscale=True, colorbar=dict(title="Frame")
                            ),
                            line=dict(color="rgba(29, 78, 216, 0.6)", width=2),
                            text=[f"Frame {f}" for f in frames],
                            hovertemplate="<b>Frame %{text}</b><br>x: %{x:.3f}<br>y: %{y:.3f}<br>z: %{z:.3f}<extra></extra>",
                        )
                    )
                    fig.update_layout(
                        title=f"Trajectory — {demo_method.value.replace('_', ' ').upper()} ({pose_count} poses)",
                        scene=dict(
                            xaxis_title="X (m)",
                            yaxis_title="Y (m)",
                            zaxis_title="Z (m)",
                            aspectmode="data",
                        ),
                        height=520,
                        margin=dict(l=0, r=0, t=40, b=0),
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Georgia, 'Times New Roman', serif", color="#0f172a"),
                    )
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})

                    # BEV (top-down XZ)
                    fig_bev = go.Figure()
                    fig_bev.add_trace(
                        go.Scatter(
                            x=xs,
                            y=zs,
                            mode="lines+markers",
                            marker=dict(
                                size=4, color=frames, colorscale="Viridis", showscale=True, colorbar=dict(title="Frame")
                            ),
                            line=dict(color="rgba(29, 78, 216, 0.5)", width=1.5),
                            hovertemplate="<b>Frame %{text}</b><br>X: %{x:.3f}<br>Z: %{y:.3f}<extra></extra>",
                            text=[str(f) for f in frames],
                        )
                    )
                    fig_bev.update_layout(
                        title="Bird's-eye view (XZ plane)",
                        xaxis_title="X (m)",
                        yaxis_title="Z (m)",
                        height=380,
                        margin=dict(l=0, r=0, t=40, b=0),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        yaxis=dict(scaleanchor="x"),
                        font=dict(family="Georgia, 'Times New Roman', serif", color="#0f172a"),
                    )
                    st.plotly_chart(fig_bev, use_container_width=True, config={"displayModeBar": False})

            # Show last few messages
            with ctrl_col:
                with st.expander("Last 10 output messages"):
                    for o in all_outputs[-10:]:
                        st.json(o.model_dump(mode="json"))
    else:
        with vis_col:
            st.info("Press **Run streaming demo** to push synthetic frames and visualize the trajectory.")


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
          .stApp {
            background:
              radial-gradient(circle at top left, rgba(125, 211, 252, 0.20), transparent 30%),
              radial-gradient(circle at top right, rgba(245, 158, 11, 0.18), transparent 24%),
              linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
            color: #0f172a;
          }
          .hero-card {
            padding: 1.8rem 1.8rem 1.5rem 1.8rem;
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 26px;
            background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(224,231,255,0.86));
            box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
            margin-bottom: 1.2rem;
          }
          .hero-card h1 {
            margin: 0;
            font-family: Georgia, "Times New Roman", serif;
            font-size: 2.4rem;
            line-height: 1.05;
            letter-spacing: -0.03em;
          }
          .eyebrow {
            margin: 0 0 0.45rem 0;
            text-transform: uppercase;
            letter-spacing: 0.18em;
            font-size: 0.78rem;
            font-weight: 700;
            color: #1d4ed8;
          }
          .hero-copy {
            max-width: 50rem;
            margin: 0.85rem 0 0 0;
            font-size: 1.02rem;
            line-height: 1.65;
            color: #334155;
          }
          .stage-card, .insight-card {
            padding: 1rem 1.1rem;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(15, 23, 42, 0.08);
            box-shadow: 0 8px 30px rgba(15, 23, 42, 0.05);
            margin-bottom: 0.85rem;
          }
          .stage-kicker {
            margin: 0 0 0.35rem 0;
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: #64748b;
          }
          .stage-card h3, .insight-card h3 {
            margin: 0 0 0.35rem 0;
            font-family: Georgia, "Times New Roman", serif;
            font-size: 1.05rem;
          }
          .stage-card p, .insight-card p {
            margin: 0.25rem 0 0 0;
            color: #334155;
            line-height: 1.55;
          }
          .stage-card ul {
            margin: 0.7rem 0 0 1rem;
            color: #0f172a;
          }
          .tone-accent {
            border-left: 6px solid #1d4ed8;
          }
          .tone-info {
            border-left: 6px solid #0f766e;
          }
          .tone-warning {
            border-left: 6px solid #f59e0b;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )
