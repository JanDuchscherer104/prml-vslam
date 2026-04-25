"""CLI entry point for the project scaffold."""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, TextIO

import click
import typer
from pydantic import ValidationError
from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.table import Table
from typer.core import TyperCommand

from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.config import RunConfig, build_run_config
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.demo import (
    build_advio_demo_run_config,
    build_runtime_source_from_run_config,
    load_run_config_toml,
    persist_advio_demo_run_config,
)
from prml_vslam.pipeline.run_bundle import RunBundleCollisionPolicy, export_run_bundle, import_run_bundle
from prml_vslam.pipeline.run_service import RunService
from prml_vslam.sources.config import AdvioSourceConfig, SourceBackendConfig, VideoSourceConfig
from prml_vslam.sources.contracts import ReferenceSource
from prml_vslam.sources.datasets.advio import (
    AdvioDatasetService,
    AdvioDownloadPreset,
    AdvioDownloadRequest,
    AdvioModality,
    AdvioPoseFrameMode,
    AdvioPoseSource,
)
from prml_vslam.sources.record3d import Record3DStreamConfig
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

RUN_CONFIG_OVERRIDE_GROUPS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "Run",
        (
            ("--experiment_name", "Run name stored in artifacts and summaries."),
            ("--mode", "Pipeline mode: offline or streaming."),
            ("--output_dir", "Artifact output directory."),
        ),
    ),
    (
        "Source Stage",
        (
            ("--stages.source.enabled", "Enable or disable source normalization."),
            ("--stages.source.backend.source_id", "Source kind: video, advio, tum_rgbd, record3d."),
            ("--stages.source.backend.video_path", "Video source path when source_id=video."),
            ("--stages.source.backend.sequence_id", "Dataset sequence id for ADVIO or TUM RGB-D."),
            ("--stages.source.backend.frame_stride", "Frame sampling stride."),
            ("--stages.source.backend.target_fps", "Frame sampling target FPS."),
            ("--stages.source.backend.replay_mode", "Replay pacing: realtime or fast_as_possible."),
            ("--stages.source.backend.dataset_serving.pose_source", "ADVIO pose provider."),
            ("--stages.source.backend.dataset_serving.pose_frame_mode", "ADVIO replay pose frame mode."),
            ("--stages.source.backend.normalize_video_orientation", "Normalize video display orientation."),
            ("--stages.source.backend.transport", "Record3D transport: usb or wifi."),
            ("--stages.source.backend.device_index", "Record3D USB device index."),
            ("--stages.source.backend.device_address", "Record3D Wi-Fi device address."),
        ),
    ),
    (
        "SLAM Stage",
        (
            ("--stages.slam.enabled", "Enable or disable SLAM."),
            ("--stages.slam.outputs.emit_dense_points", "Materialize dense point outputs."),
            ("--stages.slam.outputs.emit_sparse_points", "Materialize sparse point outputs."),
            ("--stages.slam.backend.method_id", "SLAM backend: vista or mast3r."),
            ("--stages.slam.backend.max_frames", "Frame cap for smoke runs."),
            ("--stages.slam.backend.max_view_num", "ViSTA maximum pose-graph keyframes."),
            ("--stages.slam.backend.flow_thres", "ViSTA keyframe optical-flow threshold."),
            ("--stages.slam.backend.neighbor_edge_num", "ViSTA temporal-neighbor edges."),
            ("--stages.slam.backend.loop_edge_num", "ViSTA loop-closure edges."),
            ("--stages.slam.backend.loop_dist_min", "ViSTA loop candidate minimum frame distance."),
            ("--stages.slam.backend.loop_nms", "ViSTA loop non-maximum suppression window."),
            ("--stages.slam.backend.point_conf_thres", "ViSTA retained point-confidence threshold."),
            ("--stages.slam.backend.rel_pose_thres", "ViSTA relative-pose uncertainty threshold."),
            ("--stages.slam.backend.pgo_every", "ViSTA pose-graph optimization interval."),
            ("--stages.slam.backend.random_seed", "Backend random seed."),
            ("--stages.slam.backend.device", "ViSTA device: auto, cuda, cpu."),
        ),
    ),
    (
        "Downstream Stages",
        (
            ("--stages.align_ground.enabled", "Enable or disable gravity alignment."),
            ("--stages.align_ground.ground.strategy", "Ground-alignment strategy."),
            ("--stages.align_ground.ground.min_confidence", "Minimum ground-plane confidence."),
            ("--stages.evaluate_trajectory.enabled", "Enable trajectory evaluation."),
            ("--stages.evaluate_trajectory.evaluation.baseline_source", "Reference trajectory source."),
            ("--stages.reconstruction.enabled", "Enable reconstruction."),
            ("--stages.reconstruction.backend.method_id", "Reconstruction backend id."),
            ("--stages.reconstruction.backend.voxel_length_m", "TSDF voxel length in meters."),
            ("--stages.reconstruction.backend.sdf_trunc_m", "TSDF truncation distance in meters."),
            ("--stages.reconstruction.backend.depth_sampling_stride", "RGB-D reconstruction sampling stride."),
            ("--stages.reconstruction.backend.extract_mesh", "Extract a mesh after integration."),
            ("--stages.evaluate_cloud.enabled", "Enable dense-cloud diagnostic planning."),
            ("--stages.evaluate_cloud.selection.reference_artifact_key", "Reference cloud artifact key."),
            ("--stages.evaluate_cloud.selection.estimate_artifact_key", "Estimated cloud artifact key."),
            ("--stages.summary.enabled", "Enable summary projection."),
        ),
    ),
    (
        "Visualization",
        (
            ("--visualization.connect_live_viewer", "Attach a live Rerun viewer sink."),
            ("--visualization.export_viewer_rrd", "Export a repo-owned Rerun recording."),
            ("--visualization.grpc_url", "Rerun gRPC endpoint."),
            ("--visualization.viewer_blueprint_path", "Rerun viewer blueprint path."),
            ("--visualization.frusta_history_window_streaming", "Streaming frusta history window."),
            ("--visualization.show_tracking_trajectory", "Show the tracking trajectory."),
            ("--visualization.trajectory_pose_axis_length", "Axis length for trajectory pose transforms."),
            ("--visualization.log_source_rgb", "Log source RGB frames."),
            ("--visualization.log_diagnostic_preview", "Log backend diagnostic previews."),
        ),
    ),
    (
        "Runtime",
        (("--ray_local_head_lifecycle", "Ray local-head lifecycle: ephemeral or reusable."),),
    ),
)


class RunConfigOverrideCommand(TyperCommand):
    """Typer command that appends discoverable RunConfig dotted overrides."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Render normal Typer help followed by RunConfig override paths."""
        super().format_help(ctx, formatter)
        _print_run_config_override_options()


def _print_run_config_override_options() -> None:
    console = RichConsole(file=click.get_text_stream("stdout"))
    for title, options in RUN_CONFIG_OVERRIDE_GROUPS:
        table = Table.grid(padding=(0, 2))
        table.add_column("Option", no_wrap=True)
        table.add_column("Meaning")
        for option, help_text in options:
            table.add_row(option, help_text)
        console.print(Panel(table, title=f"RunConfig Overrides - {title}", expand=False))

    notes = Table.grid(padding=(0, 2))
    notes.add_column("Topic", no_wrap=True)
    notes.add_column("Detail")
    notes.add_row("Value parsing", "JSON first, then string fallback. CLI overrides win over TOML.")
    notes.add_row("Object merge", "--stages.slam.outputs '{\"emit_dense_points\": false}'")
    notes.add_row("String value", "--mode '\"offline\"' or --mode offline")
    console.print(Panel(notes, title="RunConfig Override Syntax", expand=False))


@dataclass(slots=True)
class _RerunViewerProcess:
    """CLI-owned Rerun web viewer subprocess plus its stdout forwarder thread."""

    process: subprocess.Popen[str]
    forwarder: threading.Thread


@dataclass(frozen=True, slots=True)
class _ProcessInfo:
    """Process-table row used by the Rerun viewer cleanup command."""

    pid: int
    ppid: int
    pgid: int
    stat: str
    command: str


_ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class _TimestampedRunLogTee:
    """Mirror terminal output to one timestamped plain-text run log."""

    def __init__(self, *, target: TextIO, log_handle: TextIO, lock: threading.Lock) -> None:
        self._target = target
        self._log_handle = log_handle
        self._lock = lock
        self._pending = ""

    @property
    def encoding(self) -> str:
        return getattr(self._target, "encoding", None) or "utf-8"

    def write(self, text: str) -> int:
        self._target.write(text)
        with self._lock:
            self._pending += text
            while "\n" in self._pending:
                line, self._pending = self._pending.split("\n", maxsplit=1)
                self._write_log_line(line)
        return len(text)

    def flush(self) -> None:
        self._target.flush()
        self._log_handle.flush()

    def isatty(self) -> bool:
        return bool(getattr(self._target, "isatty", lambda: False)())

    def close_log_line(self) -> None:
        with self._lock:
            if self._pending:
                self._write_log_line(self._pending)
                self._pending = ""

    def _write_log_line(self, line: str) -> None:
        timestamp = datetime.now().astimezone().isoformat(timespec="milliseconds")
        self._log_handle.write(f"{timestamp} {_ANSI_ESCAPE_PATTERN.sub('', line)}\n")
        self._log_handle.flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target, name)


@contextmanager
def _capture_run_config_logs(*, path_config: PathConfig, run_id: str) -> Iterator[Path]:
    """Capture one `run-config` command invocation to a timestamped run log."""
    log_dir = path_config.resolve_run_logs_dir(run_id, create=True)
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H:%M:%S")
    log_path = log_dir / f"{timestamp}_{run_id}.log"
    lock = threading.Lock()
    with log_path.open("w", encoding="utf-8") as log_handle:
        stdout_tee = _TimestampedRunLogTee(target=sys.stdout, log_handle=log_handle, lock=lock)
        stderr_tee = _TimestampedRunLogTee(target=sys.stderr, log_handle=log_handle, lock=lock)
        try:
            with redirect_stdout(stdout_tee), redirect_stderr(stderr_tee):
                yield log_path
        finally:
            stdout_tee.close_log_line()
            stderr_tee.close_log_line()
            stdout_tee.flush()
            stderr_tee.flush()


def _build_rerun_viewer_command(*, run_config: RunConfig, path_config: PathConfig) -> list[str]:
    """Build the authoritative `uv run ... rerun --serve-web` command."""
    command = ["uv", "run", "--extra", "vista", "rerun"]
    blueprint_path = run_config.visualization.viewer_blueprint_path
    if blueprint_path is not None:
        command.append(path_config.resolve_repo_path(blueprint_path).as_posix())
    command.append("--serve-web")
    return command


def _forward_rerun_viewer_stdout(*, stream: TextIO, target: TextIO | None = None) -> None:
    """Forward merged child output into the main process stdout."""
    output = sys.stdout if target is None else target
    try:
        for line in stream:
            output.write(f"[rerun] {line}")
            if not line.endswith("\n"):
                output.write("\n")
            output.flush()
    finally:
        stream.close()


def _launch_rerun_viewer(*, run_config: RunConfig, path_config: PathConfig) -> _RerunViewerProcess | None:
    """Start the best-effort CLI-owned Rerun web viewer when configured."""
    if not run_config.visualization.connect_live_viewer:
        return None
    command = _build_rerun_viewer_command(run_config=run_config, path_config=path_config)
    try:
        process = subprocess.Popen(
            command,
            cwd=path_config.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
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
        _terminate_process_group(process, signal.SIGTERM)
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            _terminate_process_group(process, signal.SIGKILL)
            process.wait(timeout=5.0)
    if process.stdout is not None and not process.stdout.closed:
        process.stdout.close()
    viewer.forwarder.join(timeout=1.0)


def _wait_for_rerun_viewer_close(viewer: _RerunViewerProcess | None) -> None:
    """Keep an auto-launched viewer alive after the pipeline reaches terminal state."""
    if viewer is None or viewer.process.poll() is not None:
        return
    console.info("Rerun viewer is still running; press Ctrl+C to close it.")
    try:
        viewer.process.wait()
    except KeyboardInterrupt:
        return


def _list_processes() -> list[_ProcessInfo]:
    """Read the host process table in the same shape the cleanup command needs."""
    result = subprocess.run(
        ["ps", "-eo", "pid=,ppid=,pgid=,stat=,command="],
        check=True,
        capture_output=True,
        text=True,
    )
    processes: list[_ProcessInfo] = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(maxsplit=4)
        if len(parts) != 5:
            continue
        pid, ppid, pgid, stat, command = parts
        processes.append(
            _ProcessInfo(
                pid=int(pid),
                ppid=int(ppid),
                pgid=int(pgid),
                stat=stat,
                command=command,
            )
        )
    return processes


def _is_rerun_viewer_process(process: _ProcessInfo) -> bool:
    """Return true for auto-launched Rerun web viewer processes."""
    command = process.command
    if "--serve-web" not in command:
        return False
    if "kill-rerun" in command:
        return False
    rerun_invoked = re.search(r"(^|\s)rerun(\s|$)", command) is not None
    rerun_script = "/bin/rerun" in command
    rerun_cli_binary = "/rerun_sdk/rerun_cli/rerun" in command
    return rerun_invoked or rerun_script or rerun_cli_binary


def _find_rerun_viewer_processes(processes: list[_ProcessInfo] | None = None) -> list[_ProcessInfo]:
    """Find candidate Rerun web viewer processes in stable pid order."""
    process_table = _list_processes() if processes is None else processes
    return sorted(
        (process for process in process_table if _is_rerun_viewer_process(process)), key=lambda item: item.pid
    )


def _rerun_viewer_process_group_ids(processes: list[_ProcessInfo]) -> list[int]:
    """Return unique process-group ids for matched viewer processes."""
    return sorted({process.pgid for process in processes})


def _signal_process_group(pgid: int, sig: signal.Signals) -> bool:
    """Signal one process group if it still exists."""
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        return False
    return True


def _wait_for_rerun_process_groups_to_exit(*, pgids: list[int], timeout_seconds: float) -> list[int]:
    """Wait until no matched Rerun viewer processes remain in the target groups."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        remaining = sorted({process.pgid for process in _find_rerun_viewer_processes() if process.pgid in pgids})
        if not remaining or time.monotonic() >= deadline:
            return remaining
        time.sleep(0.1)


def _format_rerun_processes(processes: list[_ProcessInfo]) -> list[dict[str, int | str]]:
    """Render matched processes as stable JSON-like records for CLI output."""
    return [
        {
            "pid": process.pid,
            "ppid": process.ppid,
            "pgid": process.pgid,
            "stat": process.stat,
            "command": process.command,
        }
        for process in processes
    ]


def _terminate_process_group(process: subprocess.Popen[str], sig: signal.Signals) -> None:
    """Signal a viewer process group, falling back to the direct child."""
    pid = getattr(process, "pid", None)
    if pid is None:
        if sig is signal.SIGTERM:
            process.terminate()
        else:
            process.kill()
        return
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        return
    except OSError:
        if sig is signal.SIGTERM:
            process.terminate()
        else:
            process.kill()


@app.command()
def info() -> None:
    """Print a short summary of the current scaffold."""
    console.print(
        "[bold]prml-vslam[/bold]: editable Python package, typed pipeline planner, "
        "Streamlit workbench, and report/slides scaffold."
    )


@app.command("kill-rerun")
def kill_rerun(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Only list matched Rerun viewer processes without terminating them."),
    ] = False,
    timeout_seconds: Annotated[
        float,
        typer.Option("--timeout", min=0.1, help="Seconds to wait after SIGTERM before sending SIGKILL."),
    ] = 5.0,
) -> None:
    """Inspect and terminate orphaned Rerun web viewer processes."""
    processes = _find_rerun_viewer_processes()
    if not processes:
        console.print("No Rerun web viewer processes found.")
        return

    console.print("Matched Rerun web viewer processes:")
    console.plog(_format_rerun_processes(processes))
    if dry_run:
        return

    pgids = _rerun_viewer_process_group_ids(processes)
    for pgid in pgids:
        _signal_process_group(pgid, signal.SIGTERM)
    remaining = _wait_for_rerun_process_groups_to_exit(pgids=pgids, timeout_seconds=timeout_seconds)
    if remaining:
        for pgid in remaining:
            _signal_process_group(pgid, signal.SIGKILL)
        remaining = _wait_for_rerun_process_groups_to_exit(pgids=remaining, timeout_seconds=1.0)

    if remaining:
        console.error("Rerun viewer process groups still running after SIGKILL: %s", remaining)
        raise typer.Exit(code=1)
    console.print(f"Terminated {len(pgids)} Rerun viewer process group(s).")


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
    reconstruction: Annotated[
        bool,
        typer.Option(
            "--reconstruction/--no-reconstruction",
            help="Whether the plan reserves a reconstruction stage.",
        ),
    ] = False,
) -> None:
    """Build a typed benchmark run plan from the CLI."""
    run_config = build_run_config(
        experiment_name=experiment_name,
        output_dir=output_dir,
        source_backend=VideoSourceConfig(video_path=video_path, frame_stride=frame_stride),
        method=method,
        emit_dense_points=emit_dense_points,
        emit_sparse_points=emit_sparse_points,
        reference_enabled=reconstruction,
        trajectory_eval_enabled=trajectory_evaluation,
        trajectory_baseline=trajectory_baseline,
        evaluate_cloud=emit_dense_points and reconstruction,
        connect_live_viewer=True,
    )
    plan = run_config.compile_plan()
    console.plog(plan.model_dump(mode="json"))


@app.command(
    "plan-run-config",
    cls=RunConfigOverrideCommand,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def plan_run_config(
    ctx: typer.Context,
    config_path: Annotated[
        Path,
        typer.Argument(
            help="Path to a pipeline config TOML file (repo-relative paths are resolved via PathConfig).",
        ),
    ],
) -> None:
    """Build a typed benchmark run plan from a TOML config file."""
    path_config = get_path_config()
    try:
        run_cfg = load_run_config_toml(path_config=path_config, config_path=config_path)
        run_cfg = _apply_dotted_overrides_to_run_config(run_cfg, ctx.args)
        plan = run_cfg.compile_plan(path_config)
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc
    console.plog(plan.model_dump(mode="json"))


@app.command(
    "run-config",
    cls=RunConfigOverrideCommand,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def run_config(
    ctx: typer.Context,
    config_path: Annotated[
        Path,
        typer.Argument(
            help="Path to a pipeline config TOML file (repo-relative paths are resolved via PathConfig).",
        ),
    ],
) -> None:
    """Run one offline or streaming pipeline config from a TOML file."""
    path_config = get_path_config()
    try:
        run_cfg = load_run_config_toml(path_config=path_config, config_path=config_path)
        run_cfg = _apply_dotted_overrides_to_run_config(run_cfg, ctx.args)
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc
    run_id = path_config.slugify_experiment_name(run_cfg.experiment_name)
    with _capture_run_config_logs(path_config=path_config, run_id=run_id) as log_path:
        console.info("Persisting run-config log to '%s'.", log_path)
        _run_config_loaded(run_cfg=run_cfg, path_config=path_config)


def _run_config_loaded(*, run_cfg: RunConfig, path_config: PathConfig) -> None:
    """Execute an already loaded run config with durable command-log capture active."""
    run_service: RunService | None = None
    viewer: _RerunViewerProcess | None = None
    snapshot = RunSnapshot()
    preserve_local_head = False
    reached_terminal_snapshot = False
    try:
        viewer = _launch_rerun_viewer(run_config=run_cfg, path_config=path_config)
        runtime_source = build_runtime_source_from_run_config(run_config=run_cfg, path_config=path_config)
        run_service = RunService(path_config=path_config)
        run_service.start_run(run_config=run_cfg, runtime_source=runtime_source)
        snapshot = _wait_for_pipeline_terminal_snapshot(run_service, poll_interval_seconds=0.2)
        reached_terminal_snapshot = True
        preserve_local_head = snapshot.state is RunState.COMPLETED and run_cfg.ray_local_head_lifecycle == "reusable"
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
        if not reached_terminal_snapshot:
            _shutdown_rerun_viewer(viewer)
    _print_pipeline_demo_snapshot(snapshot)
    _wait_for_rerun_viewer_close(viewer)
    _shutdown_rerun_viewer(viewer)
    if snapshot.state is RunState.FAILED:
        raise typer.Exit(code=1)


@app.command("export-run")
def export_run(
    artifact_root: Annotated[
        Path,
        typer.Argument(help="Method-level run artifact root to export."),
    ],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output `.prmlrun.tar.gz` bundle path."),
    ],
) -> None:
    """Export a completed run artifact root as a portable single-file bundle."""
    try:
        result = export_run_bundle(artifact_root, output)
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc
    console.plog(
        {
            "bundle_path": result.bundle_path.as_posix(),
            "run_id": result.manifest.exported_run_id,
            "artifact_label": result.manifest.artifact_label,
            "file_count": len(result.manifest.files),
        }
    )


@app.command("import-run")
def import_run(
    bundle_path: Annotated[
        Path,
        typer.Argument(help="Portable `.prmlrun.tar.gz` bundle to import."),
    ],
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Artifacts directory that should receive the imported run."),
    ] = Path(".artifacts"),
    on_collision: Annotated[
        RunBundleCollisionPolicy,
        typer.Option("--on-collision", help="How to handle an existing target run root.", case_sensitive=False),
    ] = RunBundleCollisionPolicy.FAIL,
) -> None:
    """Import a portable run bundle into the local artifacts tree."""
    try:
        result = import_run_bundle(bundle_path, output_dir=output_dir, collision_policy=on_collision)
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc
    console.plog(
        {
            "artifact_root": result.artifact_root.as_posix(),
            "run_id": result.manifest.exported_run_id,
            "artifact_label": result.manifest.artifact_label,
            "warnings": result.warnings,
        }
    )


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
            help="Persist an offline or streaming ADVIO demo run config.",
            case_sensitive=False,
        ),
    ] = PipelineMode.OFFLINE,
    method: Annotated[
        MethodId,
        typer.Option(
            "--method",
            help="Method id stored in the persisted demo run config.",
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
        typer.Option("--dataset-frame-stride", min=1, help="Dataset frame stride stored in the demo run config."),
    ] = 1,
    dataset_target_fps: Annotated[
        float | None,
        typer.Option("--dataset-target-fps", min=0.01, help="Dataset target FPS stored in the demo run config."),
    ] = None,
) -> None:
    """Persist the canonical ADVIO demo run config as TOML."""
    path_config = get_path_config()
    advio_service = AdvioDatasetService(path_config)
    resolved_sequence_id = _resolve_demo_sequence_id(advio_service, explicit_sequence_id=sequence_id)
    scene = advio_service.scene(resolved_sequence_id)
    resolved_config_path = persist_advio_demo_run_config(
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
    normalize_video_orientation: Annotated[
        bool,
        typer.Option(
            "--normalize-video-orientation/--raw-video-orientation",
            help="Whether to normalize video display orientation during replay.",
        ),
    ] = True,
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
    run_config = build_advio_demo_run_config(
        path_config=path_config,
        sequence_id=scene.sequence_slug,
        mode=PipelineMode.STREAMING,
        method=method,
        pose_source=pose_source,
        pose_frame_mode=pose_frame_mode,
        normalize_video_orientation=normalize_video_orientation,
        dataset_frame_stride=dataset_frame_stride,
        dataset_target_fps=dataset_target_fps,
    )
    source = build_runtime_source_from_run_config(run_config=run_config, path_config=path_config)
    run_service = RunService(path_config=path_config)
    pipeline_demo_console.info(
        "Starting pipeline demo for %s (%s, %s).",
        scene.display_name,
        PipelineMode.STREAMING.value,
        method.value,
    )
    try:
        run_service.start_run(run_config=run_config, runtime_source=source)
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


@app.command("app")
def launch_app(
    browser: Annotated[
        bool,
        typer.Option("--browser/--no-browser", help="Whether to open the app in a browser automatically."),
    ] = True,
) -> None:
    """Launch the Streamlit workbench."""
    path_config = get_path_config()
    app_path = path_config.root / "streamlit_app.py"

    if not app_path.exists():
        console.error("Streamlit app file not found: %s", app_path)
        raise typer.Exit(code=1)

    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    if not browser:
        cmd.extend(["--server.headless", "true"])

    console.info("Launching Streamlit app...")
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.info("Streamlit app stopped.")
    except subprocess.CalledProcessError as exc:
        console.error("Streamlit app exited with error: %s", exc)
        raise typer.Exit(code=exc.returncode) from exc


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


def _apply_dotted_overrides_to_run_config(run_config: RunConfig, args: list[str]) -> RunConfig:
    """Apply canonical ``RunConfig`` field-path overrides after TOML load."""
    if not args:
        return run_config
    overrides = _parse_dotted_overrides(args)
    if not overrides:
        return run_config
    payload = run_config.model_dump(mode="python", round_trip=True)
    _deep_merge(payload, overrides)
    try:
        return RunConfig.model_validate(payload, extra="forbid")
    except ValidationError as exc:
        first_error = exc.errors()[0]
        location = ".".join(str(part) for part in first_error["loc"])
        raise typer.BadParameter(f"Invalid RunConfig override at `{location}`: {first_error['msg']}") from exc


def _parse_dotted_overrides(args: list[str]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    index = 0
    while index < len(args):
        token = args[index]
        if not token.startswith("--"):
            raise typer.BadParameter(f"Unexpected dotted override token `{token}`.")
        option = token[2:]
        if not option:
            raise typer.BadParameter("RunConfig override options must include a field path.")
        if "=" in option:
            path, raw_value = option.split("=", maxsplit=1)
            index += 1
        else:
            if index + 1 >= len(args):
                raise typer.BadParameter(f"Dotted override `{token}` requires a value.")
            path = option
            raw_value = args[index + 1]
            index += 2
        _deep_set(overrides, path.split("."), _parse_override_value(raw_value))
    return overrides


def _parse_override_value(raw_value: str) -> Any:
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value


def _deep_set(target: dict[str, Any], path: list[str], value: Any) -> None:
    cursor = target
    for segment in path[:-1]:
        existing = cursor.get(segment)
        if not isinstance(existing, dict):
            existing = {}
            cursor[segment] = existing
        cursor = existing
    leaf = path[-1]
    existing_leaf = cursor.get(leaf)
    if isinstance(existing_leaf, dict) and isinstance(value, dict):
        _deep_merge(existing_leaf, value)
    else:
        cursor[leaf] = value


def _deep_merge(target: dict[str, Any], overrides: dict[str, Any]) -> None:
    for key, value in overrides.items():
        existing = target.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            _deep_merge(existing, value)
        else:
            target[key] = value


def _apply_dataset_sampling_overrides(
    source_backend: SourceBackendConfig | None,
    *,
    dataset_frame_stride: int | None,
    dataset_target_fps: float | None,
) -> SourceBackendConfig:
    if dataset_frame_stride is None and dataset_target_fps is None:
        if source_backend is None:
            raise typer.BadParameter("Dataset sampling overrides require a dataset-backed source.")
        return source_backend
    if dataset_frame_stride is not None and dataset_target_fps is not None:
        raise typer.BadParameter("Configure either --dataset-frame-stride or --dataset-target-fps, not both.")
    if not isinstance(source_backend, AdvioSourceConfig):
        raise typer.BadParameter("Dataset sampling overrides require a dataset-backed source.")
    return source_backend.model_copy(
        update={
            "frame_stride": 1 if dataset_target_fps is not None else dataset_frame_stride,
            "target_fps": dataset_target_fps,
        }
    )


def _wait_for_pipeline_terminal_snapshot(
    run_service: RunService,
    *,
    poll_interval_seconds: float,
) -> RunSnapshot:
    """Poll the run service until the current demo session reaches a terminal state."""
    previous_state: RunState | None = None
    previous_processed_items = -1
    while True:
        snapshot = run_service.snapshot()
        if snapshot.state is not previous_state:
            plan_run_id = None if snapshot.plan is None else snapshot.plan.run_id
            pipeline_demo_console.info(
                "Pipeline demo state: %s%s", snapshot.state.value, "" if plan_run_id is None else f" ({plan_run_id})"
            )
            previous_state = snapshot.state
        slam_runtime_status = snapshot.stage_runtime_status.get(StageKey.SLAM)
        processed_items = 0 if slam_runtime_status is None else slam_runtime_status.processed_items
        if processed_items != previous_processed_items and processed_items > 0:
            pipeline_demo_console.info(
                "SLAM processed=%d fps=%s throughput=%s",
                processed_items,
                "n/a"
                if slam_runtime_status is None or slam_runtime_status.fps is None
                else f"{slam_runtime_status.fps:.2f}",
                "n/a"
                if slam_runtime_status is None or slam_runtime_status.throughput is None
                else f"{slam_runtime_status.throughput:.2f}",
            )
            previous_processed_items = processed_items
        if snapshot.state not in {RunState.PREPARING, RunState.RUNNING}:
            return snapshot
        time.sleep(poll_interval_seconds)


def _print_pipeline_demo_snapshot(snapshot: RunSnapshot) -> None:
    """Render the final CLI demo snapshot in a compact structured form."""
    payload = {
        "state": snapshot.state.value,
        "error_message": snapshot.error_message or None,
        "plan": None if snapshot.plan is None else snapshot.plan.model_dump(mode="json"),
        "stage_outcomes": {
            stage_key.value: outcome.model_dump(mode="json") for stage_key, outcome in snapshot.stage_outcomes.items()
        },
        "stage_runtime_status": {
            stage_key.value: status.model_dump(mode="json")
            for stage_key, status in snapshot.stage_runtime_status.items()
        },
        "live_refs": {
            stage_key.value: {ref_key: ref.model_dump(mode="json") for ref_key, ref in refs.items()}
            for stage_key, refs in snapshot.live_refs.items()
        },
        "artifacts": {
            artifact_key: artifact.model_dump(mode="json") for artifact_key, artifact in snapshot.artifacts.items()
        },
    }
    console.plog(payload)


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
