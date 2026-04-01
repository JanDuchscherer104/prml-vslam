"""Shared CLI helpers for planning and running the pipeline."""

from __future__ import annotations

import math
from pathlib import Path

import cv2
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from prml_vslam.datasets import AdvioSequence, AdvioSequenceConfig
from prml_vslam.eval import TrajectoryEvaluationConfig
from prml_vslam.pipeline import (
    CaptureMetadataConfig,
    MessageKind,
    MethodId,
    PipelineMode,
    PipelinePlannerService,
    RunPlanRequest,
    SessionManager,
    TimestampSource,
    WorkspaceMaterializerService,
    make_envelope,
)
from prml_vslam.utils.console import Console

console = Console(__name__)
planner = PipelinePlannerService()
materializer = WorkspaceMaterializerService(planner=planner)


def build_capture_metadata(
    *,
    device_label: str | None = None,
    frame_rate_hz: float | None = None,
    timestamp_source: TimestampSource = TimestampSource.CAPTURE,
    arcore_log_path: Path | None = None,
    calibration_hint_path: Path | None = None,
    notes: str | None = None,
) -> CaptureMetadataConfig:
    """Build capture metadata from shared CLI options."""
    return CaptureMetadataConfig(
        device_label=device_label,
        frame_rate_hz=frame_rate_hz,
        timestamp_source=timestamp_source,
        arcore_log_path=arcore_log_path,
        calibration_hint_path=calibration_hint_path,
        notes=notes,
    )


def build_run_request(
    *,
    experiment_name: str,
    video_path: Path,
    output_dir: Path,
    mode: PipelineMode,
    method: MethodId,
    frame_stride: int,
    dense_mapping: bool = True,
    compare_to_arcore: bool = True,
    ground_truth_cloud: bool = True,
    capture: CaptureMetadataConfig | None = None,
) -> RunPlanRequest:
    """Build the repo-owned run request from common CLI inputs."""
    return RunPlanRequest(
        experiment_name=experiment_name,
        video_path=video_path,
        output_dir=output_dir,
        mode=mode,
        method=method,
        frame_stride=frame_stride,
        enable_dense_mapping=dense_mapping,
        compare_to_arcore=compare_to_arcore,
        build_ground_truth_cloud=ground_truth_cloud,
        capture=capture or CaptureMetadataConfig(),
    )


def resolve_advio_sequence(sequence_id: int, dataset_root: Path) -> AdvioSequence:
    """Resolve one local ADVIO sequence and ensure the required files exist."""
    return AdvioSequence(config=AdvioSequenceConfig(dataset_root=dataset_root, sequence_id=sequence_id)).assert_ready()


def default_advio_experiment_name(sequence_id: int) -> str:
    """Return the default experiment label for one ADVIO sequence."""
    return f"ADVIO {sequence_id:02d}"


def estimate_sequence_frames(
    frame_timestamps_ns: list[int], *, frame_stride: int, max_frames: int | None
) -> int | None:
    """Estimate how many frames will be processed for a timestamped sequence."""
    if not frame_timestamps_ns:
        return max_frames
    estimated = max(1, math.ceil(len(frame_timestamps_ns) / frame_stride))
    if max_frames is not None:
        estimated = min(estimated, max_frames)
    return estimated


def print_eval_summary(result: TrajectoryEvaluationConfig, stats: dict[str, float], *, matching_pairs: int) -> None:
    """Render a compact trajectory-evaluation summary."""
    summary = Table(title="Trajectory evaluation summary", show_header=False, box=None, pad_edge=False)
    summary.add_column("Field", style="bold")
    summary.add_column("Value")
    summary.add_row("Reference", str(result.reference_path))
    summary.add_row("Estimate", str(result.estimate_path))
    summary.add_row("Pose relation", result.pose_relation.value)
    summary.add_row("Align", str(result.align))
    summary.add_row("Correct scale", str(result.correct_scale))
    summary.add_row("Max diff (s)", f"{result.max_diff_s:.3f}")
    summary.add_row("Matching pairs", str(matching_pairs))
    for key in sorted(stats):
        summary.add_row(key, f"{stats[key]:.6f}")
    console.print(summary)


def has_workspace_contract(artifact_root: Path) -> bool:
    """Return whether the repo-owned planning surface exists under ``artifact_root``."""
    return all(
        path.exists()
        for path in (
            artifact_root / "input" / "capture_manifest.json",
            artifact_root / "planning" / "run_request.toml",
            artifact_root / "planning" / "run_plan.toml",
        )
    )


def ensure_offline_workspace(request: RunPlanRequest) -> Path:
    """Ensure the batch workspace exists before executing the offline runtime."""
    plan = planner.build_plan(request)
    artifact_root = plan.artifact_root
    if has_workspace_contract(artifact_root):
        return artifact_root

    if artifact_root.exists() and any(artifact_root.iterdir()):
        msg = (
            f"Artifact root {artifact_root} already exists but is missing the planning contract. "
            "Remove it or materialize the workspace explicitly before running offline."
        )
        raise FileExistsError(msg)

    materializer.materialize(request)
    return artifact_root


def estimate_offline_frames(video_path: Path, *, frame_stride: int, max_frames: int | None) -> int | None:
    """Estimate the number of frames that will be processed by the offline path."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return max_frames
    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        cap.release()

    if total_frames <= 0:
        return max_frames

    estimated = max(1, math.ceil(total_frames / frame_stride))
    if max_frames is not None:
        estimated = min(estimated, max_frames)
    return estimated


def print_run_banner(
    *, title: str, mode: str, method: MethodId, artifact_root: Path, source: Path | None = None
) -> None:
    """Render a compact execution banner before running the pipeline."""
    lines = [
        f"[bold]{title}[/bold]",
        f"Mode: [cyan]{mode}[/cyan]",
        f"Method: [cyan]{method.value}[/cyan]",
        f"Artifact root: [cyan]{artifact_root}[/cyan]",
    ]
    if source is not None:
        lines.insert(3, f"Source: [cyan]{source}[/cyan]")
    console.print(Panel.fit("\n".join(lines), border_style="blue"))


def print_run_summary(
    *,
    title: str,
    session_id: str,
    method: MethodId,
    artifact_root: Path,
    frames_processed: int,
    outputs: list,
) -> None:
    """Render a readable run summary after pipeline execution."""
    pose_count = sum(1 for output in outputs if output.kind == MessageKind.POSE_UPDATE)
    preview_count = sum(1 for output in outputs if output.kind == MessageKind.PREVIEW)
    map_count = sum(1 for output in outputs if output.kind == MessageKind.MAP_UPDATE)

    summary = Table(title=title, show_header=False, box=None, pad_edge=False)
    summary.add_column("Field", style="bold")
    summary.add_column("Value")
    summary.add_row("Session", session_id)
    summary.add_row("Method", method.value)
    summary.add_row("Frames processed", str(frames_processed))
    summary.add_row("Pose updates", str(pose_count))
    summary.add_row("Preview updates", str(preview_count))
    summary.add_row("Map updates", str(map_count))
    summary.add_row("Capture manifest", str(artifact_root / "input" / "capture_manifest.json"))
    summary.add_row("Trajectory", str(artifact_root / "slam" / "trajectory.tum"))
    console.print(summary)


def build_progress(*, description: str, total: int | None) -> tuple[Progress, int]:
    """Create a Rich progress helper with or without a determinate total."""
    columns = [SpinnerColumn(), TextColumn("{task.description}")]
    if total is not None:
        columns.extend([BarColumn(), TaskProgressColumn()])
    columns.append(TimeElapsedColumn())
    progress = Progress(*columns, console=console.rich_console, transient=True)
    task_id = progress.add_task(description, total=total)
    return progress, task_id


def execute_offline_run(
    *,
    manager: SessionManager,
    method: MethodId,
    artifact_root: Path,
    video_path: Path,
    frame_stride: int,
    max_frames: int | None,
    estimated_frames: int | None,
    title: str,
    summary_title: str,
    progress_description: str,
    frame_timestamps_ns: list[int] | None = None,
) -> None:
    """Run one offline pipeline session with shared progress and summary rendering."""
    print_run_banner(
        title=title,
        mode=PipelineMode.BATCH.value,
        method=method,
        artifact_root=artifact_root,
        source=video_path,
    )

    session = manager.create_session(
        mode=PipelineMode.BATCH,
        method=method,
        artifact_root=artifact_root,
        video_path=video_path,
        frame_stride=frame_stride,
        max_frames=max_frames,
        frame_timestamps_ns=frame_timestamps_ns,
    )

    outputs: list = []
    processed_frames = 0
    progress, task_id = build_progress(description=progress_description, total=estimated_frames)
    with progress:
        for action_name, step_outputs, frame_index in manager.iterate_offline(session.session_id):
            if action_name == "slam":
                processed_frames += 1
                if estimated_frames is not None:
                    progress.advance(task_id, 1)
                    progress.update(
                        task_id,
                        description=f"{progress_description} ({processed_frames}/{estimated_frames})",
                    )
                else:
                    progress.update(
                        task_id,
                        completed=processed_frames,
                        description=f"{progress_description} (frame {frame_index + 1})",
                    )
            outputs.extend(step_outputs)
    outputs.extend(manager.close_session(session.session_id))

    print_run_summary(
        title=summary_title,
        session_id=session.session_id,
        method=method,
        artifact_root=artifact_root,
        frames_processed=processed_frames,
        outputs=outputs,
    )


def execute_streaming_demo(
    *,
    manager: SessionManager,
    method: MethodId,
    artifact_root: Path,
    num_frames: int,
) -> None:
    """Run the synthetic streaming demo with shared progress and summary rendering."""
    print_run_banner(
        title="Streaming pipeline demo",
        mode=PipelineMode.STREAMING.value,
        method=method,
        artifact_root=artifact_root,
    )

    session = manager.create_session(
        mode=PipelineMode.STREAMING,
        method=method,
        artifact_root=artifact_root,
    )

    all_outputs: list = []
    progress, task_id = build_progress(description="Running streaming demo", total=num_frames)
    with progress:
        for index in range(num_frames):
            envelope = make_envelope(
                session_id=session.session_id,
                seq=index,
                kind=MessageKind.FRAME,
                payload={"width": 640, "height": 480, "frame_index": index},
                ts_ns=int(index * (1 / 30) * 1e9),
            )
            all_outputs.extend(manager.push(session.session_id, [envelope]))
            progress.advance(task_id, 1)
            progress.update(task_id, description=f"Running streaming demo ({index + 1}/{num_frames})")

    all_outputs.extend(manager.close_session(session.session_id))

    print_run_summary(
        title="Streaming demo summary",
        session_id=session.session_id,
        method=method,
        artifact_root=artifact_root,
        frames_processed=num_frames,
        outputs=all_outputs,
    )
