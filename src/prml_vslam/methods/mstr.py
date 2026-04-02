"""MASt3R-SLAM adapter."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.methods.base import BaseMethod, ExternalMethodConfig
from prml_vslam.methods.contracts import (
    MethodArtifacts,
    MethodCommand,
    MethodId,
    MethodRunRequest,
    MethodRunResult,
    ViewerId,
)
from prml_vslam.pipeline.workspace import PreparedInput


class MSTRMethodConfig(ExternalMethodConfig):
    """Config for invoking MASt3R-SLAM from a checked-out upstream repo."""

    calibration_path: Path | None = None
    """Optional calibration file passed through to the upstream CLI."""

    @property
    def target_type(self) -> type[MSTRMethod]:
        return MSTRMethod

    @property
    def method_id(self) -> MethodId:
        return MethodId.MSTR

    @property
    def default_config_relpath(self) -> Path:
        return Path("config/base.yaml")


class MSTRMethod(BaseMethod):
    """Adapter for the MASt3R-SLAM repository interface."""

    def __init__(self, config: MSTRMethodConfig) -> None:
        super().__init__(config)
        self.config = config

    def _prepare_input(self, request: MethodRunRequest) -> PreparedInput:
        source_path = self.resolve_existing_input_path(request.input_path)
        if not (source_path.is_dir() or source_path.is_file()):
            raise ValueError(f"Unsupported MASt3R-SLAM input path '{source_path}'.")
        return PreparedInput(
            source_path=source_path,
            resolved_input_path=source_path,
        )

    def _build_artifacts(self, request: MethodRunRequest, prepared_input: PreparedInput) -> MethodArtifacts:
        run_slug = self.build_run_slug(request.artifact_root, self.method_id)
        native_output_dir = (self.config.repo_path / "logs" / run_slug).resolve()
        sequence_name = (
            prepared_input.resolved_input_path.stem
            if prepared_input.resolved_input_path.is_file()
            else prepared_input.resolved_input_path.name
        )
        return self.build_method_artifacts(
            request,
            native_output_dir=native_output_dir,
            raw_trajectory_path=(native_output_dir / f"{sequence_name}.txt").resolve(),
            raw_point_cloud_path=(native_output_dir / f"{sequence_name}.ply").resolve(),
        )

    def _build_command(
        self,
        request: MethodRunRequest,
        prepared_input: PreparedInput,
        artifacts: MethodArtifacts,
    ) -> MethodCommand:
        run_slug = artifacts.native_output_dir.name
        argv = [
            self.config.python_executable,
            "main.py",
            "--dataset",
            prepared_input.resolved_input_path.as_posix(),
            "--config",
            self.config.resolve_config_path().as_posix(),
            "--save-as",
            run_slug,
        ]
        if self.config.calibration_path is not None:
            argv.extend(["--calib", self.config.calibration_path.as_posix()])
        if not (request.viewer == ViewerId.NATIVE and request.launch_viewer):
            argv.append("--no-viz")
        return MethodCommand(cwd=self.config.repo_path, argv=argv)

    def _normalize_outputs(self, result: MethodRunResult) -> None:
        artifacts = result.artifacts
        raw_trajectory_path = artifacts.raw_trajectory_path
        raw_point_cloud_path = artifacts.raw_point_cloud_path
        if raw_trajectory_path is None or raw_point_cloud_path is None:
            raise ValueError("MASt3R-SLAM artifacts are not fully defined.")

        self.ensure_files_exist([raw_trajectory_path, raw_point_cloud_path])
        self.copy_artifact(raw_trajectory_path, artifacts.normalized_trajectory_path)
        self.copy_artifact(raw_point_cloud_path, artifacts.normalized_point_cloud_path)

    def _build_notes(self) -> list[str]:
        return [
            "MASt3R-SLAM expects its model checkpoints in the upstream 'checkpoints/' directory.",
            "The upstream repo provides a live native viewer during inference; the normalized integration adds Plotly and Open3D post-hoc viewers.",
        ]


__all__ = [
    "MSTRMethod",
    "MSTRMethodConfig",
]
