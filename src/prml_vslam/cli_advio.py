"""ADVIO dataset commands for the project CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from prml_vslam.cli_support import (
    console,
    default_advio_experiment_name,
    ensure_offline_workspace,
    estimate_sequence_frames,
    execute_offline_run,
    resolve_advio_sequence,
)
from prml_vslam.datasets import AdvioSequenceConfig, download_advio_sequence
from prml_vslam.pipeline import MethodId, SessionManager

advio_app = typer.Typer(help="ADVIO dataset download, execution, and export helpers.")

SequenceIdArg = Annotated[
    int,
    typer.Argument(min=1, max=23, help="ADVIO sequence id in the official range [1, 23]."),
]
DatasetRootOption = Annotated[
    Path,
    typer.Option("--dataset-root", help="Root directory for ADVIO archives and extracted sequences."),
]
KeepArchiveOption = Annotated[
    bool,
    typer.Option(
        "--keep-archive/--discard-archive",
        help="Whether to keep the downloaded ADVIO ZIP after extraction.",
    ),
]
ForceOption = Annotated[
    bool,
    typer.Option(
        "--force/--no-force",
        help="Whether to overwrite existing local ADVIO downloads and extracted data.",
    ),
]
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
MaxFramesOption = Annotated[
    int | None,
    typer.Option("--max-frames", min=1, help="Maximum number of frames to decode."),
]
ExperimentNameOption = Annotated[
    str | None,
    typer.Option("--experiment-name", help="Optional experiment name override."),
]
TumOutputOption = Annotated[Path | None, typer.Option("--output-path", help="Destination TUM path.")]


@advio_app.command("download")
def advio_download(
    sequence_id: SequenceIdArg,
    dataset_root: DatasetRootOption = Path("data/advio"),
    keep_archive: KeepArchiveOption = True,
    force: ForceOption = False,
) -> None:
    """Download and extract one official ADVIO sequence."""
    try:
        sequence = download_advio_sequence(
            AdvioSequenceConfig(dataset_root=dataset_root, sequence_id=sequence_id),
            keep_archive=keep_archive,
            force=force,
        )
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc
    summary = Table(title=f"ADVIO {sequence_id:02d}", show_header=False, box=None, pad_edge=False)
    summary.add_column("Field", style="bold")
    summary.add_column("Value")
    summary.add_row("Dataset root", str(dataset_root))
    summary.add_row("Sequence dir", str(sequence.config.sequence_dir))
    summary.add_row("Archive", str(sequence.config.archive_path if keep_archive else "(discarded)"))
    summary.add_row("Video", str(sequence.config.video_path))
    summary.add_row("Ground truth", str(sequence.config.ground_truth_path))
    summary.add_row("Calibration", str(sequence.config.calibration_hint_path))
    console.print(summary)


@advio_app.command("run")
def advio_run(
    sequence_id: SequenceIdArg,
    dataset_root: DatasetRootOption = Path("data/advio"),
    output_dir: OutputDirOption = Path("artifacts"),
    method: MethodOption = MethodId.VISTA_SLAM,
    frame_stride: FrameStrideOption = 1,
    max_frames: MaxFramesOption = None,
    experiment_name: ExperimentNameOption = None,
) -> None:
    """Run the offline pipeline on one ADVIO iPhone video sequence."""
    try:
        sequence = resolve_advio_sequence(sequence_id, dataset_root)
    except FileNotFoundError as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc
    frame_timestamps_ns = sequence.load_frame_timestamps_ns()
    request = sequence.build_run_request(
        experiment_name=experiment_name or default_advio_experiment_name(sequence_id),
        output_dir=output_dir,
        method=method,
        frame_stride=frame_stride,
    )
    execute_offline_run(
        manager=SessionManager(),
        method=method,
        artifact_root=ensure_offline_workspace(request),
        video_path=sequence.config.video_path,
        frame_stride=frame_stride,
        max_frames=max_frames,
        estimated_frames=estimate_sequence_frames(
            frame_timestamps_ns,
            frame_stride=frame_stride,
            max_frames=max_frames,
        ),
        title=f"ADVIO offline run ({sequence.config.sequence_name})",
        summary_title="ADVIO offline summary",
        progress_description="Running ADVIO pipeline",
        frame_timestamps_ns=frame_timestamps_ns,
    )


@advio_app.command("export-gt")
def advio_export_gt(
    sequence_id: SequenceIdArg,
    dataset_root: DatasetRootOption = Path("data/advio"),
    output_path: TumOutputOption = None,
) -> None:
    """Convert ADVIO ground truth to TUM format plus a small JSON sidecar."""
    try:
        sequence = resolve_advio_sequence(sequence_id, dataset_root)
    except FileNotFoundError as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc
    tum_path = output_path or (sequence.config.sequence_dir / "ground-truth" / "ground_truth.tum")
    sidecar_path = tum_path.with_suffix(".metadata.json")
    sequence.write_ground_truth_tum(tum_path)
    sequence.write_ground_truth_sidecar(sidecar_path)
    summary = Table(title=f"ADVIO {sequence_id:02d} ground truth export", show_header=False, box=None, pad_edge=False)
    summary.add_column("Field", style="bold")
    summary.add_column("Value")
    summary.add_row("TUM", str(tum_path))
    summary.add_row("Sidecar", str(sidecar_path))
    console.print(summary)
