"""Image-quality review page: render SLAM clouds and score them against input frames."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.eval.contracts import DiscoveredRun, ImageQualitySummary
from prml_vslam.eval.image_service import ImageQualityEvaluationService
from prml_vslam.eval.render_eval import RenderEvalConfig
from prml_vslam.sources.datasets.contracts import DatasetId

from ..state import save_model_updates
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext

_COMPUTE_ERRORS = (FileNotFoundError, RuntimeError, ValueError)
_GALLERY_LIMIT = 8


def render(context: AppContext) -> None:
    render_page_intro(
        eyebrow="Benchmark Review",
        title="Image Quality",
        body="Render each run's dense SLAM cloud from its estimated trajectory and score the synthetic views "
        "against the captured input frames (masked L1/L2/PSNR/SSIM). Rendering is explicit — trigger it below.",
    )
    state = context.state.image_quality
    service = ImageQualityEvaluationService(context.path_config)

    with st.container(border=True):
        st.subheader("Benchmark Slice")
        datasets = list(DatasetId)
        dataset = st.selectbox(
            "Dataset", datasets, index=datasets.index(state.dataset), format_func=lambda item: item.label
        )
        selection_state = context.evaluation_service.resolve_selection(
            dataset=dataset, preferred_sequence_slug=state.sequence_slug, preferred_run_root=state.run_root
        )
        if not selection_state.sequence_slugs:
            _save(context, dataset=dataset)
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
            dataset=dataset, preferred_sequence_slug=sequence_slug, preferred_run_root=state.run_root
        )
        if not selection_state.runs or selection_state.selection is None:
            _save(context, dataset=dataset, sequence_slug=sequence_slug)
            st.info(f"No runs with `slam/trajectory.tum` were found under `{selection_state.artifacts_root}`.")
            st.caption("Start a run from the `Pipeline` page or the CLI first.")
            return
        run = st.selectbox(
            "Run",
            options=selection_state.runs,
            index=selection_state.runs.index(selection_state.selection.run),
            format_func=lambda item: item.label,
        )
        gallery_every = int(
            st.number_input("Gallery: keep every Nth scored pair", min_value=1, value=int(state.gallery_every), step=1)
        )

    _save(
        context, dataset=dataset, sequence_slug=sequence_slug, run_root=run.artifact_root, gallery_every=gallery_every
    )

    summaries = {candidate.artifact_root: _try_load(service, candidate) for candidate in selection_state.runs}
    if any(summary is not None for summary in summaries.values()):
        with st.container(border=True):
            st.subheader("Method Comparison")
            _render_comparison(selection_state.runs, summaries)

    summary = summaries.get(run.artifact_root)
    with st.container(border=True):
        st.subheader(run.label)
        action_col, status_col = st.columns((0.9, 1.1), gap="large")
        compute = action_col.button(
            "Recompute" if summary is not None else "Render & score",
            type="primary",
            width="stretch",
        )
        if summary is None:
            status_col.info("Not yet rendered and scored for this run.")
        else:
            status_col.success(f"{summary.pair_count} scored pair(s) · mean coverage {summary.mean_coverage:.0%}")

    if compute:
        with st.spinner("Rendering dense cloud and scoring image quality (this can take minutes)..."):
            try:
                summary = service.evaluate_run(
                    run.artifact_root, config=RenderEvalConfig(gallery_every=gallery_every)
                ).summary
            except _COMPUTE_ERRORS as exc:
                st.error(str(exc))
                summary = None
        if summary is not None:
            st.success("Image evaluation complete.")

    if summary is None:
        st.info("Render and score this run to see metrics and the side-by-side gallery.")
        return

    _render_summary(summary)
    _render_gallery(run.artifact_root)


def _try_load(service: ImageQualityEvaluationService, run: DiscoveredRun) -> ImageQualitySummary | None:
    try:
        return service.load(run.artifact_root)
    except _COMPUTE_ERRORS:
        return None


def _render_comparison(runs: list[DiscoveredRun], summaries: dict[Path, ImageQualitySummary | None]) -> None:
    rows = [
        {
            "Run": run.label,
            "Pairs": summary.pair_count if summary else None,
            "Coverage": round(summary.mean_coverage, 3) if summary else None,
            "PSNR": round(summary.stats["image.psnr"].mean, 3) if summary else None,
            "SSIM": round(summary.stats["image.ssim"].mean, 4) if summary else None,
            "L1": round(summary.stats["image.l1"].mean, 4) if summary else None,
        }
        for run in runs
        for summary in (summaries.get(run.artifact_root),)
    ]
    st.dataframe(rows, width="stretch")


def _render_summary(summary: ImageQualitySummary) -> None:
    headline = st.columns(3, gap="small")
    headline[0].metric("PSNR (mean)", f"{summary.stats['image.psnr'].mean:.2f} dB")
    headline[1].metric("SSIM (mean)", f"{summary.stats['image.ssim'].mean:.3f}")
    headline[2].metric("Coverage", f"{summary.mean_coverage:.0%}")
    st.dataframe(
        [
            {
                "Metric": metric_id,
                "Mean": round(stats.mean, 4),
                "Median": round(stats.median, 4),
                "Min": round(stats.min, 4),
                "Max": round(stats.max, 4),
            }
            for metric_id, stats in summary.stats.items()
        ],
        width="stretch",
    )
    if summary.frames:
        st.caption("Per-frame quality")
        chart_cols = st.columns(2, gap="large")
        chart_cols[0].line_chart({"PSNR (dB)": [frame.psnr for frame in summary.frames]})
        chart_cols[1].line_chart({"SSIM": [frame.ssim for frame in summary.frames]})


def _render_gallery(run_root: Path, *, limit: int = _GALLERY_LIMIT) -> None:
    gallery_dir = run_root / "evaluation" / "render_eval" / "side_by_side"
    images = sorted(gallery_dir.glob("*.png")) if gallery_dir.exists() else []
    if not images:
        st.caption("No gallery images were written for this run (compute with the gallery enabled).")
        return
    st.subheader("Gallery — left: ground truth · right: rendered")
    shown = images[:limit]
    for row_start in range(0, len(shown), 2):
        columns = st.columns(2, gap="medium")
        for column, image_path in zip(columns, shown[row_start : row_start + 2], strict=False):
            column.image(str(image_path), caption=image_path.name, width="stretch")
    if len(images) > limit:
        st.caption(f"Showing {limit} of {len(images)} pairs from `{gallery_dir}`.")


def _save(context: AppContext, **updates: object) -> None:
    save_model_updates(context.store, context.state, context.state.image_quality, **updates)


__all__ = ["render"]
