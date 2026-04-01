"""CLI entry point for the project scaffold."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from prml_vslam.cli_advio import advio_app
from prml_vslam.cli_support import (
    build_capture_metadata,
    build_run_request,
    console,
    ensure_offline_workspace,
    estimate_offline_frames,
    execute_offline_run,
    execute_streaming_demo,
    materializer,
    planner,
    print_eval_summary,
)
from prml_vslam.eval import (
    PoseRelationId,
    TrajectoryEvaluationConfig,
    evaluate_tum_trajectories,
    write_evaluation_result,
)
from prml_vslam.pipeline import (
    MethodId,
    PipelineMode,
    RunPlanRequest,
    SessionManager,
    TimestampSource,
)

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Utilities and entry points for the PRML monocular VSLAM project scaffold.",
)
app.add_typer(advio_app, name="advio")

# TODO: do argparsing via PydanticSettings CLI and integrate with typer!
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
PoseRelationOption = Annotated[
    PoseRelationId,
    typer.Option(
        "--pose-relation",
        help="Trajectory component to evaluate with evo.",
        case_sensitive=False,
    ),
]
EvalOutputOption = Annotated[
    Path | None,
    typer.Option("--output-path", help="Optional JSON output path for the trajectory evaluation summary."),
]


def _planning_request_from_cli(
    *,
    experiment_name: str,
    video_path: Path,
    output_dir: Path,
    mode: PipelineMode,
    method: MethodId,
    frame_stride: int,
    dense_mapping: bool,
    compare_to_arcore: bool,
    ground_truth_cloud: bool,
    device_label: str | None,
    frame_rate_hz: float | None,
    timestamp_source: TimestampSource,
    arcore_log_path: Path | None,
    calibration_hint_path: Path | None,
    notes: str | None,
) -> RunPlanRequest:
    """Build the shared planning request used by plan and materialize commands."""
    return build_run_request(
        experiment_name=experiment_name,
        video_path=video_path,
        output_dir=output_dir,
        mode=mode,
        method=method,
        frame_stride=frame_stride,
        dense_mapping=dense_mapping,
        compare_to_arcore=compare_to_arcore,
        ground_truth_cloud=ground_truth_cloud,
        capture=build_capture_metadata(
            device_label=device_label,
            frame_rate_hz=frame_rate_hz,
            timestamp_source=timestamp_source,
            arcore_log_path=arcore_log_path,
            calibration_hint_path=calibration_hint_path,
            notes=notes,
        ),
    )


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
    request = _planning_request_from_cli(
        experiment_name=experiment_name,
        video_path=video_path,
        output_dir=output_dir,
        mode=mode,
        method=method,
        frame_stride=frame_stride,
        dense_mapping=dense_mapping,
        compare_to_arcore=compare_to_arcore,
        ground_truth_cloud=ground_truth_cloud,
        device_label=device_label,
        frame_rate_hz=frame_rate_hz,
        timestamp_source=timestamp_source,
        arcore_log_path=arcore_log_path,
        calibration_hint_path=calibration_hint_path,
        notes=notes,
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
    request = _planning_request_from_cli(
        experiment_name=experiment_name,
        video_path=video_path,
        output_dir=output_dir,
        mode=mode,
        method=method,
        frame_stride=frame_stride,
        dense_mapping=dense_mapping,
        compare_to_arcore=compare_to_arcore,
        ground_truth_cloud=ground_truth_cloud,
        device_label=device_label,
        frame_rate_hz=frame_rate_hz,
        timestamp_source=timestamp_source,
        arcore_log_path=arcore_log_path,
        calibration_hint_path=calibration_hint_path,
        notes=notes,
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
    request = build_run_request(
        experiment_name=experiment_name,
        video_path=video_path,
        output_dir=output_dir,
        mode=PipelineMode.BATCH,
        method=method,
        frame_stride=frame_stride,
        dense_mapping=False,
        compare_to_arcore=False,
        ground_truth_cloud=False,
    )
    execute_offline_run(
        manager=SessionManager(),
        method=method,
        artifact_root=ensure_offline_workspace(request),
        video_path=video_path,
        frame_stride=frame_stride,
        max_frames=max_frames,
        estimated_frames=estimate_offline_frames(video_path, frame_stride=frame_stride, max_frames=max_frames),
        title="Offline pipeline run",
        summary_title="Offline pipeline summary",
        progress_description="Running offline pipeline",
    )


@app.command("run-streaming-demo")
def run_streaming_demo(
    output_dir: OutputDirOption = Path("artifacts"),
    method: MethodOption = MethodId.VISTA_SLAM,
    num_frames: Annotated[int, typer.Option("--num-frames", min=1, help="Synthetic frames to push.")] = 50,
) -> None:
    """Push synthetic frames through the streaming pipeline to demo session management."""
    artifact_root = Path(output_dir) / "streaming-demo" / "streaming" / method.value
    execute_streaming_demo(
        manager=SessionManager(),
        method=method,
        artifact_root=artifact_root,
        num_frames=num_frames,
    )


@app.command("evaluate-trajectory")
def evaluate_trajectory(
    reference_path: Annotated[Path, typer.Argument(help="Reference trajectory in TUM format.")],
    estimate_path: Annotated[Path, typer.Argument(help="Estimated trajectory in TUM format.")],
    pose_relation: PoseRelationOption = PoseRelationId.TRANSLATION_PART,
    align: Annotated[bool, typer.Option("--align/--no-align", help="Apply rigid alignment before evaluation.")] = True,
    correct_scale: Annotated[
        bool,
        typer.Option("--correct-scale/--no-correct-scale", help="Allow scale correction before evaluation."),
    ] = True,
    max_diff_s: Annotated[
        float,
        typer.Option("--max-diff-s", min=0.0001, help="Maximum timestamp association difference in seconds."),
    ] = 0.02,
    output_path: EvalOutputOption = None,
) -> None:
    """Evaluate two TUM trajectories with evo and print the resulting summary."""
    config = TrajectoryEvaluationConfig(
        reference_path=reference_path,
        estimate_path=estimate_path,
        pose_relation=pose_relation,
        align=align,
        correct_scale=correct_scale,
        max_diff_s=max_diff_s,
    )
    try:
        result = evaluate_tum_trajectories(config)
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc
    if output_path is not None:
        write_evaluation_result(result, output_path)
    print_eval_summary(config, result.stats, matching_pairs=result.matching_pairs)


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
