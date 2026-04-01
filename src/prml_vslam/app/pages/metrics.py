"""Metrics-first trajectory evaluation page."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.eval import PoseRelationId

from ..models import DatasetId, EvaluationControls, MetricsPageState
from ..plotting import build_metric_summary_figure, build_trajectory_overlay_figure
from ..ui import render_header, render_key_value_rows, render_path_cards

if TYPE_CHECKING:
    from ..bootstrap import AppContext


def render(context: AppContext) -> None:
    """Render the trajectory metrics page."""
    render_header(
        title="Trajectory Metrics",
        kicker="Metrics-first app",
        copy=(
            "Review persisted evo outputs, inspect run provenance, and trigger explicit trajectory "
            "evaluation for one dataset sequence and run."
        ),
    )

    service = context.services.evaluation
    state = context.state
    paths = context.services.path_config

    with st.expander("Configured paths", expanded=False):
        render_path_cards(
            [
                ("ADVIO root", paths.advio_root),
                ("Artifacts root", paths.artifacts_root),
            ]
        )

    dataset = DatasetId.ADVIO
    sequence_ids = service.list_sequences(dataset)
    selected_sequence_id = _resolve_sequence_id(state.metrics.sequence_id, sequence_ids)
    runs = service.discover_runs(dataset, selected_sequence_id) if selected_sequence_id is not None else []
    selected_run = _resolve_run(state.metrics.run_path, runs)

    with st.container(border=True):
        selector_col, sequence_col, run_col = st.columns([0.8, 0.8, 1.4], gap="large")
        selector_col.selectbox("Dataset", options=[dataset], format_func=lambda item: item.label, disabled=True)
        if sequence_ids:
            selected_sequence_id = sequence_col.selectbox(
                "Sequence",
                options=sequence_ids,
                index=sequence_ids.index(selected_sequence_id) if selected_sequence_id is not None else 0,
                format_func=lambda item: f"ADVIO {item:02d}",
            )
        else:
            sequence_col.selectbox("Sequence", options=["No local ADVIO sequences"], disabled=True)
            selected_sequence_id = None

        if runs:
            selected_run = run_col.selectbox(
                "Method / run",
                options=runs,
                index=runs.index(selected_run) if selected_run is not None else 0,
                format_func=lambda item: item.display_label,
            )
        else:
            run_col.selectbox("Method / run", options=["No trajectory runs discovered"], disabled=True)
            selected_run = None

    controls_col, toggles_col, detail_col = st.columns([1.1, 1.0, 0.9], gap="large")
    selected_pose_relation = controls_col.selectbox(
        "Pose relation",
        options=list(PoseRelationId),
        index=list(PoseRelationId).index(state.metrics.evaluation.pose_relation),
        format_func=lambda item: item.value.replace("_", " "),
    )
    align = toggles_col.toggle("Align", value=state.metrics.evaluation.align)
    correct_scale = toggles_col.toggle("Correct scale", value=state.metrics.evaluation.correct_scale)
    max_diff_s = float(
        detail_col.number_input(
            "Max timestamp diff (s)",
            min_value=0.001,
            max_value=1.0,
            value=float(state.metrics.evaluation.max_diff_s),
            step=0.001,
            format="%.3f",
        )
    )

    state.metrics = MetricsPageState(
        dataset=dataset,
        sequence_id=selected_sequence_id,
        run_path=selected_run.artifact_root if selected_run is not None else None,
        evaluation=EvaluationControls(
            pose_relation=selected_pose_relation,
            align=align,
            correct_scale=correct_scale,
            max_diff_s=max_diff_s,
        ),
        last_result_path=state.metrics.last_result_path,
    )
    context.store.save(state)

    if not sequence_ids:
        st.warning(f"No local ADVIO sequences were found under {paths.advio_root}.")
        return

    if selected_run is None:
        st.info(
            "No trajectory-producing runs were discovered for the selected sequence. Materialize or run a benchmark "
            "first, then return here to inspect or evaluate it."
        )
        return

    selection = service.resolve_metrics_selection(
        dataset=dataset,
        sequence_id=selected_sequence_id,
        run_path=selected_run.artifact_root,
    )
    if selection is None:
        st.warning("Could not resolve the current dataset-sequence-run selection.")
        return

    matching_evaluation = service.find_matching_evaluation(selection=selection, controls=state.metrics.evaluation)
    all_evaluations = service.list_persisted_evaluations(selection)

    compute_disabled = selection.reference_path is None and selection.reference_csv_path is None
    compute_help = None
    if compute_disabled:
        compute_help = "No reference trajectory is available for the selected sequence."

    compute_requested = st.button(
        "Compute evo metrics",
        type="primary",
        disabled=compute_disabled,
        help=compute_help,
    )

    if compute_requested:
        try:
            with st.status("Running evo trajectory evaluation...", expanded=False):
                matching_evaluation = service.compute_evaluation(selection=selection, controls=state.metrics.evaluation)
        except Exception as exc:
            st.error(str(exc))
        else:
            state.metrics.last_result_path = matching_evaluation.path
            context.store.save(state)
            st.success(f"Saved evaluation to {matching_evaluation.path}.")

    if matching_evaluation is None:
        st.info("No persisted evaluation matches the current controls yet. Use the compute action to generate one.")
        if all_evaluations:
            st.markdown("### Available persisted evaluations")
            render_key_value_rows(
                [
                    {
                        "path": evaluation.path.as_posix(),
                        "pose_relation": evaluation.result.pose_relation.value,
                        "align": evaluation.result.align,
                        "correct_scale": evaluation.result.correct_scale,
                        "matching_pairs": evaluation.result.matching_pairs,
                    }
                    for evaluation in all_evaluations
                ]
            )
        return

    st.caption(f"Showing persisted evaluation: `{matching_evaluation.path}`")
    _render_result(selection=selection, evaluation=matching_evaluation, service=service)


def _resolve_sequence_id(current_value: int | None, sequence_ids: list[int]) -> int | None:
    if current_value in sequence_ids:
        return current_value
    return sequence_ids[0] if sequence_ids else None


def _resolve_run(current_path, runs):
    if current_path is not None:
        for run in runs:
            if run.artifact_root == current_path:
                return run
    return runs[0] if runs else None


def _render_result(*, selection, evaluation, service) -> None:
    result = evaluation.result
    stat_names = ["rmse", "mean", "median"]
    metric_values = [result.stats.get(name) for name in stat_names]
    metric_pairs = [("RMSE", metric_values[0]), ("Mean", metric_values[1]), ("Median", metric_values[2])]
    metric_pairs.append(("Pairs", float(result.matching_pairs)))

    metric_cols = st.columns(4)
    for column, (label, value) in zip(metric_cols, metric_pairs, strict=True):
        if value is None:
            column.metric(label, "n/a")
        elif label == "Pairs":
            column.metric(label, int(value))
        else:
            column.metric(label, f"{value:.6f}")

    provenance_rows = [
        {"field": "Dataset", "value": selection.dataset.label},
        {"field": "Sequence", "value": selection.sequence_name},
        {"field": "Mode", "value": selection.run.mode.value},
        {"field": "Method", "value": selection.run.method.value},
        {"field": "Pose relation", "value": result.pose_relation.value},
        {"field": "Align", "value": result.align},
        {"field": "Correct scale", "value": result.correct_scale},
        {"field": "Max diff (s)", "value": result.max_diff_s},
        {"field": "Reference path", "value": result.reference_path.as_posix()},
        {"field": "Estimate path", "value": result.estimate_path.as_posix()},
    ]
    st.markdown("### Provenance")
    render_key_value_rows(provenance_rows)

    chart_col, stats_col = st.columns([1.1, 0.9], gap="large")
    with chart_col:
        st.markdown("### Metric summary")
        st.plotly_chart(build_metric_summary_figure(result), width="stretch", config={"displayModeBar": False})
    with stats_col:
        st.markdown("### Raw stats")
        render_key_value_rows(
            [{"metric": name, "value": value} for name, value in sorted(result.stats.items(), key=lambda item: item[0])]
        )

    if result.reference_path.exists() and result.estimate_path.exists():
        reference_points = service.load_trajectory_points(result.reference_path)
        estimate_points = service.load_trajectory_points(result.estimate_path)
        if reference_points and estimate_points:
            st.markdown("### Trajectory overlay")
            st.plotly_chart(
                build_trajectory_overlay_figure(
                    reference_points=reference_points,
                    estimate_points=estimate_points,
                    title=f"{selection.sequence_name} · {selection.run.method.value.replace('_', ' ').upper()}",
                ),
                width="stretch",
                config={"displayModeBar": False},
            )


__all__ = ["render"]
