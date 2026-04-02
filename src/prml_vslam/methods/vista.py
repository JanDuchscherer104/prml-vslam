"""ViSTA-SLAM adapter."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from prml_vslam.methods.base import BaseMethod, ExternalMethodConfig
from prml_vslam.methods.contracts import (
    MethodArtifacts,
    MethodCommand,
    MethodId,
    MethodRunRequest,
    MethodRunResult,
)
from prml_vslam.methods.io import (
    extract_video_frames,
    is_video_path,
    materialize_image_directory,
    timestamps_for_view_names,
    write_tum_trajectory,
)
from prml_vslam.pipeline.workspace import PreparedInput
from prml_vslam.utils import SE3Pose

if TYPE_CHECKING:
    pass


class VISTAMethodConfig(ExternalMethodConfig):
    """Config for invoking ViSTA-SLAM from a checked-out upstream repo."""

    @property
    def target_type(self) -> type[VISTAMethod]:
        return VISTAMethod

    @property
    def method_id(self) -> MethodId:
        return MethodId.VISTA

    @property
    def default_config_relpath(self) -> Path:
        return Path("configs/default.yaml")


class VISTAMethod(BaseMethod):
    """Adapter for the ViSTA-SLAM repository interface."""

    def __init__(self, config: VISTAMethodConfig) -> None:
        super().__init__(config)
        self.config = config

    def _prepare_input(self, request: MethodRunRequest) -> PreparedInput:
        source_path = self.resolve_existing_input_path(request.input_path)
        run_paths = self.run_paths(request.artifact_root)
        frames_dir = run_paths.input_frames_dir
        manifest_path = run_paths.capture_manifest_path
        if is_video_path(source_path):
            manifest = extract_video_frames(
                source_path,
                frames_dir=frames_dir,
                manifest_path=manifest_path,
                frame_stride=request.frame_stride,
            )
        elif source_path.is_dir():
            manifest = materialize_image_directory(
                source_path,
                frames_dir=frames_dir,
                manifest_path=manifest_path,
                frame_stride=request.frame_stride,
            )
        else:
            raise ValueError(
                "ViSTA-SLAM expects a video file or an image directory so it can run on a sequential RGB stream."
            )

        first_frame = manifest.frames[0].image_path
        image_glob = (first_frame.parent / f"*{first_frame.suffix}").as_posix()
        return PreparedInput(
            source_path=source_path,
            resolved_input_path=frames_dir.resolve(),
            frames_dir=frames_dir.resolve(),
            image_glob=image_glob,
            manifest_path=manifest_path.resolve(),
            manifest=manifest,
        )

    def _build_artifacts(self, request: MethodRunRequest, prepared_input: PreparedInput) -> MethodArtifacts:
        native_output_dir = request.artifact_root / "native" / self.method_id.artifact_slug
        return self.build_method_artifacts(
            request,
            native_output_dir=native_output_dir,
            raw_trajectory_path=(native_output_dir / "trajectory.npy").resolve(),
            raw_point_cloud_path=(native_output_dir / "pointcloud.ply").resolve(),
            view_graph_path=(native_output_dir / "view_graph.npz").resolve(),
        )

    def _build_command(
        self,
        request: MethodRunRequest,
        prepared_input: PreparedInput,
        artifacts: MethodArtifacts,
    ) -> MethodCommand:
        if prepared_input.image_glob is None:
            raise ValueError("ViSTA-SLAM requires an image glob.")
        return MethodCommand(
            cwd=self.config.repo_path,
            argv=[
                self.config.python_executable,
                "run.py",
                "--config",
                self.config.resolve_config_path().as_posix(),
                "--images",
                prepared_input.image_glob,
                "--output",
                artifacts.native_output_dir.as_posix(),
            ],
        )

    def _build_native_viewer_command(self, artifacts: MethodArtifacts) -> MethodCommand:
        return MethodCommand(
            cwd=self.config.repo_path,
            argv=[
                self.config.python_executable,
                "scripts/vis_slam_results.py",
                artifacts.native_output_dir.as_posix(),
            ],
        )

    def _normalize_outputs(self, result: MethodRunResult) -> None:
        artifacts = result.artifacts
        raw_trajectory_path = artifacts.raw_trajectory_path
        raw_point_cloud_path = artifacts.raw_point_cloud_path
        if raw_trajectory_path is None or raw_point_cloud_path is None:
            raise ValueError("ViSTA-SLAM artifacts are not fully defined.")

        self.ensure_files_exist([raw_trajectory_path, raw_point_cloud_path])
        self.copy_artifact(raw_point_cloud_path, artifacts.normalized_point_cloud_path)

        poses = np.load(raw_trajectory_path)
        view_names = self._load_view_names(artifacts.view_graph_path)
        timestamps = timestamps_for_view_names(result.prepared_input.manifest, view_names)
        if not timestamps:
            timestamps = [float(index) for index in range(len(poses))]
        normalized_poses = [SE3Pose.from_matrix(pose) for pose in poses]
        write_tum_trajectory(artifacts.normalized_trajectory_path, normalized_poses, timestamps)

    def _build_notes(self) -> list[str]:
        return [
            "ViSTA-SLAM requires frontend STA weights and ORB vocabulary files in the upstream 'pretrains/' directory.",
            "The upstream repo provides a live Rerun viewer and a post-hoc Open3D viewer script.",
        ]

    @staticmethod
    def _load_view_names(view_graph_path: Path | None) -> list[str] | None:
        if view_graph_path is None or not view_graph_path.exists():
            return None
        payload = np.load(view_graph_path, allow_pickle=True)
        if "view_names" not in payload:
            return None
        return [str(name) for name in payload["view_names"].tolist()]


__all__ = [
    "VISTAMethod",
    "VISTAMethodConfig",
]
