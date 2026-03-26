"""CLI entry point for the project scaffold."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

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


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
