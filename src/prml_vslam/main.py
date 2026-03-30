"""CLI entry point for the project scaffold."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Annotated

import cv2
import typer
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

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

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Utilities and entry points for the PRML monocular VSLAM project scaffold.",
)
console = Console(__name__)
planner = PipelinePlannerService()
materializer = WorkspaceMaterializerService(planner=planner)

ExperimentNameArg = Annotated[str, typer.Argument(help="Human-readable experiment name.")]
VideoPathArg = Annotated[Path, typer.Argument(help="Path to the input video.")]
OutputDirOption = Annotated[
    Path,
    typer.Option("--output-dir", help="Root directory for benchmark artifacts."),
]
MethodOption = Annotated[
    MethodId,
    typer.Option(
        "--method",
        help="External monocular VSLAM backend to plan for.",
        case_sensitive=False,
    ),
]
ModeOption = Annotated[
    PipelineMode,
    typer.Option(
        "--mode",
        help="Execution mode to plan for.",
        case_sensitive=False,
    ),
]
FrameStrideOption = Annotated[
    int,
    typer.Option(min=1, max=30, help="Frame subsampling stride."),
]
DenseOption = Annotated[
    bool,
    typer.Option(
        "--dense/--no-dense",
        help="Whether the plan should include dense map export.",
    ),
]
ArcoreOption = Annotated[
    bool,
    typer.Option(
        "--arcore/--no-arcore",
        help="Whether the plan assumes ARCore comparison data is available.",
    ),
]
ReferenceCloudOption = Annotated[
    bool,
    typer.Option(
        "--reference-cloud/--no-reference-cloud",
        help="Whether the plan reserves a reference reconstruction stage.",
    ),
]
DeviceLabelOption = Annotated[
    str | None,
    typer.Option("--device-label", help="Optional human-readable capture device label."),
]
FrameRateOption = Annotated[
    float | None,
    typer.Option("--frame-rate-hz", min=0.001, help="Optional nominal capture frame rate."),
]
TimestampSourceOption = Annotated[
    TimestampSource,
    typer.Option(
        "--timestamp-source",
        help="Timestamp provenance stored in normalized artifacts.",
        case_sensitive=False,
    ),
]
ArcoreLogOption = Annotated[
    Path | None,
    typer.Option("--arcore-log-path", help="Optional ARCore side-channel log path."),
]
CalibrationHintOption = Annotated[
    Path | None,
    typer.Option("--calibration-hint-path", help="Optional calibration hint path."),
]
NotesOption = Annotated[
    str | None,
    typer.Option("--notes", help="Optional operator or experiment note."),
]


def _offline_request(
    *,
    experiment_name: str,
    video_path: Path,
    output_dir: Path,
    method: MethodId,
    frame_stride: int,
) -> RunPlanRequest:
    """Build the batch run request used by offline execution commands."""
    return RunPlanRequest(
        experiment_name=experiment_name,
        video_path=video_path,
        output_dir=output_dir,
        mode=PipelineMode.BATCH,
        method=method,
        frame_stride=frame_stride,
        capture=CaptureMetadataConfig(),
    )


def _has_workspace_contract(artifact_root: Path) -> bool:
    """Return whether the repo-owned planning surface exists under ``artifact_root``."""
    return all(
        path.exists()
        for path in (
            artifact_root / "input" / "capture_manifest.json",
            artifact_root / "planning" / "run_request.toml",
            artifact_root / "planning" / "run_plan.toml",
        )
    )


def _ensure_offline_workspace(request: RunPlanRequest) -> Path:
    """Ensure the batch workspace exists before executing the offline runtime."""
    plan = planner.build_plan(request)
    artifact_root = plan.artifact_root
    if _has_workspace_contract(artifact_root):
        return artifact_root

    if artifact_root.exists() and any(artifact_root.iterdir()):
        msg = (
            f"Artifact root {artifact_root} already exists but is missing the planning contract. "
            "Remove it or materialize the workspace explicitly before running offline."
        )
        raise FileExistsError(msg)

    materializer.materialize(request)
    return artifact_root


def _estimate_offline_frames(video_path: Path, *, frame_stride: int, max_frames: int | None) -> int | None:
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


def _print_run_banner(
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


def _print_run_summary(
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


def _build_progress(*, description: str, total: int | None) -> tuple[Progress, int]:
    """Create a Rich progress helper with or without a determinate total."""
    columns = [SpinnerColumn(), TextColumn("{task.description}")]
    if total is not None:
        columns.extend([BarColumn(), TaskProgressColumn()])
    columns.append(TimeElapsedColumn())
    progress = Progress(*columns, console=console.rich_console, transient=True)
    task_id = progress.add_task(description, total=total)
    return progress, task_id


@app.callback()
def callback() -> None:
    """Register the root command group."""
    return None


@app.command()
def info() -> None:
    """Print a short summary of the current scaffold."""
    console.print(
        "[bold]prml-vslam[/bold]: editable Python package, typed pipeline planner, "
        "Streamlit workbench, and report/slides scaffold."
    )


@app.command("plan-run")
def plan_run(
    experiment_name: ExperimentNameArg,
    video_path: VideoPathArg,
    output_dir: OutputDirOption = Path("artifacts"),
    mode: ModeOption = PipelineMode.BATCH,
    method: MethodOption = MethodId.VISTA_SLAM,
    frame_stride: FrameStrideOption = 1,
    dense_mapping: DenseOption = True,
    compare_to_arcore: ArcoreOption = True,
    ground_truth_cloud: ReferenceCloudOption = True,
    device_label: DeviceLabelOption = None,
    frame_rate_hz: FrameRateOption = None,
    timestamp_source: TimestampSourceOption = TimestampSource.CAPTURE,
    arcore_log_path: ArcoreLogOption = None,
    calibration_hint_path: CalibrationHintOption = None,
    notes: NotesOption = None,
) -> None:
    """Build a typed benchmark run plan from the CLI."""
    request = RunPlanRequest(
        experiment_name=experiment_name,
        video_path=video_path,
        output_dir=output_dir,
        mode=mode,
        method=method,
        frame_stride=frame_stride,
        enable_dense_mapping=dense_mapping,
        compare_to_arcore=compare_to_arcore,
        build_ground_truth_cloud=ground_truth_cloud,
        capture=CaptureMetadataConfig(
            device_label=device_label,
            frame_rate_hz=frame_rate_hz,
            timestamp_source=timestamp_source,
            arcore_log_path=arcore_log_path,
            calibration_hint_path=calibration_hint_path,
            notes=notes,
        ),
    )
    plan = planner.build_plan(request)
    console.plog(plan.model_dump(mode="json"))


@app.command("materialize-run")
def materialize_run(
    experiment_name: ExperimentNameArg,
    video_path: VideoPathArg,
    output_dir: OutputDirOption = Path("artifacts"),
    mode: ModeOption = PipelineMode.BATCH,
    method: MethodOption = MethodId.VISTA_SLAM,
    frame_stride: FrameStrideOption = 1,
    dense_mapping: DenseOption = True,
    compare_to_arcore: ArcoreOption = True,
    ground_truth_cloud: ReferenceCloudOption = True,
    device_label: DeviceLabelOption = None,
    frame_rate_hz: FrameRateOption = None,
    timestamp_source: TimestampSourceOption = TimestampSource.CAPTURE,
    arcore_log_path: ArcoreLogOption = None,
    calibration_hint_path: CalibrationHintOption = None,
    notes: NotesOption = None,
) -> None:
    """Materialize a deterministic workspace for a planned benchmark run."""
    request = RunPlanRequest(
        experiment_name=experiment_name,
        video_path=video_path,
        output_dir=output_dir,
        mode=mode,
        method=method,
        frame_stride=frame_stride,
        enable_dense_mapping=dense_mapping,
        compare_to_arcore=compare_to_arcore,
        build_ground_truth_cloud=ground_truth_cloud,
        capture=CaptureMetadataConfig(
            device_label=device_label,
            frame_rate_hz=frame_rate_hz,
            timestamp_source=timestamp_source,
            arcore_log_path=arcore_log_path,
            calibration_hint_path=calibration_hint_path,
            notes=notes,
        ),
    )
    workspace = materializer.materialize(request)
    console.plog(workspace.model_dump(mode="json"))


MaxFramesOption = Annotated[
    int | None,
    typer.Option("--max-frames", min=1, help="Maximum number of frames to decode."),
]


@app.command("run-offline")
def run_offline(
    experiment_name: ExperimentNameArg,
    video_path: VideoPathArg,
    output_dir: OutputDirOption = Path("artifacts"),
    method: MethodOption = MethodId.VISTA_SLAM,
    frame_stride: FrameStrideOption = 1,
    max_frames: MaxFramesOption = None,
) -> None:
    """Execute the offline pipeline on a video file using mock SLAM backends."""
    mgr = SessionManager()
    request = _offline_request(
        experiment_name=experiment_name,
        video_path=video_path,
        output_dir=output_dir,
        method=method,
        frame_stride=frame_stride,
    )
    artifact_root = _ensure_offline_workspace(request)
    estimated_frames = _estimate_offline_frames(video_path, frame_stride=frame_stride, max_frames=max_frames)

    _print_run_banner(
        title="Offline pipeline run",
        mode="batch",
        method=method,
        artifact_root=artifact_root,
        source=video_path,
    )

    sess = mgr.create_session(
        mode="offline",
        method=method,
        artifact_root=artifact_root,
        video_path=video_path,
        frame_stride=frame_stride,
        max_frames=max_frames,
    )

    outputs = []
    processed_frames = 0
    progress, task_id = _build_progress(description="Running offline pipeline", total=estimated_frames)
    with progress:
        for action_name, step_outputs, frame_index in mgr.iterate_offline(sess.session_id):
            if action_name == "slam":
                processed_frames += 1
                if estimated_frames is not None:
                    progress.advance(task_id, 1)
                    progress.update(
                        task_id,
                        description=f"Running offline pipeline ({processed_frames}/{estimated_frames})",
                    )
                else:
                    progress.update(
                        task_id,
                        completed=processed_frames,
                        description=f"Running offline pipeline (frame {frame_index + 1})",
                    )
            outputs.extend(step_outputs)
    final = mgr.close_session(sess.session_id)
    outputs.extend(final)

    _print_run_summary(
        title="Offline pipeline summary",
        session_id=sess.session_id,
        method=method,
        artifact_root=artifact_root,
        frames_processed=processed_frames,
        outputs=outputs,
    )


@app.command("run-streaming-demo")
def run_streaming_demo(
    output_dir: OutputDirOption = Path("artifacts"),
    method: MethodOption = MethodId.VISTA_SLAM,
    num_frames: Annotated[int, typer.Option("--num-frames", min=1, help="Synthetic frames to push.")] = 50,
) -> None:
    """Push synthetic frames through the streaming pipeline to demo session management."""
    mgr = SessionManager()
    artifact_root = Path(output_dir) / "streaming-demo" / "streaming" / method.value

    _print_run_banner(
        title="Streaming pipeline demo",
        mode="streaming",
        method=method,
        artifact_root=artifact_root,
    )

    sess = mgr.create_session(
        mode="streaming",
        method=method,
        artifact_root=artifact_root,
    )

    all_outputs = []
    progress, task_id = _build_progress(description="Running streaming demo", total=num_frames)
    with progress:
        for i in range(num_frames):
            envelope = make_envelope(
                session_id=sess.session_id,
                seq=i,
                kind=MessageKind.FRAME,
                payload={"width": 640, "height": 480, "frame_index": i},
                ts_ns=int(i * (1 / 30) * 1e9),
            )
            outputs = mgr.push(sess.session_id, [envelope])
            all_outputs.extend(outputs)
            progress.advance(task_id, 1)
            progress.update(task_id, description=f"Running streaming demo ({i + 1}/{num_frames})")

    final = mgr.close_session(sess.session_id)
    all_outputs.extend(final)

    _print_run_summary(
        title="Streaming demo summary",
        session_id=sess.session_id,
        method=method,
        artifact_root=artifact_root,
        frames_processed=num_frames,
        outputs=all_outputs,
    )


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
