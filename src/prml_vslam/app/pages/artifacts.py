"""Streamlit page for inspecting persisted pipeline run artifacts."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias

import streamlit as st

from prml_vslam.methods.vista.diagnostics import load_vista_native_slam_diagnostics
from prml_vslam.pipeline.artifact_inspection import (
    RunArtifactCandidate,
    RunArtifactInspection,
    discover_run_artifact_roots,
    inspect_run_artifacts,
)
from prml_vslam.pipeline.contracts.provenance import StageManifest
from prml_vslam.pipeline.run_bundle import RunBundleCollisionPolicy, export_run_bundle, import_run_bundle
from prml_vslam.plotting import (
    DEFAULT_MESH_COLOR,
    build_3d_trajectory_figure,
    build_bev_trajectory_figure,
    build_intrinsics_residual_figure,
    build_native_confidence_figure,
    build_native_intrinsics_figure,
    build_native_scale_figure,
    build_native_timing_figure,
    build_reference_reconstruction_figure,
    build_slam_reference_comparison_figure,
    build_speed_profile_figure,
    build_view_graph_figure,
)
from prml_vslam.utils import BaseData
from prml_vslam.utils.geometry import load_tum_trajectory
from prml_vslam.visualization.validation import write_validation_bundle

from ..state import save_model_updates
from ..ui import render_page_intro

if TYPE_CHECKING:
    from evo.core.trajectory import PoseTrajectory3D

    from ..bootstrap import AppContext

TableValue: TypeAlias = str | int | float | bool | None
TableRow: TypeAlias = dict[str, TableValue]

_RAW_PREVIEW_MAX_BYTES = 100_000
_HEAVY_ARTIFACT_ERRORS = (FileNotFoundError, RuntimeError, ValueError)
_MESH_COLOR_OPTIONS = {
    "#2f6fed": "Saturated blue",
    "#0f9d58": "Green",
    "#7b1fa2": "Purple",
    "#ef6c00": "Orange",
}


def render(context: AppContext) -> None:
    """Render the persisted run artifact inspector."""
    render_page_intro(
        eyebrow="Run Artifacts",
        title="Artifacts",
        body=(
            "Select a method-level run root, inspect typed persisted metadata and paths, "
            "then explicitly load heavier trajectory or reconstruction views."
        ),
    )
    candidates = discover_run_artifact_roots(context.path_config)
    selected_root = _render_run_selector(context, candidates)
    if selected_root is None:
        st.info(f"No persisted run roots were found under `{context.path_config.artifacts_dir}`.")
        return
    if not selected_root.exists():
        st.warning(f"Selected run root does not exist: `{selected_root}`.")
        return

    try:
        inspection = inspect_run_artifacts(selected_root)
    except _HEAVY_ARTIFACT_ERRORS as exc:
        st.error(str(exc))
        return

    if inspection.load_errors:
        with st.expander("Typed load warnings", expanded=False):
            for error in inspection.load_errors:
                st.warning(error)

    _render_bundle_controls(context, inspection)

    overview_tab, paths_tab, trajectories_tab, reconstruction_tab, diagnostics_tab, raw_tab = st.tabs(
        ["Overview", "Paths", "Trajectories", "Reconstruction", "Diagnostics", "Raw"]
    )
    with overview_tab:
        _render_overview(inspection)
    with paths_tab:
        _render_paths(inspection)
    with trajectories_tab:
        _render_trajectories(inspection)
    with reconstruction_tab:
        _render_reconstruction(context, inspection)
    with diagnostics_tab:
        _render_diagnostics(context, inspection)
    with raw_tab:
        _render_raw_previews(inspection)


def _render_run_selector(context: AppContext, candidates: list[RunArtifactCandidate]) -> Path | None:
    state = context.state.artifacts
    with st.container(border=True):
        st.subheader("Run Selection")
        use_manual_path = st.toggle("Use manual artifact root", value=state.use_manual_path)
        selected_run_root = state.selected_run_root
        if candidates and not use_manual_path:
            candidate_roots = [candidate.artifact_root for candidate in candidates]
            if selected_run_root not in candidate_roots:
                selected_run_root = candidate_roots[0]
            selected_run_root = st.selectbox(
                "Discovered run root",
                options=candidate_roots,
                index=candidate_roots.index(selected_run_root),
                format_func=lambda path: _candidate_label(path, candidates),
            )
            st.caption(f"Discovered `{len(candidates)}` persisted run root(s).")
        elif not candidates:
            st.info("No discovered run roots are available; enter an explicit artifact root below.")
            use_manual_path = True

        manual_run_root = st.text_input(
            "Manual artifact root",
            value=state.manual_run_root,
            placeholder=".artifacts/vista-full-tuning/vista",
        )
        save_model_updates(
            context.store,
            context.state,
            state,
            selected_run_root=selected_run_root,
            manual_run_root=manual_run_root,
            use_manual_path=use_manual_path,
        )
    if use_manual_path:
        if not manual_run_root.strip():
            return None
        return context.path_config.resolve_repo_path(manual_run_root.strip())
    return selected_run_root


def _candidate_label(path: Path, candidates: list[RunArtifactCandidate]) -> str:
    for candidate in candidates:
        if candidate.artifact_root == path:
            return candidate.label
    return path.as_posix()


def _render_overview(inspection: RunArtifactInspection) -> None:
    snapshot = inspection.snapshot
    metric_values = (
        ("Run ID", snapshot.run_id or "unknown"),
        ("State", snapshot.state.value.upper()),
        ("Events", str(inspection.event_count)),
        ("Files", str(sum(1 for row in inspection.file_inventory if row.kind != "dir"))),
    )
    for column, (label, value) in zip(st.columns(4, gap="small"), metric_values, strict=True):
        column.metric(label, value)

    st.caption(f"Artifact root: `{inspection.artifact_root}`")
    if inspection.summary is not None:
        st.markdown("**Run Summary**")
        st.json(inspection.summary.model_dump(mode="json"), expanded=False)
    if inspection.stage_manifests:
        st.markdown("**Stages**")
        st.dataframe(StageManifest.table_rows(inspection.stage_manifests), hide_index=True, width="stretch")

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Typed Metadata**")
        _metadata_json("Sequence Manifest", inspection.sequence_manifest)
        _metadata_json("Benchmark Inputs", inspection.benchmark_inputs)
        _metadata_json("Reconstruction Metadata", inspection.reconstruction_metadata)
        _metadata_json("Ground Alignment", inspection.ground_alignment)
    with right:
        st.markdown("**File Inventory**")
        st.dataframe(_inventory_rows(inspection), hide_index=True, width="stretch")
    _render_input_and_attempts(inspection)


def _render_paths(inspection: RunArtifactInspection) -> None:
    st.markdown("**Canonical RunArtifactPaths**")
    st.dataframe(_path_rows(inspection), hide_index=True, width="stretch")
    st.markdown("**Stage Output Paths**")
    if inspection.stage_output_paths:
        st.dataframe(_stage_output_rows(inspection), hide_index=True, width="stretch")
    else:
        st.info("No persisted stage output paths were found.")


def _render_bundle_controls(context: AppContext, inspection: RunArtifactInspection) -> None:
    with st.container(border=True):
        st.subheader("Portable Run Bundle")
        export_column, import_column = st.columns(2, gap="large")
        with export_column:
            default_bundle_path = (
                context.path_config.artifacts_dir
                / f"{inspection.artifact_root.parent.name}-{inspection.artifact_root.name}.prmlrun.tar.gz"
            )
            export_path_text = st.text_input("Export path", value=default_bundle_path.as_posix())
            if st.button("Export selected run", type="primary"):
                try:
                    result = export_run_bundle(
                        inspection.artifact_root,
                        context.path_config.resolve_repo_path(export_path_text),
                    )
                except (OSError, RuntimeError, ValueError) as exc:
                    st.error(str(exc))
                else:
                    st.success(
                        f"Exported `{result.manifest.exported_run_id}` "
                        f"with {len(result.manifest.files)} files to `{result.bundle_path}`."
                    )
        with import_column:
            uploaded_bundle = st.file_uploader("Import `.prmlrun.tar.gz`", type=["gz"])
            collision_policy = st.selectbox(
                "Collision policy",
                options=list(RunBundleCollisionPolicy),
                format_func=lambda policy: policy.value,
            )
            if st.button("Import bundle", disabled=uploaded_bundle is None):
                if uploaded_bundle is None:
                    st.warning("Choose a bundle before importing.")
                    return
                temp_path = _write_uploaded_bundle(uploaded_bundle.getvalue())
                try:
                    result = import_run_bundle(
                        temp_path,
                        output_dir=context.path_config.artifacts_dir,
                        collision_policy=collision_policy,
                    )
                except (OSError, RuntimeError, ValueError) as exc:
                    st.error(str(exc))
                else:
                    st.success(f"Imported run to `{result.artifact_root}`.")
                    if result.warnings:
                        for warning in result.warnings:
                            st.warning(warning)
                    st.rerun()
                finally:
                    temp_path.unlink(missing_ok=True)


def _write_uploaded_bundle(payload: bytes) -> Path:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".prmlrun.tar.gz") as temp_file:
        temp_file.write(payload)
        return Path(temp_file.name)


def _render_trajectories(inspection: RunArtifactInspection) -> None:
    paths = inspection.run_paths
    st.caption("Trajectory files are loaded only when requested.")
    if not st.button("Load trajectory views", type="primary"):
        st.info("Press the button to load TUM trajectories and render trajectory figures.")
        return
    trajectories: list[tuple[str, PoseTrajectory3D]] = []
    try:
        if paths.trajectory_path.exists():
            trajectories.append(("SLAM estimate", load_tum_trajectory(paths.trajectory_path)))
        ground_truth_path = paths.artifact_root / "benchmark" / "ground_truth.tum"
        if ground_truth_path.exists():
            trajectories.append(("Ground truth", load_tum_trajectory(ground_truth_path)))
    except _HEAVY_ARTIFACT_ERRORS as exc:
        st.error(str(exc))
        return
    if not trajectories:
        st.warning("No `slam/trajectory.tum` or `benchmark/ground_truth.tum` file is available for this run.")
        return

    st.plotly_chart(build_bev_trajectory_figure(trajectories, title="Trajectory BEV Overlay"), width="stretch")
    figure_columns = st.columns(2, gap="large")
    figure_columns[0].plotly_chart(
        build_3d_trajectory_figure(trajectories, title="Trajectory 3D Overlay", pose_axes_name="SLAM estimate"),
        width="stretch",
    )
    figure_columns[1].plotly_chart(build_speed_profile_figure(trajectories), width="stretch")


def _render_reconstruction(context: AppContext, inspection: RunArtifactInspection) -> None:
    st.caption("PLY reconstruction artifacts are loaded only when requested.")
    state = context.state.artifacts
    current_color = (
        state.reconstruction_mesh_color
        if state.reconstruction_mesh_color in _MESH_COLOR_OPTIONS
        else DEFAULT_MESH_COLOR
    )
    with st.form("artifact_reconstruction_render_form"):
        modality_left, modality_right = st.columns(2, gap="small")
        show_point_cloud = modality_left.checkbox(
            "Point cloud",
            value=state.show_reconstruction_point_cloud,
        )
        show_mesh = modality_right.checkbox(
            "Mesh",
            value=state.show_reconstruction_mesh,
        )
        budget_left, budget_right = st.columns(2, gap="small")
        max_points = int(
            budget_left.number_input(
                "Max points",
                min_value=1_000,
                max_value=1_000_000,
                value=state.reconstruction_max_points,
                step=5_000,
            )
        )
        target_triangles = int(
            budget_right.number_input(
                "Target triangles",
                min_value=1_000,
                max_value=1_000_000,
                value=state.reconstruction_target_triangles,
                step=5_000,
            )
        )
        style_left, style_right = st.columns(2, gap="small")
        mesh_opacity = float(
            style_left.slider(
                "Mesh opacity",
                min_value=0.05,
                max_value=1.0,
                value=state.reconstruction_mesh_opacity,
                step=0.05,
            )
        )
        mesh_color = style_right.selectbox(
            "Mesh color",
            options=list(_MESH_COLOR_OPTIONS),
            index=list(_MESH_COLOR_OPTIONS).index(current_color),
            format_func=lambda color: _MESH_COLOR_OPTIONS[color],
        )
        render_requested = st.form_submit_button(
            "Render reconstruction",
            type="primary",
            disabled=not (show_point_cloud or show_mesh),
        )
    save_model_updates(
        context.store,
        context.state,
        state,
        show_reconstruction_point_cloud=show_point_cloud,
        show_reconstruction_mesh=show_mesh,
        reconstruction_max_points=max_points,
        reconstruction_target_triangles=target_triangles,
        reconstruction_mesh_opacity=mesh_opacity,
        reconstruction_mesh_color=mesh_color,
    )
    if not show_point_cloud and not show_mesh:
        st.warning("Select at least one reconstruction modality.")
        return
    if not render_requested:
        st.info("Submit the form to load the selected reconstruction modalities.")
        return
    try:
        figure, summary = build_reference_reconstruction_figure(
            inspection.artifact_root,
            show_point_cloud=show_point_cloud,
            show_mesh=show_mesh,
            max_points=max_points,
            target_triangles=target_triangles,
            mesh_color=mesh_color,
            mesh_opacity=mesh_opacity,
        )
    except _HEAVY_ARTIFACT_ERRORS as exc:
        st.error(str(exc))
        return
    st.plotly_chart(figure, width="stretch")
    st.json(summary.model_dump(mode="json"), expanded=False)


def _render_diagnostics(context: AppContext, inspection: RunArtifactInspection) -> None:
    _render_native_diagnostics(inspection)
    st.divider()
    _render_slam_reference_comparison(context, inspection)
    st.divider()
    _render_rerun_validation(context, inspection)


def _render_native_diagnostics(inspection: RunArtifactInspection) -> None:
    st.subheader("Native SLAM Diagnostics")
    st.caption("Native arrays are loaded only when requested.")
    if not st.button("Load native diagnostics", type="primary"):
        st.info("Load `confs.npz`, `scales.npy`, `intrinsics.npy`, `trajectory.npy`, and `view_graph.npz`.")
        return
    try:
        diagnostics = load_vista_native_slam_diagnostics(inspection.artifact_root)
    except _HEAVY_ARTIFACT_ERRORS as exc:
        st.error(str(exc))
        return
    metrics = (
        ("Keyframes", str(len(diagnostics.keyframe_indices))),
        (
            "Confidence threshold",
            "n/a" if diagnostics.confidence_threshold is None else f"{diagnostics.confidence_threshold:.3f}",
        ),
        ("View graph nodes", "n/a" if diagnostics.view_graph is None else str(diagnostics.view_graph.node_count)),
        ("Loop-like edges", "n/a" if diagnostics.view_graph is None else str(len(diagnostics.view_graph.loop_edges))),
    )
    for column, (label, value) in zip(st.columns(4, gap="small"), metrics, strict=True):
        column.metric(label, value)
    rows = [
        [build_native_confidence_figure(diagnostics), build_native_scale_figure(diagnostics)],
        [build_native_intrinsics_figure(diagnostics), build_native_timing_figure(diagnostics)],
    ]
    for figures in rows:
        for column, figure in zip(st.columns(2, gap="large"), figures, strict=True):
            column.plotly_chart(figure, width="stretch")
    if diagnostics.view_graph is not None:
        st.plotly_chart(build_view_graph_figure(diagnostics), width="stretch")
        with st.expander("Top connected view-graph nodes", expanded=False):
            st.dataframe(
                [{"Node": item.node, "Degree": item.degree} for item in diagnostics.view_graph.top_degree_nodes],
                hide_index=True,
                width="stretch",
            )
    if diagnostics.intrinsics_comparison is not None:
        st.plotly_chart(build_intrinsics_residual_figure(diagnostics), width="stretch")
        with st.expander("Intrinsics comparison summary", expanded=False):
            comparison = diagnostics.intrinsics_comparison
            st.json(
                {
                    "raster_space": comparison.raster_space,
                    "reference": comparison.reference.model_dump(mode="json"),
                    "mean_estimate": comparison.mean_estimate.model_dump(mode="json"),
                },
                expanded=False,
            )


def _render_slam_reference_comparison(context: AppContext, inspection: RunArtifactInspection) -> None:
    state = context.state.artifacts
    st.subheader("SLAM vs Reference")
    with st.form("artifact_slam_reference_comparison_form"):
        modality_columns = st.columns(4, gap="small")
        show_slam_cloud = modality_columns[0].checkbox("SLAM cloud", value=state.comparison_show_slam_cloud)
        show_reference_cloud = modality_columns[1].checkbox(
            "Reference cloud",
            value=state.comparison_show_reference_cloud,
        )
        show_reference_mesh = modality_columns[2].checkbox("Reference mesh", value=state.comparison_show_reference_mesh)
        show_trajectories = modality_columns[3].checkbox("Trajectories", value=state.comparison_show_trajectories)
        budget_columns = st.columns(3, gap="small")
        slam_max_points = int(
            budget_columns[0].number_input(
                "SLAM max points",
                min_value=1_000,
                max_value=1_000_000,
                value=state.comparison_slam_max_points,
                step=10_000,
            )
        )
        reference_max_points = int(
            budget_columns[1].number_input(
                "Reference max points",
                min_value=1_000,
                max_value=1_000_000,
                value=state.comparison_reference_max_points,
                step=10_000,
            )
        )
        target_triangles = int(
            budget_columns[2].number_input(
                "Reference target triangles",
                min_value=1_000,
                max_value=1_000_000,
                value=state.comparison_target_triangles,
                step=10_000,
            )
        )
        render_requested = st.form_submit_button(
            "Render SLAM vs reference",
            type="primary",
            disabled=not any((show_slam_cloud, show_reference_cloud, show_reference_mesh, show_trajectories)),
        )
    save_model_updates(
        context.store,
        context.state,
        state,
        comparison_show_slam_cloud=show_slam_cloud,
        comparison_show_reference_cloud=show_reference_cloud,
        comparison_show_reference_mesh=show_reference_mesh,
        comparison_show_trajectories=show_trajectories,
        comparison_slam_max_points=slam_max_points,
        comparison_reference_max_points=reference_max_points,
        comparison_target_triangles=target_triangles,
    )
    if not any((show_slam_cloud, show_reference_cloud, show_reference_mesh, show_trajectories)):
        st.warning("Select at least one comparison modality.")
        return
    if not render_requested:
        st.info("Submit the form to load the selected comparison artifacts.")
        return
    try:
        figure, summary = build_slam_reference_comparison_figure(
            inspection.artifact_root,
            show_slam_cloud=show_slam_cloud,
            show_reference_cloud=show_reference_cloud,
            show_reference_mesh=show_reference_mesh,
            show_trajectories=show_trajectories,
            slam_max_points=slam_max_points,
            reference_max_points=reference_max_points,
            target_triangles=target_triangles,
        )
    except _HEAVY_ARTIFACT_ERRORS as exc:
        st.error(str(exc))
        return
    st.plotly_chart(figure, width="stretch")
    st.json(summary.model_dump(mode="json"), expanded=False)


def _render_rerun_validation(context: AppContext, inspection: RunArtifactInspection) -> None:
    state = context.state.artifacts
    st.subheader("Rerun Validation Bundle")
    recording_path = inspection.run_paths.viewer_rrd_path
    if not recording_path.exists():
        st.info(f"No repo-owned Rerun recording exists at `{recording_path}`.")
        return
    with st.form("artifact_rerun_validation_form"):
        columns = st.columns(2, gap="small")
        max_keyed_clouds = int(
            columns[0].number_input(
                "Max keyed clouds",
                min_value=1,
                max_value=200,
                value=state.rerun_validation_max_keyed_clouds,
                step=1,
            )
        )
        max_render_points = int(
            columns[1].number_input(
                "Max render points",
                min_value=1_000,
                max_value=250_000,
                value=state.rerun_validation_max_render_points,
                step=5_000,
            )
        )
        generate = st.form_submit_button("Generate validation bundle", type="primary")
    save_model_updates(
        context.store,
        context.state,
        state,
        rerun_validation_max_keyed_clouds=max_keyed_clouds,
        rerun_validation_max_render_points=max_render_points,
    )
    if not generate:
        st.info("Generate the bundle explicitly; `.rrd` files can be large.")
        return
    try:
        artifacts = write_validation_bundle(
            recording_path,
            output_dir=recording_path.parent / "validation",
            max_keyed_clouds=max_keyed_clouds,
            max_render_points=max_render_points,
        )
    except _HEAVY_ARTIFACT_ERRORS as exc:
        st.error(str(exc))
        return
    st.success(f"Validation bundle written to `{artifacts.summary_json.parent}`.")
    st.json(artifacts.model_dump(mode="json"), expanded=False)
    preview_columns = st.columns(2, gap="large")
    preview_columns[0].image(str(artifacts.map_xy_png), caption="Map XY")
    preview_columns[1].image(str(artifacts.map_xz_png), caption="Map XZ")


def _render_raw_previews(inspection: RunArtifactInspection) -> None:
    preview_paths = [
        row.path
        for row in inspection.file_inventory
        if row.kind in {"json", "yaml", "yml"}
        and row.size_bytes is not None
        and row.size_bytes <= _RAW_PREVIEW_MAX_BYTES
    ]
    if not preview_paths:
        st.info("No small JSON or YAML metadata files are available for raw preview.")
        return
    selected_path = st.selectbox(
        "Metadata file",
        options=preview_paths,
        format_func=lambda path: path.relative_to(inspection.artifact_root).as_posix(),
    )
    st.code(_raw_preview_text(selected_path), language=_raw_preview_language(selected_path))


def _render_input_and_attempts(inspection: RunArtifactInspection) -> None:
    columns = st.columns(2, gap="large")
    with columns[0]:
        st.markdown("**Input Diagnostics**")
        if inspection.input_diagnostics is None:
            st.info("Input diagnostics are not available.")
        else:
            st.json(inspection.input_diagnostics.model_dump(mode="json"), expanded=False)
    with columns[1]:
        st.markdown("**Run Attempts**")
        if not inspection.attempts:
            st.info("No run attempts were found in the event log.")
        else:
            st.dataframe(_attempt_rows(inspection), hide_index=True, width="stretch")


def _metadata_json(label: str, value: BaseData | None) -> None:
    if value is None:
        st.caption(f"{label}: missing")
        return
    with st.expander(label, expanded=False):
        st.json(value.model_dump(mode="json"), expanded=False)


def _inventory_rows(inspection: RunArtifactInspection) -> list[TableRow]:
    return [
        {
            "Path": row.relative_path,
            "Kind": row.kind,
            "Size": row.size_label,
        }
        for row in inspection.file_inventory
    ]


def _attempt_rows(inspection: RunArtifactInspection) -> list[TableRow]:
    return [
        {
            "Attempt": attempt.attempt_index,
            "State": attempt.state,
            "Events": attempt.event_count,
            "First": attempt.first_event_id,
            "Last": attempt.last_event_id,
            "Failed Stage": attempt.failed_stage_key,
        }
        for attempt in inspection.attempts
    ]


def _path_rows(inspection: RunArtifactInspection) -> list[TableRow]:
    return [
        {
            "Name": row.name,
            "Exists": row.exists,
            "Kind": row.kind,
            "Size": row.size_label,
            "Path": row.path.as_posix(),
        }
        for row in inspection.canonical_paths
    ]


def _stage_output_rows(inspection: RunArtifactInspection) -> list[TableRow]:
    return [
        {
            "Stage": row.stage_id,
            "Name": row.name,
            "Exists": row.exists,
            "Kind": row.kind,
            "Size": row.size_label,
            "Path": row.path.as_posix(),
        }
        for row in inspection.stage_output_paths
    ]


def _raw_preview_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        try:
            return json.dumps(json.loads(text), indent=2, sort_keys=True)
        except json.JSONDecodeError:
            return text
    return text


def _raw_preview_language(path: Path) -> str:
    return "json" if path.suffix == ".json" else "yaml"


__all__ = ["render"]
