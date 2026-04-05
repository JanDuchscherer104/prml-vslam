"""Controller helpers for the interactive Pipeline page demo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.datasets.interfaces import DatasetId
from prml_vslam.io import Cv2ReplayMode
from prml_vslam.methods import MethodId
from prml_vslam.methods.mock_tracking import MockTrackingRuntimeConfig
from prml_vslam.pipeline.contracts import (
    BenchmarkEvaluationConfig,
    DatasetSourceSpec,
    DenseConfig,
    PipelineMode,
    ReferenceConfig,
    RunRequest,
    TrackingConfig,
)
from prml_vslam.utils import BaseData

from .pipeline_runtime import PipelineDemoSnapshot, PipelineDemoState

if TYPE_CHECKING:
    from .bootstrap import AppContext


_ACTIVE_PIPELINE_STATES = {PipelineDemoState.CONNECTING, PipelineDemoState.RUNNING}


class PipelineDemoFormData(BaseData):
    """Typed form payload for the interactive pipeline demo."""

    sequence_id: int
    """Selected ADVIO sequence id."""

    mode: PipelineMode
    """Selected pipeline mode."""

    method: MethodId
    """Selected mock tracking backend label."""

    pose_source: AdvioPoseSource
    """Selected pose source for the ADVIO replay stream."""

    respect_video_rotation: bool = False
    """Whether the replay should honor rotation metadata."""

    start_requested: bool = False
    """Whether the user requested a new run."""

    stop_requested: bool = False
    """Whether the user requested to stop the current run."""


def sync_pipeline_demo_state(
    context: AppContext,
    snapshot: PipelineDemoSnapshot | None = None,
) -> PipelineDemoSnapshot:
    """Keep persisted Pipeline-page running state aligned with the runtime snapshot."""
    snapshot = context.pipeline_runtime.snapshot() if snapshot is None else snapshot
    if context.state.pipeline.is_running and snapshot.state not in _ACTIVE_PIPELINE_STATES:
        context.state.pipeline.is_running = False
        context.store.save(context.state)
    return snapshot


def handle_pipeline_demo_action(context: AppContext, form: PipelineDemoFormData) -> str | None:
    """Apply one Pipeline-page action and return an error message when it fails."""
    _save_page_state(
        context,
        sequence_id=form.sequence_id,
        mode=form.mode,
        method=form.method,
        pose_source=form.pose_source,
        respect_video_rotation=form.respect_video_rotation,
    )
    if form.stop_requested:
        context.pipeline_runtime.stop()
        context.state.pipeline.is_running = False
        context.store.save(context.state)
        return None
    if not form.start_requested:
        return None

    try:
        scene = context.advio_service.scene(form.sequence_id)
        request = _build_demo_request(
            output_dir=context.path_config.artifacts_dir,
            sequence_slug=scene.sequence_slug,
            mode=form.mode,
            method=form.method,
        )
        plan = request.build(context.path_config)
        run_paths = context.path_config.plan_run_paths(
            experiment_name=request.experiment_name,
            method_slug=request.tracking.method.artifact_slug,
            output_dir=request.output_dir,
        )
        sequence_manifest = context.advio_service.build_sequence_manifest(
            sequence_id=form.sequence_id,
            output_dir=run_paths.sequence_manifest_path.parent,
        )
        _write_json(run_paths.sequence_manifest_path, sequence_manifest.model_dump(mode="json"))
        tracker = MockTrackingRuntimeConfig(method_id=form.method).setup_target()
        if tracker is None:
            raise RuntimeError("Failed to initialize the mock tracking runtime.")
        context.pipeline_runtime.start(
            sequence_id=form.sequence_id,
            sequence_label=scene.display_name,
            pose_source=form.pose_source,
            plan=plan,
            tracking_config=request.tracking,
            sequence_manifest=sequence_manifest,
            stream=context.advio_service.open_preview_stream(
                sequence_id=form.sequence_id,
                pose_source=form.pose_source,
                respect_video_rotation=form.respect_video_rotation,
                loop=form.mode is PipelineMode.STREAMING,
                replay_mode=Cv2ReplayMode.REALTIME,
            ),
            tracker=tracker,
        )
        context.state.pipeline.is_running = True
        context.store.save(context.state)
        return None
    except Exception as exc:
        context.state.pipeline.is_running = False
        context.store.save(context.state)
        return str(exc)


def _build_demo_request(
    *,
    output_dir: Path,
    sequence_slug: str,
    mode: PipelineMode,
    method: MethodId,
) -> RunRequest:
    return RunRequest(
        experiment_name=f"advio-{mode.value}-{sequence_slug}-{method.value}",
        mode=mode,
        output_dir=output_dir,
        source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id=sequence_slug),
        tracking=TrackingConfig(method=method),
        dense=DenseConfig(enabled=False),
        reference=ReferenceConfig(enabled=False),
        evaluation=BenchmarkEvaluationConfig(
            compare_to_arcore=False,
            evaluate_cloud=False,
            evaluate_efficiency=False,
        ),
    )


def _save_page_state(context: AppContext, **updates: object) -> None:
    page_state = context.state.pipeline
    if all(getattr(page_state, key) == value for key, value in updates.items()):
        return
    for key, value in updates.items():
        setattr(page_state, key, value)
    context.store.save(context.state)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


__all__ = ["PipelineDemoFormData", "handle_pipeline_demo_action", "sync_pipeline_demo_state"]
