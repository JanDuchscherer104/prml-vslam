"""Offline Rerun artifact post-processing for tracked 3D camera playback.

The repo-owned live/export path intentionally stays pinned to
``rerun-sdk==0.24.1``. That version can log the camera pose and trajectory, but
it cannot encode viewer camera-controls that follow an entity. This module
keeps that newer viewer-only behavior out of the logging path by generating a
small Rerun 0.27 blueprint sidecar and merging it with an existing recording.
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
import textwrap
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

APPLICATION_ID = "prml-vslam"
FOLLOW_RERUN_PACKAGE = "rerun-sdk==0.27.0"
TRACKING_CAMERA_ENTITY_PATH = "world/live/model/camera/image"

SCENE_CONTENTS: tuple[str, ...] = (
    "+ world/alignment/**",
    "+ world/reconstruction/**",
    "+ world/live/tracking/**",
    "+ world/live/model",
    "+ world/live/model/camera/image",
    "- world/live/model/camera/image/depth",
    "- world/live/model/camera/image/depth/**",
    "- world/live/model/points",
    "- world/live/model/points/**",
    "- world/keyframes/cameras/**",
    "+ world/keyframes/points/**",
    "+ world/trajectory/tracking",
)

CommandRunner = Callable[[Sequence[str], Path | None], subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class FollowArtifactResult:
    """Paths produced by one offline follow-artifact build."""

    source_rrd_path: Path
    """Existing repo-owned Rerun recording used as the immutable input."""

    output_rrd_path: Path
    """Merged recording containing the source data plus the follow blueprint."""

    blueprint_rrd_path: Path | None
    """Optional retained blueprint sidecar; ``None`` when a temporary sidecar was used."""

    tracking_entity_path: str
    """Entity path used by the 3D viewer camera controls as the follow target."""

    rerun_package: str
    """Isolated Rerun package spec used to generate and merge the follow blueprint."""


def default_follow_output_path(recording_path: Path) -> Path:
    """Return the default follow-enabled artifact path for an existing recording."""
    return recording_path.with_name(f"{recording_path.stem}_follow{recording_path.suffix}")


def create_follow_trajectory_artifact(
    recording_path: Path,
    *,
    output_path: Path | None = None,
    recording_id: str | None = None,
    tracking_entity_path: str = TRACKING_CAMERA_ENTITY_PATH,
    application_id: str = APPLICATION_ID,
    rerun_package: str = FOLLOW_RERUN_PACKAGE,
    uvx_executable: str = "uvx",
    overwrite: bool = False,
    keep_blueprint_path: Path | None = None,
    cwd: Path | None = None,
    command_runner: CommandRunner | None = None,
) -> FollowArtifactResult:
    """Create an offline Rerun recording whose 3D view follows the tracked camera.

    Args:
        recording_path: Existing `.rrd` recording to keep as the source of
            truth. The file is read by `rerun rrd merge` and is not modified.
        output_path: Destination merged `.rrd`. Defaults to a sibling named
            `<stem>_follow.rrd`.
        recording_id: Store recording id to route the merged output under. When
            omitted, repo-owned pipeline artifact paths use the experiment
            directory name.
        tracking_entity_path: Time-varying entity whose transform the 3D viewer
            camera controls should follow. For repo-owned ViSTA recordings this
            is `world/live/tracking/camera`.
        application_id: Rerun application id for the generated blueprint store.
            It must match the source recording's application id for the viewer
            to apply the blueprint naturally.
        rerun_package: `uvx --from` package spec that provides a Rerun version
            with `EyeControls3D(tracking_entity=...)`.
        uvx_executable: Executable used to run the isolated Rerun runtime.
        overwrite: Whether an existing output artifact may be replaced.
        keep_blueprint_path: Optional path where the generated blueprint sidecar
            should be retained for inspection. When omitted, a temporary sidecar
            is generated and deleted after the merge.
        cwd: Optional working directory for subprocesses.
        command_runner: Optional test seam for subprocess execution.

    Returns:
        A :class:`FollowArtifactResult` describing the generated artifact.

    Raises:
        FileNotFoundError: If `recording_path` does not exist.
        FileExistsError: If `output_path` exists and `overwrite` is false.
        ValueError: If input and output resolve to the same path.
        RuntimeError: If the isolated Rerun command fails.
    """
    source_rrd_path = recording_path.resolve()
    if not source_rrd_path.exists():
        raise FileNotFoundError(f"Rerun recording '{source_rrd_path}' does not exist.")
    if source_rrd_path.suffix != ".rrd":
        raise ValueError(f"Expected a .rrd source recording, got '{source_rrd_path}'.")

    output_rrd_path = (default_follow_output_path(source_rrd_path) if output_path is None else output_path).resolve()
    if output_rrd_path == source_rrd_path:
        raise ValueError("Follow artifact output must not replace the source recording in-place.")
    if output_rrd_path.exists() and not overwrite:
        raise FileExistsError(f"Follow artifact '{output_rrd_path}' already exists.")
    output_rrd_path.parent.mkdir(parents=True, exist_ok=True)

    runner = _run_command if command_runner is None else command_runner
    routed_recording_id = _default_recording_id(source_rrd_path) if recording_id is None else recording_id
    with tempfile.TemporaryDirectory(prefix="prml-vslam-rerun-follow-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        script_path = temp_dir / "build_follow_blueprint.py"
        merged_rrd_path = temp_dir / "merged_follow.rrd"
        script_path.write_text(_follow_blueprint_script(), encoding="utf-8")

        blueprint_rrd_path = (
            keep_blueprint_path.resolve() if keep_blueprint_path is not None else temp_dir / "follow_blueprint.rrd"
        )
        blueprint_rrd_path.parent.mkdir(parents=True, exist_ok=True)
        _run_checked(
            runner,
            _build_blueprint_command(
                uvx_executable=uvx_executable,
                rerun_package=rerun_package,
                script_path=script_path,
                output_path=blueprint_rrd_path,
                application_id=application_id,
                tracking_entity_path=tracking_entity_path,
            ),
            cwd=cwd,
        )
        _run_checked(
            runner,
            _merge_command(
                uvx_executable=uvx_executable,
                rerun_package=rerun_package,
                source_rrd_path=source_rrd_path,
                blueprint_rrd_path=blueprint_rrd_path,
                output_rrd_path=merged_rrd_path,
            ),
            cwd=cwd,
        )
        _run_checked(
            runner,
            _route_command(
                uvx_executable=uvx_executable,
                rerun_package=rerun_package,
                merged_rrd_path=merged_rrd_path,
                output_rrd_path=output_rrd_path,
                application_id=application_id,
                recording_id=routed_recording_id,
            ),
            cwd=cwd,
        )

    return FollowArtifactResult(
        source_rrd_path=source_rrd_path,
        output_rrd_path=output_rrd_path,
        blueprint_rrd_path=None if keep_blueprint_path is None else keep_blueprint_path.resolve(),
        tracking_entity_path=tracking_entity_path,
        rerun_package=rerun_package,
    )


def _default_recording_id(source_rrd_path: Path) -> str:
    if source_rrd_path.parent.name == "visualization" and len(source_rrd_path.parents) >= 3:
        return source_rrd_path.parents[2].name
    return source_rrd_path.stem


def _build_blueprint_command(
    *,
    uvx_executable: str,
    rerun_package: str,
    script_path: Path,
    output_path: Path,
    application_id: str,
    tracking_entity_path: str,
) -> list[str]:
    return [
        uvx_executable,
        "--from",
        rerun_package,
        "python",
        script_path.as_posix(),
        "--output",
        output_path.as_posix(),
        "--application-id",
        application_id,
        "--tracking-entity",
        tracking_entity_path,
    ]


def _merge_command(
    *,
    uvx_executable: str,
    rerun_package: str,
    source_rrd_path: Path,
    blueprint_rrd_path: Path,
    output_rrd_path: Path,
) -> list[str]:
    return [
        uvx_executable,
        "--from",
        rerun_package,
        "rerun",
        "rrd",
        "merge",
        source_rrd_path.as_posix(),
        blueprint_rrd_path.as_posix(),
        "-o",
        output_rrd_path.as_posix(),
    ]


def _route_command(
    *,
    uvx_executable: str,
    rerun_package: str,
    merged_rrd_path: Path,
    output_rrd_path: Path,
    application_id: str,
    recording_id: str,
) -> list[str]:
    return [
        uvx_executable,
        "--from",
        rerun_package,
        "rerun",
        "rrd",
        "route",
        merged_rrd_path.as_posix(),
        "--application-id",
        application_id,
        "--recording-id",
        recording_id,
        "-o",
        output_rrd_path.as_posix(),
    ]


def _run_command(command: Sequence[str], cwd: Path | None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=None if cwd is None else cwd.as_posix(),
        check=True,
        text=True,
        capture_output=True,
    )


def _run_checked(runner: CommandRunner, command: Sequence[str], *, cwd: Path | None) -> None:
    try:
        runner(command, cwd)
    except subprocess.CalledProcessError as exc:
        stderr = "" if exc.stderr is None else str(exc.stderr).strip()
        stdout = "" if exc.stdout is None else str(exc.stdout).strip()
        detail = stderr or stdout or "no command output"
        raise RuntimeError(f"Rerun follow-artifact command failed: {' '.join(command)}\n{detail}") from exc


def _follow_blueprint_script() -> str:
    return textwrap.dedent(
        f"""
        from __future__ import annotations

        import argparse
        from pathlib import Path

        import rerun as rr
        import rerun.blueprint as rrb

        SCENE_CONTENTS = {SCENE_CONTENTS!r}


        def build_blueprint(tracking_entity_path: str) -> rrb.Blueprint:
            return rrb.Blueprint(
                rrb.Horizontal(
                    rrb.Spatial3DView(
                        origin="world",
                        name="3D Scene",
                        contents=list(SCENE_CONTENTS),
                        eye_controls=rrb.EyeControls3D(tracking_entity=tracking_entity_path),
                    ),
                    rrb.Tabs(
                        rrb.Spatial2DView(
                            origin="world/live/model/diag/rgb",
                            contents="world/live/model/diag/rgb",
                            name="Model RGB",
                        ),
                        rrb.Spatial2DView(
                            origin="world/live/model/camera/image",
                            contents="world/live/model/camera/image/depth",
                            name="Model Depth",
                        ),
                        name="2D Views",
                    ),
                ),
            )


        def main() -> None:
            parser = argparse.ArgumentParser()
            parser.add_argument("--output", required=True)
            parser.add_argument("--application-id", required=True)
            parser.add_argument("--tracking-entity", required=True)
            args = parser.parse_args()

            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            recording = rr.RecordingStream(application_id=args.application_id, recording_id="follow-blueprint")
            recording.save(output_path)
            rr.send_blueprint(
                build_blueprint(args.tracking_entity),
                make_active=True,
                make_default=True,
                recording=recording,
            )
            recording.flush()
            recording.disconnect()


        if __name__ == "__main__":
            main()
        """
    ).strip()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a follow-enabled offline Rerun recording.")
    parser.add_argument("recording_path", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--recording-id", default=None)
    parser.add_argument("--tracking-entity", default=TRACKING_CAMERA_ENTITY_PATH)
    parser.add_argument("--application-id", default=APPLICATION_ID)
    parser.add_argument("--rerun-package", default=FOLLOW_RERUN_PACKAGE)
    parser.add_argument("--uvx", default="uvx")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--keep-blueprint", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    """Command-line entry point for creating a follow-enabled `.rrd` artifact."""
    args = _parse_args()
    result = create_follow_trajectory_artifact(
        args.recording_path,
        output_path=args.output,
        recording_id=args.recording_id,
        tracking_entity_path=args.tracking_entity,
        application_id=args.application_id,
        rerun_package=args.rerun_package,
        uvx_executable=args.uvx,
        overwrite=args.overwrite,
        keep_blueprint_path=args.keep_blueprint,
    )
    print(result.output_rrd_path.as_posix())


if __name__ == "__main__":
    main()


__all__ = [
    "APPLICATION_ID",
    "FOLLOW_RERUN_PACKAGE",
    "TRACKING_CAMERA_ENTITY_PATH",
    "FollowArtifactResult",
    "create_follow_trajectory_artifact",
    "default_follow_output_path",
    "main",
]
