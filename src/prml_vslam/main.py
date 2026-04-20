"""CLI entry point for the project scaffold."""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, TextIO

import typer

from prml_vslam.benchmark import ReferenceSource
from prml_vslam.datasets.advio import (
    AdvioDatasetService,
    AdvioDownloadPreset,
    AdvioDownloadRequest,
    AdvioModality,
    AdvioPoseFrameMode,
    AdvioPoseSource,
)
from prml_vslam.io import Record3DStreamConfig
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts.request import DatasetSourceSpec, VideoSourceSpec, build_run_request
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState, StreamingRunSnapshot
from prml_vslam.pipeline.demo import (
    build_advio_demo_request,
    build_runtime_source_from_request,
    load_run_request_toml,
    persist_advio_demo_request,
)
from prml_vslam.pipeline.run_service import RunService
from prml_vslam.utils.console import Console
from prml_vslam.utils.path_config import PathConfig, get_path_config

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
pipeline_demo_console = Console("pipeline.demo")

app.add_typer(advio_app, name="advio")


@dataclass(slots=True)
class _RerunViewerProcess:
    """CLI-owned Rerun web viewer subprocess plus its stdout forwarder thread."""

    process: subprocess.Popen[str]
    forwarder: threading.Thread


def _build_rerun_viewer_command(*, request: RunRequest, path_config: PathConfig) -> list[str]:
    """Build the authoritative `uv run ... rerun --serve-web` command."""
    command = ["uv", "run", "--extra", "vista", "rerun"]
    blueprint_path = request.visualization.viewer_blueprint_path
    if blueprint_path is not None:
        command.append(path_config.resolve_repo_path(blueprint_path).as_posix())
    command.append("--serve-web")
    return command


def _forward_rerun_viewer_stdout(*, stream: TextIO, target: TextIO = sys.stdout) -> None:
    """Forward merged child output into the main process stdout."""
    try:
        for line in stream:
            target.write(f"[rerun] {line}")
            if not line.endswith("\n"):
                target.write("\n")
            target.flush()
    finally:
        stream.close()


def _launch_rerun_viewer(*, request: RunRequest, path_config: PathConfig) -> _RerunViewerProcess | None:
    """Start the best-effort CLI-owned Rerun web viewer when configured."""
    if not request.visualization.connect_live_viewer:
        return None
    command = _build_rerun_viewer_command(request=request, path_config=path_config)
    try:
        process = subprocess.Popen(
            command,
            cwd=path_config.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        console.warning("Failed to launch the Rerun viewer subprocess: %s", exc)
        return None
    if process.stdout is None:
        console.warning("Rerun viewer started without a stdout pipe; continuing without forwarded viewer logs.")
        if process.poll() is None:
            process.terminate()
        return None
    forwarder = threading.Thread(
        target=_forward_rerun_viewer_stdout,
        kwargs={"stream": process.stdout},
        daemon=True,
        name="rerun-viewer-stdout",
    )
    forwarder.start()
    time.sleep(0.2)
    if process.poll() is not None:
        console.warning(
            "Rerun viewer exited early with code %s; continuing without auto-launched live viewer.",
            process.returncode,
        )
        return None
    return _RerunViewerProcess(process=process, forwarder=forwarder)


def _shutdown_rerun_viewer(viewer: _RerunViewerProcess | None) -> None:
    """Terminate the CLI-owned Rerun viewer subprocess and release its pipe."""
    if viewer is None:
        return
    process = viewer.process
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5.0)
    if process.stdout is not None and not process.stdout.closed:
        process.stdout.close()
    viewer.forwarder.join(timeout=1.0)


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
        ".artifacts"
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
    emit_dense_points: Annotated[
        bool,
        typer.Option("--dense/--no-dense", help="Whether the plan should include dense map export."),
    ] = True,
    emit_sparse_points: Annotated[
        bool,
        typer.Option("--sparse/--no-sparse", help="Whether the plan should include sparse geometry export."),
    ] = True,
    trajectory_evaluation: Annotated[
        bool,
        typer.Option("--trajectory-eval/--no-trajectory-eval", help="Whether to plan trajectory evaluation."),
    ] = False,
    trajectory_baseline: Annotated[
        ReferenceSource,
        typer.Option(
            "--trajectory-baseline",
            help="Reference source selected for trajectory evaluation.",
            case_sensitive=False,
        ),
    ] = ReferenceSource.GROUND_TRUTH,
    reference_reconstruction: Annotated[
        bool,
        typer.Option(
            "--reference/--no-reference",
            help="Whether the plan reserves a reference reconstruction stage.",
        ),
    ] = False,
    evaluate_efficiency: Annotated[
        bool,
        typer.Option("--efficiency/--no-efficiency", help="Whether the plan reserves efficiency metrics."),
    ] = False,
) -> None:
    """Build a typed benchmark run plan from the CLI."""
    request = build_run_request(
        experiment_name=experiment_name,
        output_dir=output_dir,
        source=VideoSourceSpec(video_path=video_path, frame_stride=frame_stride),
        method=method,
        emit_dense_points=emit_dense_points,
        emit_sparse_points=emit_sparse_points,
        reference_enabled=reference_reconstruction,
        trajectory_eval_enabled=trajectory_evaluation,
        trajectory_baseline=trajectory_baseline,
        evaluate_cloud=emit_dense_points and reference_reconstruction,
        evaluate_efficiency=evaluate_efficiency,
        connect_live_viewer=True,
    )
    plan = request.build()
    console.plog(plan.model_dump(mode="json"))


@app.command("plan-run-config")
def plan_run_config(
    config_path: Annotated[
        Path,
        typer.Argument(
            help="Path to a RunRequest TOML file (repo-relative paths are resolved via PathConfig).",
        ),
    ],
    dataset_frame_stride: Annotated[
        int | None,
        typer.Option("--dataset-frame-stride", min=1, help="Override dataset frame stride from the TOML source."),
    ] = None,
    dataset_target_fps: Annotated[
        float | None,
        typer.Option("--dataset-target-fps", min=0.01, help="Override dataset target FPS from the TOML source."),
    ] = None,
) -> None:
    """Build a typed benchmark run plan from a TOML config file."""
    path_config = get_path_config()
    try:
        request = load_run_request_toml(path_config=path_config, config_path=config_path)
        request = _apply_dataset_sampling_overrides(
            request,
            dataset_frame_stride=dataset_frame_stride,
            dataset_target_fps=dataset_target_fps,
        )
        plan = request.build(path_config)
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc
    console.plog(plan.model_dump(mode="json"))


@app.command("run-config")
def run_config(
    config_path: Annotated[
        Path,
        typer.Argument(
            help="Path to an offline RunRequest TOML file (repo-relative paths are resolved via PathConfig).",
        ),
    ],
    dataset_frame_stride: Annotated[
        int | None,
        typer.Option("--dataset-frame-stride", min=1, help="Override dataset frame stride from the TOML source."),
    ] = None,
    dataset_target_fps: Annotated[
        float | None,
        typer.Option("--dataset-target-fps", min=0.01, help="Override dataset target FPS from the TOML source."),
    ] = None,
) -> None:
    """Run one offline or streaming pipeline request from a TOML config file."""
    path_config = get_path_config()
    run_service: RunService | None = None
    viewer: _RerunViewerProcess | None = None
    request: RunRequest | None = None
    snapshot = RunSnapshot()
    preserve_local_head = False
    try:
        request = load_run_request_toml(path_config=path_config, config_path=config_path)
        request = _apply_dataset_sampling_overrides(
            request,
            dataset_frame_stride=dataset_frame_stride,
            dataset_target_fps=dataset_target_fps,
        )
        viewer = _launch_rerun_viewer(request=request, path_config=path_config)
        runtime_source = build_runtime_source_from_request(request=request, path_config=path_config)
        run_service = RunService(path_config=path_config)
        run_service.start_run(request=request, runtime_source=runtime_source)
        snapshot = _wait_for_pipeline_terminal_snapshot(run_service, poll_interval_seconds=0.2)
        preserve_local_head = (
            snapshot.state is RunState.COMPLETED and request.runtime.ray.local_head_lifecycle == "reusable"
        )
    except KeyboardInterrupt as exc:
        if run_service is not None:
            run_service.stop_run()
            snapshot = run_service.snapshot()
            _print_pipeline_demo_snapshot(snapshot)
        raise typer.Exit(code=130) from exc
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc
    finally:
        if run_service is not None:
            run_service.shutdown(preserve_local_head=preserve_local_head)
        _shutdown_rerun_viewer(viewer)
    _print_pipeline_demo_snapshot(snapshot)
    if snapshot.state is RunState.FAILED:
        raise typer.Exit(code=1)


@app.command("write-demo-config")
def write_demo_config(
    sequence_id: Annotated[
        int | None,
        typer.Option(
            "--sequence",
            help="ADVIO sequence id to use. Defaults to the first replay-ready local scene.",
        ),
    ] = None,
    mode: Annotated[
        PipelineMode,
        typer.Option(
            "--mode",
            help="Persist an offline or streaming ADVIO demo request.",
            case_sensitive=False,
        ),
    ] = PipelineMode.OFFLINE,
    method: Annotated[
        MethodId,
        typer.Option(
            "--method",
            help="Method id stored in the persisted demo request.",
            case_sensitive=False,
        ),
    ] = MethodId.VISTA,
    config_path: Annotated[
        Path | None,
        typer.Option(
            "--config-path",
            help="Optional output TOML path. Bare filenames resolve under .configs/pipelines/.",
        ),
    ] = None,
    dataset_frame_stride: Annotated[
        int,
        typer.Option("--dataset-frame-stride", min=1, help="Dataset frame stride stored in the demo request."),
    ] = 1,
    dataset_target_fps: Annotated[
        float | None,
        typer.Option("--dataset-target-fps", min=0.01, help="Dataset target FPS stored in the demo request."),
    ] = None,
) -> None:
    """Persist the canonical ADVIO demo request as TOML."""
    path_config = get_path_config()
    advio_service = AdvioDatasetService(path_config)
    resolved_sequence_id = _resolve_demo_sequence_id(advio_service, explicit_sequence_id=sequence_id)
    scene = advio_service.scene(resolved_sequence_id)
    resolved_config_path = persist_advio_demo_request(
        path_config=path_config,
        sequence_id=scene.sequence_slug,
        mode=mode,
        method=method,
        dataset_frame_stride=dataset_frame_stride,
        dataset_target_fps=dataset_target_fps,
        config_path=config_path,
    )
    console.plog(
        {
            "config_path": str(resolved_config_path),
            "sequence_id": scene.sequence_slug,
            "mode": mode.value,
            "method": method.value,
        }
    )


@app.command("record3d-devices")
def record3d_devices() -> None:
    """List USB-connected Record3D devices visible to the bindings."""
    try:
        session = Record3DStreamConfig().setup_target()
        if session is None:
            raise RuntimeError("Failed to initialize the Record3D session.")
        devices = session.list_devices()
    except RuntimeError as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc

    if not devices:
        console.warning(
            "No Record3D devices detected. Connect the iPhone via USB, open Record3D, and enable USB Streaming mode."
        )
        return

    console.plog([device.model_dump(mode="json") for device in devices])


@app.command("pipeline-demo")
def pipeline_demo(
    sequence_id: Annotated[
        int | None,
        typer.Option(
            "--sequence",
            help="ADVIO sequence id to replay. Defaults to the first replay-ready local scene.",
        ),
    ] = None,
    method: Annotated[
        MethodId,
        typer.Option(
            "--method",
            help="SLAM backend used by the bounded demo.",
            case_sensitive=False,
        ),
    ] = MethodId.VISTA,
    pose_source: Annotated[
        AdvioPoseSource,
        typer.Option(
            "--pose-source",
            help="Pose source injected into ADVIO replay packets.",
            case_sensitive=False,
        ),
    ] = AdvioPoseSource.GROUND_TRUTH,
    pose_frame_mode: Annotated[
        AdvioPoseFrameMode,
        typer.Option(
            "--pose-frame-mode",
            help="Frame semantics used when serving ADVIO replay poses.",
            case_sensitive=False,
        ),
    ] = AdvioPoseFrameMode.PROVIDER_WORLD,
    respect_video_rotation: Annotated[
        bool,
        typer.Option(
            "--respect-video-rotation/--ignore-video-rotation",
            help="Whether to honor ADVIO video rotation metadata during replay.",
        ),
    ] = False,
    dataset_frame_stride: Annotated[
        int,
        typer.Option("--dataset-frame-stride", min=1, help="Frame stride used for ADVIO replay packets."),
    ] = 1,
    dataset_target_fps: Annotated[
        float | None,
        typer.Option("--dataset-target-fps", min=0.01, help="Target FPS used for ADVIO replay packets."),
    ] = None,
    poll_interval_seconds: Annotated[
        float,
        typer.Option(
            "--poll-interval",
            min=0.05,
            help="Seconds between status polls while the demo session is active.",
        ),
    ] = 0.2,
) -> None:
    """Run the bounded ADVIO replay demo without starting Streamlit."""
    path_config = get_path_config()
    advio_service = AdvioDatasetService(path_config)
    resolved_sequence_id = _resolve_demo_sequence_id(advio_service, explicit_sequence_id=sequence_id)
    scene = advio_service.scene(resolved_sequence_id)
    request = build_advio_demo_request(
        path_config=path_config,
        sequence_id=scene.sequence_slug,
        mode=PipelineMode.STREAMING,
        method=method,
        pose_source=pose_source,
        pose_frame_mode=pose_frame_mode,
        respect_video_rotation=respect_video_rotation,
        dataset_frame_stride=dataset_frame_stride,
        dataset_target_fps=dataset_target_fps,
    )
    source = build_runtime_source_from_request(request=request, path_config=path_config)
    run_service = RunService(path_config=path_config)
    pipeline_demo_console.info(
        "Starting pipeline demo for %s (%s, %s).",
        scene.display_name,
        PipelineMode.STREAMING.value,
        method.value,
    )
    try:
        run_service.start_run(request=request, runtime_source=source)
        snapshot = _wait_for_pipeline_terminal_snapshot(
            run_service,
            poll_interval_seconds=poll_interval_seconds,
        )
    except KeyboardInterrupt as exc:
        pipeline_demo_console.warning("Interrupted; stopping the active pipeline demo.")
        run_service.stop_run()
        snapshot = run_service.snapshot()
        _print_pipeline_demo_snapshot(snapshot)
        raise typer.Exit(code=130) from exc
    _print_pipeline_demo_snapshot(snapshot)
    if snapshot.state is RunState.FAILED:
        raise typer.Exit(code=1)


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


def _resolve_demo_sequence_id(service: AdvioDatasetService, *, explicit_sequence_id: int | None) -> int:
    """Resolve one replay-ready ADVIO sequence for the CLI demo."""
    if explicit_sequence_id is not None:
        return explicit_sequence_id
    previewable_ids = [status.scene.sequence_id for status in service.local_scene_statuses() if status.replay_ready]
    if not previewable_ids:
        raise typer.BadParameter(
            "No replay-ready ADVIO scenes were found. Download the streaming bundle first or pass --sequence."
        )
    return previewable_ids[0]


def _apply_dataset_sampling_overrides(
    request: RunRequest,
    *,
    dataset_frame_stride: int | None,
    dataset_target_fps: float | None,
) -> RunRequest:
    if dataset_frame_stride is None and dataset_target_fps is None:
        return request
    if dataset_frame_stride is not None and dataset_target_fps is not None:
        raise typer.BadParameter("Configure either --dataset-frame-stride or --dataset-target-fps, not both.")
    if not isinstance(request.source, DatasetSourceSpec):
        raise typer.BadParameter("Dataset sampling overrides require a dataset-backed source.")
    source = request.source.model_copy(
        update={
            "frame_stride": 1 if dataset_target_fps is not None else dataset_frame_stride,
            "target_fps": dataset_target_fps,
        }
    )
    return request.model_copy(update={"source": DatasetSourceSpec.model_validate(source.model_dump(mode="python"))})


def _wait_for_pipeline_terminal_snapshot(
    run_service: RunService,
    *,
    poll_interval_seconds: float,
) -> RunSnapshot:
    """Poll the run service until the current demo session reaches a terminal state."""
    previous_state: RunState | None = None
    previous_received_frames = -1
    while True:
        snapshot = run_service.snapshot()
        if snapshot.state is not previous_state:
            plan_run_id = None if snapshot.plan is None else snapshot.plan.run_id
            pipeline_demo_console.info(
                "Pipeline demo state: %s%s", snapshot.state.value, "" if plan_run_id is None else f" ({plan_run_id})"
            )
            previous_state = snapshot.state
        if isinstance(snapshot, StreamingRunSnapshot) and snapshot.received_frames != previous_received_frames:
            pipeline_demo_console.info(
                "Frames=%d sparse=%d dense=%d",
                snapshot.received_frames,
                snapshot.num_sparse_points,
                snapshot.num_dense_points,
            )
            previous_received_frames = snapshot.received_frames
        if snapshot.state not in {RunState.PREPARING, RunState.RUNNING}:
            return snapshot
        time.sleep(poll_interval_seconds)


def _print_pipeline_demo_snapshot(snapshot: RunSnapshot) -> None:
    """Render the final CLI demo snapshot in a compact structured form."""
    payload = {
        "state": snapshot.state.value,
        "error_message": snapshot.error_message or None,
        "plan": None if snapshot.plan is None else snapshot.plan.model_dump(mode="json"),
        "sequence_manifest": None
        if snapshot.sequence_manifest is None
        else snapshot.sequence_manifest.model_dump(mode="json"),
        "slam": None if snapshot.slam is None else snapshot.slam.model_dump(mode="json"),
        "summary": None if snapshot.summary is None else snapshot.summary.model_dump(mode="json"),
    }
    if isinstance(snapshot, StreamingRunSnapshot):
        payload["received_frames"] = snapshot.received_frames
        payload["num_sparse_points"] = snapshot.num_sparse_points
        payload["num_dense_points"] = snapshot.num_dense_points
    console.plog(payload)


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
