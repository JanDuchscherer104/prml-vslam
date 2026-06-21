"""Scene explorer and artifact visualization for normalized datasets."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

import prml_vslam.plotting as plots
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.datasets.normalized_query import NormalizedDatasetQuery, NormalizedSequenceRecord

from ..models import AdvioPageState, Record3DDatasetPageState, TumRgbdPageState
from ..state import save_model_updates
from .dashboard import compact_dashboard_frame
from .query import (
    build_reference_cloud_scene_figure_cached,
    load_scene_trajectory_series,
    reference_cloud_artifact_cache_key,
    trajectory_artifact_cache_key,
)

if TYPE_CHECKING:
    from ..bootstrap import AppContext


DatasetExplorerState = AdvioPageState | TumRgbdPageState | Record3DDatasetPageState


def render_scene_tab(
    *,
    context: AppContext,
    normalized: NormalizedDatasetQuery,
    page_state: DatasetExplorerState,
    dataset_label: str,
    key_prefix: str,
) -> None:
    """Render the normalized scene explorer, metrics, and artifacts."""
    selected_id = render_sequence_explorer(
        context=context,
        records=normalized.scene_sequence_records(),
        all_records=normalized.records,
        page_state=page_state,
        dataset_label=dataset_label,
        key_prefix=key_prefix,
    )
    if selected_id is None:
        return
    profile_key = render_scene_profile_selector(
        normalized=normalized,
        sequence_id=selected_id,
        key_prefix=key_prefix,
    )
    render_scene_statistics(normalized=normalized, sequence_id=selected_id, profile_key=profile_key)
    render_scene_trajectories(
        normalized=normalized,
        sequence_id=selected_id,
        profile_key=profile_key,
        key_prefix=key_prefix,
    )


def render_scene_profile_selector(
    *,
    normalized: NormalizedDatasetQuery,
    sequence_id: str,
    key_prefix: str,
) -> str | None:
    """Select one normalized profile for the chosen scene."""
    records = normalized.records_for_sequence(sequence_id=sequence_id)
    if not records:
        return None
    preferred = normalized.preferred_profile_key(sequence_id=sequence_id)
    profile_keys = [record.profile_key for record in records]
    selected_profile = st.selectbox(
        "Profile",
        options=profile_keys,
        index=profile_keys.index(preferred) if preferred in profile_keys else 0,
        format_func=lambda profile_key: profile_label(records, str(profile_key)),
        key=f"{key_prefix}:profile",
    )
    return str(selected_profile)


def profile_label(records: list[NormalizedSequenceRecord], profile_key: str) -> str:
    """Return the visible profile label for a normalized record."""
    record = next((item for item in records if item.profile_key == profile_key), None)
    if record is None:
        return profile_key
    suffix = "default" if record.is_default_profile else "profile"
    return f"{profile_key} ({suffix})"


def render_scene_statistics(*, normalized: NormalizedDatasetQuery, sequence_id: str, profile_key: str | None) -> None:
    """Render scene metrics without collapsing multiple trajectories into one unlabeled row."""
    observation = first_scene_row(
        normalized.observation_summary_frame(sequence_id=sequence_id, profile_key=profile_key),
        sequence_id=sequence_id,
    )
    metrics = (
        ("Frames", row_value(observation, "observation_frame_count")),
        ("Duration", format_number(row_value(observation, "observation_duration_s"), suffix=" s")),
        ("Mean FPS", format_number(row_value(observation, "observation_mean_fps"))),
    )
    for column, (label, value) in zip(st.columns(3, gap="small"), metrics, strict=True):
        column.metric(label, value or "n/a")

    trajectory_frame = normalized.trajectory_summary_frame(sequence_id=sequence_id, profile_key=profile_key)
    if not trajectory_frame.empty:
        st.subheader("Trajectory Metrics")
        st.dataframe(scene_trajectory_table_frame(trajectory_frame), hide_index=True, width="stretch")


def scene_trajectory_table_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a deterministic subject/scope-qualified scene trajectory table."""
    compact = compact_dashboard_frame(frame)
    if compact.empty or not {"scope", "subject"}.issubset(compact.columns):
        return compact
    priority = compact["scope"].astype(str).map({"reference_trajectory": 0, "candidate_trajectory": 1}).fillna(2)
    return (
        compact.assign(_scope_priority=priority)
        .sort_values(["_scope_priority", "subject"], kind="stable")
        .drop(columns=["_scope_priority"])
        .reset_index(drop=True)
    )


def render_scene_trajectories(
    *,
    normalized: NormalizedDatasetQuery,
    sequence_id: str,
    profile_key: str | None,
    key_prefix: str,
) -> None:
    """Render normalized trajectory and reference-cloud artifacts for one scene."""
    trajectory_artifacts = normalized.trajectory_artifacts(sequence_id=sequence_id, profile_key=profile_key)
    trajectory_key = trajectory_artifact_cache_key(trajectory_artifacts)
    trajectories = load_scene_trajectory_series(trajectory_key)
    if not trajectories:
        st.info("No normalized trajectory artifact is available for this scene.")
    else:
        st.subheader("Trajectory")
        columns = st.columns(2, gap="large")
        columns[0].plotly_chart(
            plots.build_bev_trajectory_figure(trajectories, plane_axes=scene_bev_axes(normalized.dataset_id)),
            width="stretch",
            key=f"{key_prefix}:bev-trajectory",
        )
        columns[1].plotly_chart(
            plots.build_3d_trajectory_figure(trajectories),
            width="stretch",
            key=f"{key_prefix}:3d-trajectory",
        )
    clouds = normalized.reference_cloud_artifacts(sequence_id=sequence_id, profile_key=profile_key)
    if clouds:
        st.subheader("Reference Cloud")
        st.dataframe(
            [
                {
                    "Cloud": cloud.label,
                    "Path": cloud.path.as_posix(),
                    "Metadata": cloud.metadata_path.as_posix(),
                }
                for cloud in clouds
            ],
            hide_index=True,
            width="stretch",
        )
        if st.button("Load reference cloud", key=f"{key_prefix}:load-reference-cloud"):
            st.plotly_chart(
                build_reference_cloud_scene_figure_cached(
                    reference_cloud_artifact_cache_key(clouds),
                    trajectory_key,
                ),
                width="stretch",
                key=f"{key_prefix}:reference-cloud",
            )


def scene_bev_axes(dataset_id: DatasetId) -> tuple[int, int]:
    """Return the bird's-eye plane axes for one dataset's canonical frame."""
    return (0, 2) if dataset_id is DatasetId.ADVIO else (0, 1)


def first_scene_row(frame: pd.DataFrame, *, sequence_id: str) -> pd.Series | None:
    """Return the first row for a sequence from a single-subject frame."""
    if frame.empty or "sequence_id" not in frame:
        return None
    selected = frame.loc[frame["sequence_id"].astype(str).eq(sequence_id)]
    return None if selected.empty else selected.iloc[0]


def row_value(row: pd.Series | None, key: str) -> str:
    """Return a string metric value from one optional frame row."""
    if row is None or key not in row:
        return ""
    value = row[key]
    return "" if value is None else str(value)


def format_number(value: str, *, suffix: str = "") -> str:
    """Format a numeric string for compact metric display."""
    if not value:
        return ""
    try:
        return f"{float(value):.2f}{suffix}"
    except ValueError:
        return value


def render_sequence_explorer(
    *,
    context: AppContext,
    records: list[NormalizedSequenceRecord],
    all_records: list[NormalizedSequenceRecord],
    page_state: DatasetExplorerState,
    dataset_label: str,
    key_prefix: str,
) -> str | None:
    """Render scene selection and profile inventory for a normalized dataset."""
    sequence_ids = [record.sequence_id for record in records]
    with st.container(border=True):
        st.subheader("Sequence Explorer")
        if not sequence_ids:
            st.info(f"Build at least one normalized {dataset_label} entry to unlock sequence statistics.")
            return None
        selected_id = (
            page_state.explorer_sequence_id if page_state.explorer_sequence_id in sequence_ids else sequence_ids[0]
        )
        selected_id = st.selectbox(
            "Normalized Scene",
            options=sequence_ids,
            index=sequence_ids.index(selected_id),
            format_func=lambda sequence_id: next(
                record.sequence_label for record in records if record.sequence_id == sequence_id
            ),
            key=f"{key_prefix}:scene",
        )
        save_model_updates(context.store, context.state, page_state, explorer_sequence_id=selected_id)
        selected_records = [record for record in all_records if record.sequence_id == selected_id]
        st.dataframe(
            [
                {
                    "Profile": record.profile_key,
                    "Default Profile": record.is_default_profile,
                    "Stats Rows": record.stats_row_count,
                    "Metadata Rows": record.metadata_row_count,
                    "Root": record.root.as_posix(),
                }
                for record in selected_records
            ],
            hide_index=True,
            width="stretch",
        )
        return selected_id
