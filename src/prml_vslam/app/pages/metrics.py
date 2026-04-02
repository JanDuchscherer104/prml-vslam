"""Metrics Streamlit page for trajectory evaluation review."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from ..models import (
    DatasetId,
    DiscoveredRun,
    EvaluationArtifact,
    EvaluationControls,
    MetricsPageState,
    PoseRelationId,
    SelectionSnapshot,
)
from ..plotting.metrics import build_error_figure, build_trajectory_figure

if TYPE_CHECKING:
    from ..bootstrap import AppContext


def render(context: AppContext) -> None:
    """Render the primary metrics page."""
    state = context.state
    service = context.metrics_service

    with st.container(border=True):
        st.caption("Metrics-First App")
        st.title("Trajectory Metrics")
        st.caption(
            "Inspect persisted `evo` results or trigger an explicit APE run for one dataset, sequence, and artifact run."
        )

    selectors_col, controls_col = st.columns((1.6, 1.0), gap="large")
    with selectors_col:
        with st.container(border=True):
            dataset = st.selectbox(
                "Dataset",
                options=list(DatasetId),
                format_func=lambda item: item.label,
                index=list(DatasetId).index(state.metrics.dataset),
            )
            sequences = service.list_sequences(dataset)
            if not sequences:
                state.metrics = MetricsPageState(dataset=dataset)
                context.store.save(state)
                st.warning(f"No local {dataset.label} sequences were found under `{service.dataset_root(dataset)}`.")
                return

            selected_sequence = _select_sequence(
                sequences=sequences,
                current=state.metrics.sequence_slug,
            )
            runs = service.discover_runs(dataset, selected_sequence)
            if not runs:
                state.metrics = MetricsPageState(dataset=dataset, sequence_slug=selected_sequence)
                context.store.save(state)
                st.info(
                    "No benchmark runs with `slam/trajectory.tum` were found for the selected sequence under "
                    f"`{context.path_config.artifacts_dir}`."
                )
                return

            selected_run = _select_run(
                runs=runs,
                current=state.metrics.run_root,
            )

    with controls_col:
        with st.container(border=True):
            controls = _render_controls(state.metrics.evaluation)
            st.caption(
                "Evaluation never runs on selector changes. Only the primary action below writes or refreshes native "
                "`evo` results."
            )

    state.metrics = MetricsPageState(
        dataset=dataset,
        sequence_slug=selected_sequence,
        run_root=selected_run.artifact_root,
        evaluation=controls,
        result_path=state.metrics.result_path,
    )
    context.store.save(state)

    selection = service.resolve_selection(
        dataset=dataset,
        sequence_slug=selected_sequence,
        run_root=selected_run.artifact_root,
    )
    if selection is None:
        st.error("The current dataset selection could not be resolved.")
        return

    try:
        evaluation = service.load_evaluation(selection=selection, controls=controls)
    except RuntimeError as exc:
        st.error(str(exc))
        return
    can_compute = selection.reference_path is not None and selection.run.estimate_path.exists()

    action_col, status_col = st.columns((0.95, 1.05), gap="large")
    with action_col:
        compute = st.button("Compute evo metrics", type="primary", disabled=not can_compute, width="stretch")
    with status_col:
        if selection.reference_path is None:
            st.warning(
                "Missing `ground_truth.tum` for the selected sequence. The app only evaluates when a TUM reference "
                "trajectory already exists."
            )
        elif evaluation is not None:
            st.success(f"Loaded persisted result from `{evaluation.path}`.")
        else:
            st.info("No persisted result matches the current controls yet.")

    if compute:
        with st.spinner("Running evo APE..."):
            try:
                evaluation = service.compute_evaluation(selection=selection, controls=controls)
            except RuntimeError as exc:
                st.error(str(exc))
                return
        state.metrics.result_path = evaluation.path
        context.store.save(state)
        st.success(f"Persisted fresh `evo` result to `{evaluation.path}`.")

    _render_provenance(selection=selection, evaluation=evaluation)
    if evaluation is None:
        return

    metric_columns = st.columns(4, gap="small")
    metric_columns[0].metric("RMSE", f"{evaluation.stats.rmse:.4f}")
    metric_columns[1].metric("Mean", f"{evaluation.stats.mean:.4f}")
    metric_columns[2].metric("Median", f"{evaluation.stats.median:.4f}")
    metric_columns[3].metric("Max", f"{evaluation.stats.max:.4f}")

    figure_columns = st.columns((1.3, 1.0), gap="large")
    with figure_columns[0]:
        if evaluation.trajectories:
            st.plotly_chart(build_trajectory_figure(evaluation.trajectories), width="stretch")
    with figure_columns[1]:
        if evaluation.error_series is not None:
            st.plotly_chart(build_error_figure(evaluation.error_series), width="stretch")


def _select_sequence(*, sequences: list[str], current: str | None) -> str:
    index = sequences.index(current) if current in sequences else 0
    return st.selectbox("Sequence", options=sequences, index=index)


def _select_run(*, runs: list[DiscoveredRun], current: object) -> DiscoveredRun:
    run_paths = [run.artifact_root for run in runs]
    index = run_paths.index(current) if current in run_paths else 0
    return st.selectbox("Run", options=runs, index=index, format_func=lambda run: run.label)


def _render_controls(current: EvaluationControls) -> EvaluationControls:
    pose_relation = st.selectbox(
        "Pose Relation",
        options=list(PoseRelationId),
        index=list(PoseRelationId).index(current.pose_relation),
        format_func=lambda item: item.label,
    )
    align = st.toggle("Rigid alignment", value=current.align)
    correct_scale = st.toggle("Scale correction", value=current.correct_scale)
    max_diff_s = st.number_input(
        "Max timestamp diff (s)",
        min_value=0.0,
        step=0.01,
        format="%.3f",
        value=float(current.max_diff_s),
    )
    return EvaluationControls(
        pose_relation=pose_relation,
        align=align,
        correct_scale=correct_scale,
        max_diff_s=float(max_diff_s),
    )


def _render_provenance(*, selection: SelectionSnapshot, evaluation: EvaluationArtifact | None) -> None:
    # The page keeps provenance dense and visible because the same figure can otherwise be hard to interpret.
    lines = [
        f"- Dataset: `{selection.dataset.label}`",
        f"- Sequence: `{selection.sequence_slug}`",
        f"- Run: `{selection.run.label}`",
        f"- Estimate path: `{selection.run.estimate_path}`",
        f"- Reference path: `{selection.reference_path}`",
    ]
    if evaluation is not None:
        lines.extend(
            [
                f"- Pose relation: `{evaluation.controls.pose_relation.label}`",
                f"- Alignment: `{evaluation.controls.align}`",
                f"- Scale correction: `{evaluation.controls.correct_scale}`",
                f"- Max timestamp diff (s): `{evaluation.controls.max_diff_s:.3f}`",
                f"- Matched pairs: `{evaluation.matched_pairs}`",
                f"- Persisted result: `{evaluation.path}`",
            ]
        )

    st.subheader("Provenance")
    st.markdown("\n".join(lines))
