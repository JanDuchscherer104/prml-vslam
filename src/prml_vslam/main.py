"""CLI entry point for the project scaffold."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from prml_vslam.io import (
    Record3DConnectionError,
    Record3DDependencyError,
    Record3DPreviewConfig,
    Record3DStreamConfig,
    Record3DTimeoutError,
)
from prml_vslam.pipeline import MethodId, PipelinePlannerService, RunPlanRequest
from prml_vslam.utils.console import Console

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Utilities and entry points for the PRML monocular VSLAM project scaffold.",
)
console = Console(__name__)
planner = PipelinePlannerService()

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
DeviceIndexOption = Annotated[
    int,
    typer.Option("--device-index", min=0, help="Zero-based index into the connected Record3D devices."),
]
FrameTimeoutOption = Annotated[
    float,
    typer.Option("--frame-timeout", min=0.1, help="Seconds to wait for the next Record3D frame."),
]
MaxFramesOption = Annotated[
    int | None,
    typer.Option("--max-frames", min=1, help="Optional number of frames to preview before stopping."),
]
ConfidenceOption = Annotated[
    bool,
    typer.Option(
        "--confidence/--no-confidence",
        help="Whether to open a preview window for the Record3D confidence map.",
    ),
]


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
    method: MethodOption = MethodId.VISTA_SLAM,
    frame_stride: FrameStrideOption = 1,
    dense_mapping: DenseOption = True,
    compare_to_arcore: ArcoreOption = True,
    ground_truth_cloud: ReferenceCloudOption = True,
) -> None:
    """Build a typed benchmark run plan from the CLI."""
    request = RunPlanRequest(
        experiment_name=experiment_name,
        video_path=video_path,
        output_dir=output_dir,
        method=method,
        frame_stride=frame_stride,
        enable_dense_mapping=dense_mapping,
        compare_to_arcore=compare_to_arcore,
        build_ground_truth_cloud=ground_truth_cloud,
    )
    plan = planner.build_plan(request)
    console.plog(plan.model_dump(mode="json"))


@app.command("record3d-devices")
def record3d_devices() -> None:
    """List USB-connected Record3D devices visible to the bindings."""
    try:
        session = Record3DStreamConfig().setup_target()
        if session is None:
            raise Record3DConnectionError("Failed to initialize the Record3D session.")
        devices = session.list_devices()
    except (Record3DConnectionError, Record3DDependencyError, Record3DTimeoutError) as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc

    if not devices:
        console.warning(
            "No Record3D devices detected. Connect the iPhone via USB, open Record3D, and enable USB Streaming mode."
        )
        return

    console.plog([device.model_dump(mode="json") for device in devices])


@app.command("record3d-preview")
def record3d_preview(
    device_index: DeviceIndexOption = 0,
    frame_timeout: FrameTimeoutOption = 5.0,
    max_frames: MaxFramesOption = None,
    show_confidence: ConfidenceOption = True,
) -> None:
    """Open a simple OpenCV preview for the live Record3D RGBD stream."""
    preview = Record3DPreviewConfig(
        stream=Record3DStreamConfig(
            device_index=device_index,
            frame_timeout_seconds=frame_timeout,
        ),
        max_frames=max_frames,
        show_confidence=show_confidence,
    )

    try:
        app_instance = preview.setup_target()
        if app_instance is None:
            raise Record3DConnectionError("Failed to initialize the Record3D preview app.")
        app_instance.run()
    except (Record3DConnectionError, Record3DDependencyError, Record3DTimeoutError) as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
