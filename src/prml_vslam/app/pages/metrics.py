from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.eval.contracts import BenchmarkReference, EvaluationArtifact
from prml_vslam.plotting import build_error_figure, build_trajectory_figure
from prml_vslam.sources.datasets.contracts import DatasetId

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
        selection_state = context.evaluation_service.resolve_selection(
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
            index=selection_state.sequence_slugs.index(
                selection_state.sequence_slug or selection_state.sequence_slugs[0]
            ),
        )
        selection_state = context.evaluation_service.resolve_selection(
            dataset=dataset,
            preferred_sequence_slug=sequence_slug,
            preferred_run_root=metrics.run_root,
        )
        if not selection_state.runs or selection_state.selection is None:
            _save_state(context, dataset=dataset, sequence_slug=sequence_slug)
            st.info(
                f"No benchmark runs with `slam/trajectory.tum` were found under `{selection_state.artifacts_root}`."
            )
            st.caption("Start a bounded demo run from the `Pipeline` page or use the CLI planning flow first.")
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

    resolved = context.evaluation_service.resolve_selection(
        dataset=dataset,
        preferred_sequence_slug=sequence_slug,
        preferred_run_root=run.artifact_root,
    )
    selection = resolved.selection
    if selection is None:
        st.error("Could not resolve the selected benchmark slice.")
        return
    _save_state(context, dataset=dataset, sequence_slug=sequence_slug, run_root=selection.run.artifact_root)

    references = context.evaluation_service.discover_benchmark_references(selection.run.artifact_root)
    if not references:
        st.info(
            "No benchmark reference trajectories found in the run's `benchmark/` directory. "
            "Re-run with a dataset that provides reference trajectories."
        )
        return

    evaluations: dict[str, EvaluationArtifact | None] = {
        ref.source_key: _try_load(context, run=selection.run, reference=ref) for ref in references
    }
    missing = [ref for ref in references if evaluations[ref.source_key] is None]

    with st.container(border=True):
        action_col, status_col = st.columns((0.9, 1.1), gap="large")
        compute = action_col.button(
            "Compute missing" if missing else "Recompute all",
            type="primary",
            width="stretch",
        )
        if missing:
            status_col.info(f"{len(missing)} of {len(references)} source(s) not yet evaluated.")
        else:
            status_col.success(f"All {len(references)} reference source(s) have persisted results.")

    if compute:
        targets = missing if missing else references
        with st.spinner(f"Computing evo metrics for {len(targets)} reference(s)..."):
            for ref in targets:
                try:
                    evaluations[ref.source_key] = context.evaluation_service.compute_evaluation_for_source(
                        run=selection.run, reference=ref
                    )
                except EVALUATION_ERRORS as exc:
                    st.error(f"{ref.label}: {exc}")
        st.success("Evaluation complete.")

    loaded = [ref for ref in references if evaluations[ref.source_key] is not None]
    if loaded:
        with st.container(border=True):
            st.subheader("Comparison")
            _render_comparison_table(references, evaluations)

    for ref in references:
        evaluation = evaluations[ref.source_key]
        with st.expander(ref.label, expanded=evaluation is not None):
            if evaluation is None:
                st.info(f"No persisted result for **{ref.label}** yet. Use the compute button above.")
                continue
            _render_source_detail(evaluation)


def _try_load(
    context: AppContext,
    *,
    run: object,
    reference: BenchmarkReference,
) -> EvaluationArtifact | None:
    try:
        return context.evaluation_service.load_evaluation_for_source(run=run, reference=reference)
    except EVALUATION_ERRORS:
        return None


def _render_comparison_table(
    references: list[BenchmarkReference],
    evaluations: dict[str, EvaluationArtifact | None],
) -> None:
    import pandas as pd

    rows = []
    for ref in references:
        ev = evaluations.get(ref.source_key)
        rows.append(
            {
                "Source": ref.label,
                "RMSE (m)": round(ev.stats.rmse, 4) if ev else None,
                "Mean (m)": round(ev.stats.mean, 4) if ev else None,
                "Median (m)": round(ev.stats.median, 4) if ev else None,
                "Max (m)": round(ev.stats.max, 4) if ev else None,
                "Matched Pairs": ev.matched_pairs if ev else None,
            }
        )
    st.dataframe(pd.DataFrame(rows).set_index("Source"), use_container_width=True)


def _render_source_detail(evaluation: EvaluationArtifact) -> None:
    cols = st.columns(5, gap="small")
    labels = ("RMSE", "Mean", "Median", "Max", "Matched Pairs")
    values: tuple[float | int, ...] = (
        evaluation.stats.rmse,
        evaluation.stats.mean,
        evaluation.stats.median,
        evaluation.stats.max,
        evaluation.matched_pairs,
    )
    for col, label, value in zip(cols, labels, values, strict=True):
        col.metric(label, f"{value:.4f}" if isinstance(value, float) else str(value))
    figure_columns = st.columns((1.3, 1.0), gap="large")
    if evaluation.trajectories:
        figure_columns[0].plotly_chart(build_trajectory_figure(evaluation.trajectories), width="stretch")
    if evaluation.error_series is not None:
        figure_columns[1].plotly_chart(build_error_figure(evaluation.error_series), width="stretch")


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
