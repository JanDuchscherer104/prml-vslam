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
    Record3DStreamConfig,
    Record3DTimeoutError,
)
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import (
    BenchmarkEvaluationConfig,
    DenseConfig,
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
    experiment_name: Annotated[str, typer.Argument(help="Human-readable experiment name.")],
    video_path: Annotated[Path, typer.Argument(help="Path to the input video.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Root directory for benchmark artifacts.")] = Path(
        "artifacts"
    ),
    method: Annotated[
        MethodId,
        typer.Option(
            "--method",
            help="External monocular VSLAM backend to plan for.",
            case_sensitive=False,
        ),
    ] = MethodId.VISTA,
    frame_stride: Annotated[int, typer.Option(min=1, max=30, help="Frame subsampling stride.")] = 1,
    dense_mapping: Annotated[
        bool,
        typer.Option("--dense/--no-dense", help="Whether the plan should include dense map export."),
    ] = True,
    compare_to_arcore: Annotated[
        bool,
        typer.Option(
            "--arcore/--no-arcore",
            help="Whether the plan assumes ARCore comparison data is available.",
        ),
    ] = True,
    ground_truth_cloud: Annotated[
        bool,
        typer.Option(
            "--reference-cloud/--no-reference-cloud",
            help="Whether the plan reserves a reference reconstruction stage.",
        ),
    ] = True,
) -> None:
    """Build a typed benchmark run plan from the CLI."""
    request = RunRequest(
        experiment_name=experiment_name,
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
    plan = request.build()
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
    sequence_ids: Annotated[
        list[int] | None,
        typer.Option("--sequence", help="Repeat to select one or more ADVIO sequence ids. Omit to target all scenes."),
    ] = None,
    preset: Annotated[
        AdvioDownloadPreset,
        typer.Option(
            "--preset",
            help="Curated modality bundle used when no explicit modality override is provided.",
            case_sensitive=False,
        ),
    ] = AdvioDownloadPreset.OFFLINE,
    modalities: Annotated[
        list[AdvioModality] | None,
        typer.Option(
            "--modality",
            help="Repeat to override the preset with explicit modality groups.",
            case_sensitive=False,
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite/--reuse",
            help="Whether to re-download cached ZIPs and replace extracted files.",
        ),
    ] = False,
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
