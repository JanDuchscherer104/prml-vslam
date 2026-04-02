"""CLI entry point for the project scaffold."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from prml_vslam.datasets import AdvioDatasetService
from prml_vslam.datasets.advio import AdvioDownloadPreset, AdvioDownloadRequest, AdvioModality
from prml_vslam.io import (
    Record3DConnectionError,
    Record3DDependencyError,
    Record3DPreviewConfig,
    Record3DStreamConfig,
    Record3DTimeoutError,
)
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import (
    BenchmarkEvaluationConfig,
    DenseConfig,
    PipelineMode,
    PipelinePlannerService,
    ReferenceConfig,
    RunRequest,
    TrackingConfig,
    VideoSourceSpec,
)
from prml_vslam.utils.console import Console
from prml_vslam.utils.path_config import get_path_config

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Utilities and entry points for the PRML monocular VSLAM project scaffold.",
)
advio_app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="ADVIO dataset inspection and download helpers.",
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
AdvioSequenceOption = Annotated[
    list[int] | None,
    typer.Option(
        "--sequence",
        help="Repeat to select one or more ADVIO sequence ids. Omit to target all scenes.",
    ),
]
AdvioPresetOption = Annotated[
    AdvioDownloadPreset,
    typer.Option(
        "--preset",
        help="Curated modality bundle used when no explicit modality override is provided.",
        case_sensitive=False,
    ),
]
AdvioModalityOption = Annotated[
    list[AdvioModality] | None,
    typer.Option(
        "--modality",
        help="Repeat to override the preset with explicit modality groups.",
        case_sensitive=False,
    ),
]
OverwriteExistingOption = Annotated[
    bool,
    typer.Option(
        "--overwrite/--reuse",
        help="Whether to re-download cached ZIPs and replace extracted files.",
    ),
]

app.add_typer(advio_app, name="advio")


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
    method: MethodOption = MethodId.VISTA,
    frame_stride: FrameStrideOption = 1,
    dense_mapping: DenseOption = True,
    compare_to_arcore: ArcoreOption = True,
    ground_truth_cloud: ReferenceCloudOption = True,
) -> None:
    """Build a typed benchmark run plan from the CLI."""
    request = RunRequest(
        experiment_name=experiment_name,
        mode=PipelineMode.OFFLINE,
        output_dir=output_dir,
        source=VideoSourceSpec(video_path=video_path, frame_stride=frame_stride),
        tracking=TrackingConfig(method=method),
        dense=DenseConfig(enabled=dense_mapping),
        reference=ReferenceConfig(enabled=ground_truth_cloud),
        evaluation=BenchmarkEvaluationConfig(
            compare_to_arcore=compare_to_arcore,
            evaluate_cloud=dense_mapping and ground_truth_cloud,
            evaluate_efficiency=True,
        ),
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


@advio_app.command("summary")
def advio_summary() -> None:
    """Print committed and local ADVIO dataset coverage."""
    service = AdvioDatasetService(get_path_config())
    summary = service.summarize()
    payload = {
        "dataset_root": str(service.dataset_root),
        "upstream": service.catalog.upstream.model_dump(mode="json"),
        "summary": summary.model_dump(mode="json"),
        "local_sequence_ids": [
            status.scene.sequence_id for status in service.local_scene_statuses() if status.sequence_dir
        ],
    }
    console.plog(payload)


@advio_app.command("download")
def advio_download(
    sequence_ids: AdvioSequenceOption = None,
    preset: AdvioPresetOption = AdvioDownloadPreset.OFFLINE,
    modalities: AdvioModalityOption = None,
    overwrite: OverwriteExistingOption = False,
) -> None:
    """Download selected ADVIO scene archives and extract only requested modality bundles."""
    service = AdvioDatasetService(get_path_config())
    try:
        result = service.download(
            AdvioDownloadRequest(
                sequence_ids=[] if sequence_ids is None else sequence_ids,
                preset=preset,
                modalities=[] if modalities is None else modalities,
                overwrite=overwrite,
            )
        )
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc

    payload = {
        "result": result.model_dump(mode="json"),
        "summary": service.summarize().model_dump(mode="json"),
    }
    console.plog(payload)


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
