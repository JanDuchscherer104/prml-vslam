from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.eval.contracts import EvaluationArtifact, EvaluationSelection, SelectionSnapshot
from prml_vslam.plotting import build_error_figure, build_trajectory_figure

from ..state import save_model_updates
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext
EVALUATION_ERRORS = (FileNotFoundError, RuntimeError, ValueError)


def render(context: AppContext) -> None:
    render_page_intro(
        eyebrow="Benchmark Review",
        title="Trajectory Metrics",
        body="Inspect persisted trajectory metrics or trigger a fresh explicit `evo` APE evaluation for one "
        "dataset, sequence, and artifact slice. Evaluation stays explicit so metrics never run as a side effect.",
    )
    metrics = context.state.metrics
    with st.container(border=True):
        st.subheader("Benchmark Slice")
        datasets = list(DatasetId)
        dataset = st.selectbox(
            "Dataset", datasets, index=datasets.index(metrics.dataset), format_func=lambda item: item.label
        )
        selection_state = _resolve_selection(
            context,
            dataset=dataset,
            preferred_sequence_slug=metrics.sequence_slug,
            preferred_run_root=metrics.run_root,
        )
        if not selection_state.sequence_slugs:
            _save_state(context, dataset=dataset)
            st.warning(f"No local {dataset.label} sequences were found under `{selection_state.dataset_root}`.")
            return
        sequence_slug = st.selectbox(
            "Sequence",
            options=selection_state.sequence_slugs,
            index=selection_state.sequence_slugs.index(_selected_sequence_slug(selection_state)),
        )
        selection_state = _resolve_selection(
            context,
            dataset=dataset,
            preferred_sequence_slug=sequence_slug,
            preferred_run_root=metrics.run_root,
        )
        if not selection_state.runs or selection_state.selection is None:
            _save_state(context, dataset=dataset, sequence_slug=sequence_slug)
            st.info(
                f"No benchmark runs with `slam/trajectory.tum` were found under `{selection_state.artifacts_root}`."
            )
            return
        run = st.selectbox(
            "Run",
            options=selection_state.runs,
            index=selection_state.runs.index(selection_state.selection.run),
            format_func=lambda item: item.label,
        )
        st.caption(
            "The current repository-local evaluator exposes no extra runtime knobs. Use the compute action below to refresh the persisted `evo` result."
        )
    selection_state = _resolve_selection(
        context,
        dataset=dataset,
        preferred_sequence_slug=sequence_slug,
        preferred_run_root=run.artifact_root,
    )
    selection = selection_state.selection
    if selection is None:
        st.error("Could not resolve the selected benchmark slice.")
        return
    _save_state(
        context,
        dataset=dataset,
        sequence_slug=sequence_slug,
        run_root=selection.run.artifact_root,
        result_path=None,
    )
    try:
        evaluation = context.evaluation_service.load_evaluation(selection=selection)
    except EVALUATION_ERRORS as exc:
        st.error(str(exc))
        return
    _save_state(
        context,
        dataset=dataset,
        sequence_slug=selection.sequence_slug,
        run_root=selection.run.artifact_root,
        result_path=None if evaluation is None else evaluation.path,
    )

    can_compute = selection.reference_path is not None and selection.run.estimate_path.exists()
    with st.container(border=True):
        action_col, status_col = st.columns((0.9, 1.1), gap="large")
        compute = action_col.button("Compute evo metrics", type="primary", disabled=not can_compute, width="stretch")
        if selection.reference_path is None:
            status_col.warning(
                "Missing `ground_truth.tum` for the selected sequence. The app only evaluates when a TUM reference trajectory already exists."
            )
        elif evaluation is not None:
            status_col.success(f"Loaded persisted result from `{evaluation.path}`.")
        else:
            status_col.info("No persisted result matches the current controls yet.")
    if compute:
        with st.spinner("Computing evo trajectory metrics..."):
            try:
                evaluation = context.evaluation_service.compute_evaluation(selection=selection)
            except EVALUATION_ERRORS as exc:
                st.error(str(exc))
                return
        _save_state(
            context,
            dataset=dataset,
            sequence_slug=selection.sequence_slug,
            run_root=selection.run.artifact_root,
            result_path=evaluation.path,
        )
        st.success(f"Persisted fresh evo metric result to `{evaluation.path}`.")
    if evaluation is None:
        _render_provenance(dataset=dataset, selection=selection, evaluation=None)
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
        _render_provenance(dataset=dataset, selection=selection, evaluation=evaluation)


def _save_state(
    context: AppContext,
    *,
    dataset: DatasetId,
    sequence_slug: str | None = None,
    run_root: Path | None = None,
    result_path: Path | None = None,
) -> None:
    save_model_updates(
        context.store,
        context.state,
        context.state.metrics,
        dataset=dataset,
        sequence_slug=sequence_slug,
        run_root=run_root,
        result_path=result_path,
    )


def _resolve_selection(
    context: AppContext,
    *,
    dataset: DatasetId,
    preferred_sequence_slug: str | None,
    preferred_run_root: Path | None,
) -> EvaluationSelection:
    """Resolve dataset discovery and run selection through the evaluation service."""
    return context.evaluation_service.resolve_selection(
        dataset=dataset,
        preferred_sequence_slug=preferred_sequence_slug,
        preferred_run_root=preferred_run_root,
    )


def _selected_sequence_slug(selection_state: EvaluationSelection) -> str:
    """Return the current sequence selection or the first available sequence."""
    if selection_state.sequence_slug is not None:
        return selection_state.sequence_slug
    return selection_state.sequence_slugs[0]


def _render_provenance(
    *,
    dataset: DatasetId,
    selection: SelectionSnapshot,
    evaluation: EvaluationArtifact | None,
) -> None:
    lines = [
        f"- Dataset: `{dataset.label}`",
        f"- Sequence: `{selection.sequence_slug}`",
        f"- Run: `{selection.run.label}`",
        f"- Estimate path: `{selection.run.estimate_path}`",
        f"- Reference path: `{selection.reference_path}`",
    ]
    if evaluation is not None:
        lines += [
            f"- Matched pairs: `{evaluation.matched_pairs}`",
            f"- Persisted result: `{evaluation.path}`",
        ]
    with st.container(border=True):
        st.subheader("Provenance")
        st.markdown("\n".join(lines))
