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

from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.eval.contracts import ErrorSeries, MetricStats, TrajectorySeries
from prml_vslam.pipeline import RunRequest
from prml_vslam.pipeline.contracts import (
    DatasetSourceSpec,
    StageManifest,
)
from prml_vslam.pipeline.demo import load_run_request_toml
from prml_vslam.pipeline.session import PipelineSessionSnapshot, PipelineSessionState
from prml_vslam.plotting import build_evo_ape_colormap_figure
from prml_vslam.utils import BaseData, PathConfig
from prml_vslam.utils.geometry import load_tum_trajectory
from prml_vslam.utils.image_utils import normalize_grayscale_image

from ..live_session import (
    LiveMetric,
    live_poll_interval,
    render_camera_intrinsics,
    render_live_action_slot,
    render_live_fragment,
    render_live_session_shell,
    render_live_trajectory,
    rerun_after_action,
)
from ..state import save_model_updates
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


_ACTIVE_SESSION_STATES = frozenset({PipelineSessionState.CONNECTING, PipelineSessionState.RUNNING})
_EVO_ASSOCIATION_MAX_DIFF_S = 0.01


class PipelinePageAction(BaseData):
    """Typed action payload for the pipeline page controls."""

    config_path: Path
    """Selected pipeline request TOML."""

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
    previewable_statuses = [status for status in statuses if status.replay_ready]
    snapshot = context.run_service.snapshot()
    is_active = snapshot.state in _ACTIVE_SESSION_STATES
    with st.container(border=True):
        st.subheader("ADVIO Replay Demo")
        st.caption(
            "Select a persisted ADVIO pipeline request TOML and run it as a bounded offline or looped streaming session."
        )
        if not previewable_statuses:
            st.info(
                "Download the ADVIO streaming bundle for at least one scene to unlock the interactive pipeline demo."
            )
            return
        config_paths = _discover_pipeline_config_paths(context.path_config)
        if not config_paths:
            st.info("Persist at least one pipeline request TOML under `.configs/pipelines/` to unlock this demo.")
            return
        page_state = context.state.pipeline
        selected_config_path = page_state.config_path if page_state.config_path in config_paths else config_paths[0]
        selected_config_path = st.selectbox(
            "Pipeline Config",
            options=config_paths,
            index=config_paths.index(selected_config_path),
            format_func=lambda config_path: _pipeline_config_label(context.path_config, config_path),
        )
        request, request_error = _load_pipeline_request(context.path_config, selected_config_path)
        sequence_id, request_support_error = _resolve_advio_sequence_id(request=request, statuses=statuses)
        left, right = st.columns(2, gap="large")
        with left:
            st.markdown("**Resolved Request**")
            if request is None:
                st.warning(request_error or "Failed to load the selected pipeline config.")
            else:
                st.json(_request_summary_payload(request), expanded=False)
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
            if request_support_error is None and request is not None and sequence_id is not None:
                st.caption(f"Resolved demo sequence: `{context.advio_service.scene(sequence_id).display_name}`")
            elif request_support_error is not None:
                st.warning(request_support_error)
        start_requested, stop_requested = render_live_action_slot(
            is_active=is_active,
            start_label="Start run",
            stop_label="Stop run",
            start_disabled=request is None or request_support_error is not None,
        )
        action = PipelinePageAction(
            config_path=selected_config_path,
            pose_source=pose_source,
            respect_video_rotation=respect_video_rotation,
            start_requested=start_requested,
            stop_requested=stop_requested,
        )
        error_message = _handle_pipeline_page_action(
            context=context,
            action=action,
        )
        if rerun_after_action(
            action_requested=action.start_requested or action.stop_requested,
            error_message=error_message,
        ):
            return
        snapshot = context.run_service.snapshot()
        if error_message:
            st.error(error_message)
        render_live_fragment(
            run_every=live_poll_interval(is_active=snapshot.state in _ACTIVE_SESSION_STATES, interval_seconds=0.2),
            render_body=lambda: _render_pipeline_snapshot(context.run_service.snapshot()),
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
                st.dataframe(snapshot.plan.stage_rows(), hide_index=True, width="stretch")
            with right:
                st.markdown("**Stage Manifests**")
                if snapshot.stage_manifests:
                    st.dataframe(StageManifest.table_rows(snapshot.stage_manifests), hide_index=True, width="stretch")
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
                    st.code(
                        json.dumps(snapshot.sequence_manifest.model_dump(mode="json"), indent=2, sort_keys=True),
                        language="json",
                    )
                if snapshot.summary is not None:
                    st.markdown("**Run Summary**")
                    st.code(
                        json.dumps(snapshot.summary.model_dump(mode="json"), indent=2, sort_keys=True),
                        language="json",
                    )
            with right:
                if snapshot.slam is not None:
                    st.markdown("**SLAM Artifacts**")
                    st.code(
                        json.dumps(snapshot.slam.model_dump(mode="json"), indent=2, sort_keys=True),
                        language="json",
                    )


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
        config_path=action.config_path,
        pose_source=action.pose_source,
        respect_video_rotation=action.respect_video_rotation,
    )
    try:
        if action.stop_requested:
            context.run_service.stop_run()
            return None
        if not action.start_requested:
            return None
        _start_advio_demo_run(
            context,
            config_path=action.config_path,
            pose_source=action.pose_source,
            respect_video_rotation=action.respect_video_rotation,
        )
        return None
    except Exception as exc:
        return str(exc)


def _start_advio_demo_run(
    context: AppContext,
    *,
    config_path: Path,
    pose_source: AdvioPoseSource,
    respect_video_rotation: bool,
) -> None:
    """Start one bounded ADVIO demo run through the shared run facade."""
    request = load_run_request_toml(path_config=context.path_config, config_path=config_path)
    sequence_id, sequence_error = _resolve_advio_sequence_id(
        request=request,
        statuses=context.advio_service.local_scene_statuses(),
    )
    if sequence_error is not None or sequence_id is None:
        raise ValueError(sequence_error or "Failed to resolve an ADVIO scene for the selected pipeline config.")
    source = context.advio_service.build_streaming_source(
        sequence_id=sequence_id,
        pose_source=pose_source,
        respect_video_rotation=respect_video_rotation,
    )
    context.run_service.start_run(request=request, source=source)


def _discover_pipeline_config_paths(path_config: PathConfig) -> list[Path]:
    config_dir = path_config.resolve_pipeline_configs_dir()
    if not config_dir.exists():
        return []
    return sorted(path.resolve() for path in config_dir.rglob("*.toml") if path.is_file())


def _pipeline_config_label(path_config: PathConfig, config_path: Path) -> str:
    config_root = path_config.resolve_pipeline_configs_dir()
    try:
        return str(config_path.relative_to(config_root))
    except ValueError:
        return (
            str(config_path.relative_to(path_config.root))
            if config_path.is_relative_to(path_config.root)
            else str(config_path)
        )


def _load_pipeline_request(path_config: PathConfig, config_path: Path) -> tuple[RunRequest | None, str | None]:
    try:
        return load_run_request_toml(path_config=path_config, config_path=config_path), None
    except Exception as exc:
        return None, str(exc)


def _resolve_advio_sequence_id(
    *,
    request: RunRequest | None,
    statuses: list[object],
) -> tuple[int | None, str | None]:
    if request is None:
        return None, None
    match request.source:
        case DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id=sequence_slug):
            for status in statuses:
                scene = getattr(status, "scene", None)
                if scene is None or getattr(scene, "sequence_slug", None) != sequence_slug:
                    continue
                if bool(getattr(status, "replay_ready", False)):
                    return int(scene.sequence_id), None
                return None, f"ADVIO sequence '{sequence_slug}' is available locally but not replay-ready."
            return None, f"ADVIO sequence '{sequence_slug}' is not available locally."
        case DatasetSourceSpec(dataset_id=dataset_id):
            return None, f"Dataset '{dataset_id.value}' is not supported by this demo page."
        case _:
            return None, "This demo page only supports dataset-backed ADVIO pipeline configs."


def _request_summary_payload(request: RunRequest) -> dict[str, object]:
    payload = {
        "experiment_name": request.experiment_name,
        "mode": request.mode.value,
        "output_dir": request.output_dir.as_posix(),
        "slam": {
            "method": request.slam.method.value,
            "config_path": None if request.slam.config_path is None else request.slam.config_path.as_posix(),
            "max_frames": request.slam.max_frames,
            "emit_dense_points": request.slam.emit_dense_points,
            "emit_sparse_points": request.slam.emit_sparse_points,
        },
        "reference": request.reference.model_dump(mode="json"),
        "evaluation": request.evaluation.model_dump(mode="json"),
    }
    match request.source:
        case DatasetSourceSpec(dataset_id=dataset_id, sequence_id=sequence_id):
            payload["source"] = {
                "kind": "dataset",
                "dataset_id": dataset_id.value,
                "sequence_id": sequence_id,
            }
        case _:
            payload["source"] = request.source.model_dump(mode="json")
    return payload


def _pointmap_depth_preview(pointmap: np.ndarray) -> np.ndarray:
    return normalize_grayscale_image(np.asarray(pointmap[..., 2], dtype=np.float32))


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
            reference_trajectory,
            estimate_trajectory,
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


__all__ = ["render"]
