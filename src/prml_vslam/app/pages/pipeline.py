"""Streamlit page for the runnable ADVIO pipeline demo."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import streamlit as st
from evo.core import metrics as evo_metrics
from evo.core import sync as evo_sync
from evo.core.trajectory import PoseTrajectory3D

from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.eval.contracts import ErrorSeries, MetricStats, TrajectorySeries
from prml_vslam.interfaces import TimedPoseTrajectory
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunPlan
from prml_vslam.pipeline.contracts import StageManifest
from prml_vslam.pipeline.session import PipelineSessionSnapshot, PipelineSessionState
from prml_vslam.plotting import build_evo_ape_colormap_figure
from prml_vslam.utils import BaseData
from prml_vslam.utils.geometry import load_tum_trajectory

from ..image_utils import normalize_grayscale_image
from ..live_session import (
    LiveMetric,
    render_camera_intrinsics,
    render_live_fragment,
    render_live_session_shell,
    render_live_trajectory,
)
from ..pipeline_demo import start_advio_demo_run
from ..state import save_model_updates
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


_ACTIVE_SESSION_STATES = frozenset({PipelineSessionState.CONNECTING, PipelineSessionState.RUNNING})
_EVO_ASSOCIATION_MAX_DIFF_S = 0.01


class PipelinePageAction(BaseData):
    """Typed action payload for the pipeline page form and buttons."""

    sequence_id: int
    """Selected ADVIO sequence id."""

    mode: PipelineMode
    """Selected pipeline mode."""

    method: MethodId
    """Selected mock SLAM backend label."""

    pose_source: AdvioPoseSource
    """Selected pose source for the ADVIO replay stream."""

    respect_video_rotation: bool = False
    """Whether the replay should honor video rotation metadata."""

    start_requested: bool = False
    """Whether the user requested a new run."""

    stop_requested: bool = False
    """Whether the user requested the current run to stop."""


class PipelineEvoPreview(BaseData):
    """`evo` APE payload rendered by the pipeline-demo trajectory tab."""

    reference: TrajectorySeries
    estimate: TrajectorySeries
    error_series: ErrorSeries
    stats: MetricStats


def render(context: AppContext) -> None:
    """Render the interactive ADVIO replay demo."""
    render_page_intro(
        eyebrow="Streaming Surface",
        title="Pipeline Demo",
        body=(
            "Run the bounded ADVIO replay demo through the repository-local mock SLAM backend "
            "and monitor frames, trajectory, planned stages, and written artifacts."
        ),
    )
    statuses = context.advio_service.local_scene_statuses()
    previewable_ids = [status.scene.sequence_id for status in statuses if status.replay_ready]
    snapshot = context.pipeline_runtime.snapshot()
    is_active = snapshot.state in _ACTIVE_SESSION_STATES
    with st.container(border=True):
        st.subheader("ADVIO Replay Demo")
        st.caption(
            "Use one replay-ready ADVIO scene as a bounded offline or looped streaming session for the current pipeline demo."
        )
        if not previewable_ids:
            st.info(
                "Download the ADVIO streaming bundle for at least one scene to unlock the interactive pipeline demo."
            )
            return
        page_state = context.state.pipeline
        selected_sequence_id = (
            page_state.sequence_id if page_state.sequence_id in previewable_ids else previewable_ids[0]
        )
        with st.form("pipeline_demo_form", border=False):
            selected_sequence_id = st.selectbox(
                "ADVIO Scene",
                options=previewable_ids,
                index=previewable_ids.index(selected_sequence_id),
                format_func=lambda sequence_id: context.advio_service.scene(sequence_id).display_name,
            )
            left, right = st.columns(2, gap="large")
            with left:
                mode = st.selectbox(
                    "Mode",
                    options=list(PipelineMode),
                    index=list(PipelineMode).index(page_state.mode),
                    format_func=lambda item: item.label,
                )
                method = st.selectbox(
                    "Mock Method",
                    options=list(MethodId),
                    index=list(MethodId).index(page_state.method),
                    format_func=lambda item: item.display_name,
                )
            with right:
                pose_source = st.selectbox(
                    "Pose Source",
                    options=list(AdvioPoseSource),
                    index=list(AdvioPoseSource).index(page_state.pose_source),
                    format_func=lambda item: item.label,
                )
                respect_video_rotation = st.toggle(
                    "Respect video rotation metadata",
                    value=page_state.respect_video_rotation,
                )
            start_requested = st.form_submit_button(
                "Start run" if not is_active else "Restart run",
                type="primary",
                use_container_width=True,
            )
        stop_requested = st.button("Stop run", disabled=not is_active, use_container_width=True)
        error_message = _handle_pipeline_page_action(
            context=context,
            action=PipelinePageAction(
                sequence_id=selected_sequence_id,
                mode=mode,
                method=method,
                pose_source=pose_source,
                respect_video_rotation=respect_video_rotation,
                start_requested=start_requested,
                stop_requested=stop_requested,
            ),
        )
        snapshot = context.pipeline_runtime.snapshot()
        if error_message:
            st.error(error_message)
        render_live_fragment(
            run_every=0.2 if snapshot.state in _ACTIVE_SESSION_STATES else None,
            render_body=lambda: _render_pipeline_snapshot(context.pipeline_runtime.snapshot()),
        )


def _render_pipeline_snapshot(snapshot: PipelineSessionSnapshot) -> None:
    render_live_session_shell(
        title=None,
        status_renderer=lambda: _render_pipeline_notice(snapshot),
        metrics=_pipeline_metrics(snapshot),
        caption=_pipeline_caption(snapshot),
        body_renderer=lambda: _render_pipeline_tabs(snapshot),
    )


def _pipeline_metrics(snapshot: PipelineSessionSnapshot) -> tuple[LiveMetric, ...]:
    return (
        ("Status", snapshot.state.value.upper()),
        ("Mode", "Idle" if snapshot.plan is None else snapshot.plan.mode.label),
        ("Received Frames", str(snapshot.received_frames)),
        ("Frame Rate", f"{snapshot.measured_fps:.2f} fps"),
        ("Sparse Points", str(snapshot.num_sparse_points)),
        ("Dense Points", str(snapshot.num_dense_points)),
    )


def _pipeline_caption(snapshot: PipelineSessionSnapshot) -> str | None:
    if snapshot.plan is None:
        return None
    return (
        f"Run Id: `{snapshot.plan.run_id}` · Artifact Root: `{snapshot.plan.artifact_root}`"
        f" · Method: {snapshot.plan.method.display_name}"
    )


def _render_pipeline_tabs(snapshot: PipelineSessionSnapshot) -> None:
    packet = snapshot.latest_packet
    tabs = st.tabs(["Frames", "Trajectory", "Plan", "Artifacts"])
    with tabs[0]:
        if packet is None:
            st.info("No frame has been processed yet.")
        else:
            pointmap = snapshot.latest_slam_update.pointmap if snapshot.latest_slam_update is not None else None
            preview_left, preview_right = st.columns(2, gap="large")
            with preview_left:
                st.markdown("**RGB Frame**")
                st.image(packet.rgb, channels="RGB", clamp=True, width="stretch")
            with preview_right:
                st.markdown("**Pointmap Depth**")
                if pointmap is None:
                    st.info("No pointmap preview is available for the current frame.")
                else:
                    st.image(_pointmap_depth_preview(pointmap), clamp=True, width="stretch")
            details_left, details_right = st.columns((1.0, 1.0), gap="large")
            with details_left:
                st.markdown("**SLAM Update**")
                if snapshot.latest_slam_update is None:
                    st.info("No SLAM update is available yet.")
                else:
                    st.json(
                        {
                            **snapshot.latest_slam_update.model_dump(mode="json", exclude={"pointmap"}),
                            "pointmap_shape": None if pointmap is None else list(pointmap.shape),
                        },
                        expanded=False,
                    )
            with details_right:
                st.markdown("**Frame Metadata**")
                st.json(
                    {
                        "seq": packet.seq,
                        "timestamp_ns": packet.timestamp_ns,
                        "metadata": packet.metadata,
                    },
                    expanded=False,
                )
                st.markdown("**Camera Intrinsics**")
                render_camera_intrinsics(
                    intrinsics=packet.intrinsics,
                    missing_message="Camera intrinsics are not available for the current packet.",
                )
    with tabs[1]:
        render_live_trajectory(
            positions_xyz=snapshot.trajectory_positions_xyz,
            timestamps_s=snapshot.trajectory_timestamps_s if len(snapshot.trajectory_timestamps_s) else None,
            empty_message="The mock SLAM backend has not produced any trajectory points yet.",
        )
        st.markdown("**Evo APE Colormap**")
        show_evo_preview = st.toggle(
            "Enable evo APE preview",
            value=False,
            key="pipeline_show_evo_preview",
        )
        if not show_evo_preview:
            st.caption("Enable the toggle to run explicit evo APE preview for the current demo slice.")
        else:
            evo_preview, evo_error = _resolve_evo_preview(snapshot)
            if evo_error is not None:
                st.warning(evo_error)
            elif evo_preview is None:
                st.info(
                    "Complete one demo run with a reference trajectory to render the evo APE colormap for this slice."
                )
            else:
                st.plotly_chart(
                    build_evo_ape_colormap_figure(
                        reference=evo_preview.reference,
                        estimate=evo_preview.estimate,
                        error_series=evo_preview.error_series,
                    ),
                    width="stretch",
                )
                st.caption(
                    f"Matched pairs: `{len(evo_preview.error_series.values)}` · RMSE: `{evo_preview.stats.rmse:.4f} m`"
                )
    with tabs[2]:
        if snapshot.plan is None:
            st.info("Start a run to inspect the generated plan and execution records.")
        else:
            left, right = st.columns(2, gap="large")
            with left:
                st.markdown("**Planned Stages**")
                st.dataframe(_stage_rows(snapshot.plan), hide_index=True, width="stretch")
            with right:
                st.markdown("**Stage Manifests**")
                if snapshot.stage_manifests:
                    st.dataframe(_stage_manifest_rows(snapshot.stage_manifests), hide_index=True, width="stretch")
                else:
                    st.info("Stage manifests will appear once the run starts writing outputs.")
    with tabs[3]:
        if snapshot.sequence_manifest is None and snapshot.slam is None and snapshot.summary is None:
            st.info("Run the demo to inspect the materialized manifest, SLAM artifacts, and run summary.")
        else:
            left, right = st.columns(2, gap="large")
            with left:
                if snapshot.sequence_manifest is not None:
                    st.markdown("**Sequence Manifest**")
                    st.code(_json_dump(snapshot.sequence_manifest.model_dump(mode="json")), language="json")
                if snapshot.summary is not None:
                    st.markdown("**Run Summary**")
                    st.code(_json_dump(snapshot.summary.model_dump(mode="json")), language="json")
            with right:
                if snapshot.slam is not None:
                    st.markdown("**SLAM Artifacts**")
                    st.code(_json_dump(snapshot.slam.model_dump(mode="json")), language="json")


def _render_pipeline_notice(snapshot: PipelineSessionSnapshot) -> None:
    match snapshot.state:
        case PipelineSessionState.IDLE:
            st.info("Select a replay-ready ADVIO scene and start the pipeline demo.")
        case PipelineSessionState.CONNECTING:
            st.info("Preparing the sequence manifest and starting the mock SLAM backend.")
        case PipelineSessionState.RUNNING:
            st.success("Processing ADVIO frames through the mock SLAM backend.")
        case PipelineSessionState.COMPLETED:
            st.success("The offline demo finished and wrote mock SLAM artifacts.")
        case PipelineSessionState.STOPPED:
            st.warning("The demo stopped. The last frame, trajectory, and written artifacts remain visible below.")
        case PipelineSessionState.FAILED:
            st.error(snapshot.error_message or "The pipeline demo failed.")


def _handle_pipeline_page_action(context: AppContext, action: PipelinePageAction) -> str | None:
    """Apply one pipeline-page action and return a surfaced error when one occurs."""
    save_model_updates(
        context.store,
        context.state,
        context.state.pipeline,
        sequence_id=action.sequence_id,
        mode=action.mode,
        method=action.method,
        pose_source=action.pose_source,
        respect_video_rotation=action.respect_video_rotation,
    )
    if action.stop_requested:
        context.pipeline_runtime.stop()
        return None
    if not action.start_requested:
        return None

    try:
        start_advio_demo_run(
            context,
            sequence_id=action.sequence_id,
            mode=action.mode,
            method=action.method,
            pose_source=action.pose_source,
            respect_video_rotation=action.respect_video_rotation,
        )
        return None
    except Exception as exc:
        return str(exc)


def _pointmap_depth_preview(pointmap: np.ndarray) -> np.ndarray:
    return normalize_grayscale_image(np.asarray(pointmap[..., 2], dtype=np.float32))


def _stage_rows(plan: RunPlan) -> list[dict[str, str]]:
    return [
        {
            "Stage": stage.title,
            "Id": stage.id.value,
            "Outputs": ", ".join(path.name for path in stage.outputs),
        }
        for stage in plan.stages
    ]


def _stage_manifest_rows(stage_manifests: list[StageManifest]) -> list[dict[str, str]]:
    return [
        {
            "Stage": manifest.stage_id.value,
            "Status": manifest.status.value,
            "Config Hash": manifest.config_hash,
            "Outputs": ", ".join(path.name for path in manifest.output_paths.values()),
        }
        for manifest in stage_manifests
    ]


def _json_dump(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _resolve_evo_preview(snapshot: PipelineSessionSnapshot) -> tuple[PipelineEvoPreview | None, str | None]:
    if snapshot.sequence_manifest is None or snapshot.slam is None:
        return None, None
    reference_path = snapshot.sequence_manifest.reference_tum_path
    estimate_path = snapshot.slam.trajectory_tum.path
    if reference_path is None:
        return None, "No `ground_truth.tum` reference is available for this ADVIO slice."
    if not reference_path.exists() or not estimate_path.exists():
        return None, None
    try:
        return (
            _compute_evo_preview(
                reference_path=reference_path,
                estimate_path=estimate_path,
                reference_mtime_ns=reference_path.stat().st_mtime_ns,
                estimate_mtime_ns=estimate_path.stat().st_mtime_ns,
            ),
            None,
        )
    except (RuntimeError, ValueError) as exc:
        return None, str(exc)


@lru_cache(maxsize=32)
def _compute_evo_preview(
    *,
    reference_path: Path,
    estimate_path: Path,
    reference_mtime_ns: int,
    estimate_mtime_ns: int,
) -> PipelineEvoPreview:
    del reference_mtime_ns, estimate_mtime_ns
    reference_trajectory = load_tum_trajectory(reference_path)
    estimate_trajectory = load_tum_trajectory(estimate_path)
    try:
        associated_reference, associated_estimate = evo_sync.associate_trajectories(
            _to_evo_trajectory(reference_trajectory),
            _to_evo_trajectory(estimate_trajectory),
            max_diff=_EVO_ASSOCIATION_MAX_DIFF_S,
        )
    except evo_sync.SyncException as exc:
        raise ValueError(
            f"No matching timestamps were found for evo APE (max_diff={_EVO_ASSOCIATION_MAX_DIFF_S:.3f}s)."
        ) from exc

    metric = evo_metrics.APE(evo_metrics.PoseRelation.translation_part)
    metric.process_data((associated_reference, associated_estimate))
    error_values = np.asarray(metric.error, dtype=np.float64)
    if error_values.size == 0:
        raise ValueError("evo APE produced zero matched trajectory pairs for the current run.")

    return PipelineEvoPreview(
        reference=TrajectorySeries(
            name="Reference",
            timestamps_s=np.asarray(associated_reference.timestamps, dtype=np.float64),
            positions_xyz=np.asarray(associated_reference.positions_xyz, dtype=np.float64),
        ),
        estimate=TrajectorySeries(
            name="Estimate",
            timestamps_s=np.asarray(associated_estimate.timestamps, dtype=np.float64),
            positions_xyz=np.asarray(associated_estimate.positions_xyz, dtype=np.float64),
        ),
        error_series=ErrorSeries(
            timestamps_s=np.asarray(associated_reference.timestamps, dtype=np.float64),
            values=error_values,
        ),
        stats=MetricStats.from_error_values(error_values),
    )


def _to_evo_trajectory(trajectory: TimedPoseTrajectory) -> PoseTrajectory3D:
    return PoseTrajectory3D(
        positions_xyz=trajectory.positions_xyz,
        orientations_quat_wxyz=np.roll(trajectory.quaternions_xyzw, 1, axis=1),
        timestamps=trajectory.timestamps_s,
    )


__all__ = ["render"]
