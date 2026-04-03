from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.datasets.interfaces import DatasetId
from prml_vslam.eval.interfaces import EvaluationArtifact, EvaluationControls, PoseRelationId, SelectionSnapshot
from prml_vslam.eval.services import build_selection, list_sequences, resolve_dataset_root

from ..plotting.metrics import build_error_figure, build_trajectory_figure
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext

# fmt: off
EVALUATION_ERRORS = (FileNotFoundError, RuntimeError, ValueError)


def render(context: AppContext) -> None:
    render_page_intro(
        eyebrow="Benchmark Review",
        title="Trajectory Metrics",
        body="Inspect persisted trajectory metrics or trigger a fresh local comparison for one dataset, sequence, "
        "and artifact slice. Controls stay explicit so evaluation never runs as a side effect.",
    )
    metrics = context.state.metrics
    service = context.evaluation_service
    selectors_col, controls_col = st.columns((1.6, 1.0), gap="large")
    with selectors_col:
        with st.container(border=True):
            st.subheader("Benchmark Slice")
            datasets = list(DatasetId)
            dataset = st.selectbox("Dataset", datasets, index=datasets.index(metrics.dataset), format_func=lambda item: item.label)
            dataset_root = resolve_dataset_root(context.path_config, dataset)
            sequences = list_sequences(dataset=dataset, dataset_root=dataset_root)
            if not sequences:
                _save_state(context, dataset=dataset)
                st.warning(f"No local {dataset.label} sequences were found under `{dataset_root}`.")
                return
            sequence_index = sequences.index(metrics.sequence_slug) if metrics.sequence_slug in sequences else 0
            sequence_slug = st.selectbox("Sequence", options=sequences, index=sequence_index)
            runs = service.discover_runs(sequence_slug)
            if not runs:
                _save_state(context, dataset=dataset, sequence_slug=sequence_slug)
                st.info(f"No benchmark runs with `slam/trajectory.tum` were found under `{context.path_config.artifacts_dir}`.")
                return
            run_paths = [run.artifact_root for run in runs]
            run_index = run_paths.index(metrics.run_root) if metrics.run_root in run_paths else 0
            run = st.selectbox("Run", options=runs, index=run_index, format_func=lambda item: item.label)
    with controls_col:
        with st.container(border=True):
            st.subheader("Evaluation Controls")
            controls = _render_controls(metrics.evaluation)
            st.caption("Evaluation never runs on selector changes. Only the primary action below writes or refreshes persisted metric results.")
    _save_state(context, dataset=dataset, sequence_slug=sequence_slug, run_root=run.artifact_root, controls=controls, result_path=metrics.result_path)
    selection = build_selection(dataset=dataset, dataset_root=dataset_root, sequence_slug=sequence_slug, run=run)
    try:
        evaluation = service.load_evaluation(selection=selection, controls=controls)
    except EVALUATION_ERRORS as exc:
        st.error(str(exc))
        return

    can_compute = selection.reference_path is not None and selection.run.estimate_path.exists()
    with st.container(border=True):
        action_col, status_col = st.columns((0.9, 1.1), gap="large")
        compute = action_col.button("Compute metrics", type="primary", disabled=not can_compute, width="stretch")
        if selection.reference_path is None:
            status_col.warning("Missing `ground_truth.tum` for the selected sequence. The app only evaluates when a TUM reference trajectory already exists.")
        elif evaluation is not None:
            status_col.success(f"Loaded persisted result from `{evaluation.path}`.")
        else:
            status_col.info("No persisted result matches the current controls yet.")
    if compute:
        with st.spinner("Computing trajectory metrics..."):
            try:
                evaluation = service.compute_evaluation(selection=selection, controls=controls)
            except EVALUATION_ERRORS as exc:
                st.error(str(exc))
                return
        context.state.metrics.result_path = evaluation.path
        context.store.save(context.state)
        st.success(f"Persisted fresh metric result to `{evaluation.path}`.")
    if evaluation is None:
        _render_provenance(selection=selection, evaluation=None)
        return

    with st.container(border=True):
        for column, label, value in zip(
            st.columns(4, gap="small"),
            ("RMSE", "Mean", "Median", "Max"),
            (evaluation.stats.rmse, evaluation.stats.mean, evaluation.stats.median, evaluation.stats.max),
            strict=True,
        ):
            column.metric(label, f"{value:.4f}")
    figures_tab, provenance_tab = st.tabs(["Figures", "Provenance"])
    with figures_tab:
        figure_columns = st.columns((1.3, 1.0), gap="large")
        if evaluation.trajectories:
            figure_columns[0].plotly_chart(build_trajectory_figure(evaluation.trajectories), width="stretch")
        if evaluation.error_series is not None:
            figure_columns[1].plotly_chart(build_error_figure(evaluation.error_series), width="stretch")
    with provenance_tab:
        _render_provenance(selection=selection, evaluation=evaluation)


def _save_state(
    context: AppContext,
    *,
    dataset: DatasetId,
    sequence_slug: str | None = None,
    run_root: Path | None = None,
    controls: EvaluationControls | None = None,
    result_path: Path | None = None,
) -> None:
    metrics = context.state.metrics
    metrics.dataset = dataset
    metrics.sequence_slug = sequence_slug
    metrics.run_root = run_root
    metrics.evaluation = controls or EvaluationControls()
    metrics.result_path = result_path
    context.store.save(context.state)


def _render_controls(current: EvaluationControls) -> EvaluationControls:
    pose_options = list(PoseRelationId)
    pose_relation = st.selectbox("Pose Relation", pose_options, index=pose_options.index(current.pose_relation), format_func=lambda item: item.label)
    max_diff_s = st.number_input("Max timestamp diff (s)", min_value=0.0, step=0.01, format="%.3f", value=float(current.max_diff_s))
    return EvaluationControls(
        pose_relation=pose_relation,
        align=st.toggle("Rigid alignment", value=current.align),
        correct_scale=st.toggle("Scale correction", value=current.correct_scale),
        max_diff_s=float(max_diff_s),
    )


def _render_provenance(*, selection: SelectionSnapshot, evaluation: EvaluationArtifact | None) -> None:
    lines = [f"- Dataset: `{selection.dataset.label}`", f"- Sequence: `{selection.sequence_slug}`", f"- Run: `{selection.run.label}`", f"- Estimate path: `{selection.run.estimate_path}`", f"- Reference path: `{selection.reference_path}`"]
    if evaluation is not None:
        lines += [f"- Pose relation: `{evaluation.controls.pose_relation.label}`", f"- Alignment: `{evaluation.controls.align}`", f"- Scale correction: `{evaluation.controls.correct_scale}`", f"- Max timestamp diff (s): `{evaluation.controls.max_diff_s:.3f}`", f"- Matched pairs: `{evaluation.matched_pairs}`", f"- Persisted result: `{evaluation.path}`"]
    with st.container(border=True):
        st.subheader("Provenance")
        st.markdown("\n".join(lines))
# fmt: on
