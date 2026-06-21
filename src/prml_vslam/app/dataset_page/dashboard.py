"""Dashboard panels for normalized dataset snapshots."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import prml_vslam.plotting as plots
from prml_vslam.plotting.datasets import (
    build_observation_metric_figure,
    build_payload_footprint_figure,
    build_trajectory_metric_figure,
)
from prml_vslam.sources.datasets.advio import AdvioLocalSceneStatus
from prml_vslam.sources.datasets.contracts import DatasetSummary
from prml_vslam.sources.datasets.normalized_query import NormalizedDatasetQuery


def render_dataset_dashboard(
    *,
    normalized: NormalizedDatasetQuery,
    summary: DatasetSummary,
    key_prefix: str,
    advio_statuses: list[AdvioLocalSceneStatus] | None,
) -> None:
    """Render normalized-store dashboard charts for one dataset."""
    render_dashboard_metrics(normalized=normalized, summary=summary)
    if normalized.issues:
        st.warning(
            f"{len(normalized.issues)} normalized entr{'y' if len(normalized.issues) == 1 else 'ies'} need rebuild or attention."
        )
    if advio_statuses is not None:
        render_advio_catalog_overview(advio_statuses)
    footprint = normalized.payload_footprint_frame()
    if not footprint.empty:
        st.plotly_chart(
            build_payload_footprint_figure(footprint),
            width="stretch",
            key=f"{key_prefix}:payload-footprint",
        )
    observation_summary = normalized.observation_summary_frame()
    if not observation_summary.empty:
        st.subheader("Observation Statistics")
        first_row = st.columns(2, gap="large")
        first_row[0].plotly_chart(
            build_observation_metric_figure(
                observation_summary,
                value_column="observation_frame_count",
                title="Stored Frames per Scene",
                yaxis_title="Frames",
            ),
            width="stretch",
            key=f"{key_prefix}:observation-frames",
        )
        first_row[1].plotly_chart(
            build_observation_metric_figure(
                observation_summary,
                value_column="observation_duration_s",
                title="Observation Duration per Scene",
                yaxis_title="Duration (s)",
            ),
            width="stretch",
            key=f"{key_prefix}:observation-duration",
        )
        with st.expander("Observation summary table", expanded=False):
            st.dataframe(compact_dashboard_frame(observation_summary), hide_index=True, width="stretch")
    trajectory_summary = normalized.trajectory_summary_frame()
    if not trajectory_summary.empty:
        trajectory_chart_frame = trajectory_dashboard_chart_frame(trajectory_summary)
        st.subheader("Trajectory Statistics")
        trajectory_row = st.columns(2, gap="large")
        trajectory_row[0].plotly_chart(
            build_trajectory_metric_figure(
                trajectory_chart_frame,
                value_column="trajectory_path_length_m",
                title="Trajectory Path Length per Scene",
                yaxis_title="Path Length (m)",
            ),
            width="stretch",
            key=f"{key_prefix}:trajectory-path-length",
        )
        trajectory_row[1].plotly_chart(
            build_trajectory_metric_figure(
                trajectory_chart_frame,
                value_column="trajectory_mean_speed_m_s",
                title="Mean Speed per Scene",
                yaxis_title="Mean Speed (m/s)",
            ),
            width="stretch",
            key=f"{key_prefix}:trajectory-speed",
        )
        st.plotly_chart(
            build_trajectory_metric_figure(
                trajectory_chart_frame,
                value_column="trajectory_mean_curvature_rad_m",
                title="Mean Curvature per Scene",
                yaxis_title="Mean Curvature (rad/m)",
            ),
            width="stretch",
            key=f"{key_prefix}:trajectory-curvature",
        )
        with st.expander("Trajectory summary table", expanded=False):
            st.dataframe(compact_dashboard_frame(trajectory_summary), hide_index=True, width="stretch")


def trajectory_dashboard_chart_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Select one row per sequence and trajectory subject for dashboard charts."""
    if frame.empty or not {"sequence_id", "subject"}.issubset(frame.columns):
        return frame
    if "scope" not in frame:
        return frame.drop_duplicates(subset=["sequence_id", "subject"], keep="first").reset_index(drop=True)
    priority = frame["scope"].astype(str).map({"reference_trajectory": 0, "candidate_trajectory": 1}).fillna(2)
    selected = (
        frame.assign(_scope_priority=priority)
        .sort_values(["sequence_id", "subject", "_scope_priority"], kind="stable")
        .drop_duplicates(subset=["sequence_id", "subject"], keep="first")
        .drop(columns=["_scope_priority"])
    )
    return selected.reset_index(drop=True)


def compact_dashboard_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return compact columns for dashboard detail tables."""
    columns = [
        column
        for column in (
            "dataset_id",
            "sequence_id",
            "profile_key",
            "scope",
            "subject",
            "observation_frame_count",
            "observation_duration_s",
            "observation_mean_fps",
            "rgb_frame_count",
            "depth_frame_count",
            "trajectory_path_length_m",
            "trajectory_duration_s",
            "trajectory_mean_curvature_rad_m",
            "trajectory_mean_speed_m_s",
        )
        if column in frame
    ]
    return frame.loc[:, columns] if columns else frame


def render_dashboard_metrics(*, normalized: NormalizedDatasetQuery, summary: DatasetSummary) -> None:
    """Render top-level normalized-store and download-cache metrics."""
    footprint = normalized.payload_footprint_frame()
    total_mb = 0.0 if footprint.empty else float(pd.to_numeric(footprint["Total MB"], errors="coerce").sum())
    sequence_count = len(normalized.sequence_ids)
    average_mb = 0.0 if sequence_count == 0 else total_mb / sequence_count
    columns = st.columns(5, gap="small")
    for column, (label, value) in zip(
        columns,
        (
            ("Normalized Scenes", str(sequence_count)),
            ("Catalog Scenes", str(summary.total_scene_count)),
            ("Store Size", f"{total_mb:.1f} MB"),
            ("Avg Scene Footprint", f"{average_mb:.1f} MB"),
            ("Issues", str(len(normalized.issues))),
        ),
        strict=True,
    ):
        column.metric(label, value)
    cache_columns = st.columns(2, gap="small")
    cache_columns[0].metric("Downloaded Cache", str(summary.local_scene_count))
    cache_columns[1].metric("Cached Archives", str(summary.cached_archive_count))


def render_advio_catalog_overview(statuses: list[AdvioLocalSceneStatus]) -> None:
    """Render ADVIO-specific catalog composition charts."""
    st.subheader("ADVIO Catalog Metadata")
    figure_rows = (
        (plots.build_scene_mix_figure(statuses), plots.build_local_readiness_figure(statuses)),
        (plots.build_crowd_density_figure(statuses), plots.build_scene_attribute_figure(statuses)),
    )
    for row_index, figures in enumerate(figure_rows):
        for column_index, (column, figure) in enumerate(zip(st.columns(2, gap="large"), figures, strict=True)):
            column.plotly_chart(figure, width="stretch", key=f"advio-catalog:{row_index}:{column_index}")
