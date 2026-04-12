"""Centralized filesystem path handling for the PRML VSLAM project."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from pydantic import ConfigDict, Field, ValidationInfo, field_validator

from .base_config import BaseConfig
from .base_data import BaseData

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ROOT_DIR_FIELDS = (
    "artifacts_dir captures_dir data_dir logs_dir configs_dir method_repos_dir method_envs_dir checkpoints_dir".split()
)


class RunArtifactPaths(BaseData):
    """Typed layout for one planned benchmark run."""

    model_config = ConfigDict(frozen=True)

    artifact_root: Path
    """Root directory for all artifacts in the run."""
    input_frames_dir: Path
    """Directory containing decoded input frames."""
    input_timestamps_path: Path
    """Path to canonical normalized frame timestamps."""
    input_intrinsics_path: Path
    """Path to canonical normalized intrinsics metadata."""
    input_rotation_metadata_path: Path
    """Path to canonical source-rotation metadata."""
    capture_manifest_path: Path
    """Path to the normalized capture manifest."""
    sequence_manifest_path: Path
    """Path to the normalized sequence manifest."""
    benchmark_inputs_path: Path
    """Path to prepared benchmark-side input metadata."""
    trajectory_path: Path
    """Path to the exported trajectory."""
    sparse_points_path: Path
    """Path to the exported sparse point cloud."""
    dense_points_path: Path
    """Path to the exported dense point cloud."""
    native_output_dir: Path
    """Directory containing preserved native backend outputs."""
    native_rerun_rrd_path: Path
    """Path to a preserved native backend Rerun recording."""
    arcore_alignment_path: Path
    """Path to the ARCore alignment artifact."""
    trajectory_metrics_path: Path
    """Path to persisted trajectory evaluation metrics."""
    cloud_metrics_path: Path
    """Path to persisted dense-cloud evaluation metrics."""
    efficiency_metrics_path: Path
    """Path to persisted runtime-efficiency metrics."""
    reference_cloud_path: Path
    """Path to the reference reconstruction artifact."""
    summary_path: Path
    """Path to the run-level summary artifact."""
    stage_manifests_path: Path
    """Path to the persisted stage-manifest bundle."""

    @classmethod
    def build(cls, artifact_root: Path) -> RunArtifactPaths:
        """Build the canonical artifact layout from an explicit root."""
        resolved_root = artifact_root.expanduser().resolve()
        return cls(
            artifact_root=resolved_root,
            input_frames_dir=(resolved_root / "input" / "frames").resolve(),
            input_timestamps_path=(resolved_root / "input" / "timestamps.json").resolve(),
            input_intrinsics_path=(resolved_root / "input" / "intrinsics.yaml").resolve(),
            input_rotation_metadata_path=(resolved_root / "input" / "rotation_metadata.json").resolve(),
            capture_manifest_path=(resolved_root / "input" / "capture_manifest.json").resolve(),
            sequence_manifest_path=(resolved_root / "input" / "sequence_manifest.json").resolve(),
            benchmark_inputs_path=(resolved_root / "benchmark" / "inputs.json").resolve(),
            trajectory_path=(resolved_root / "slam" / "trajectory.tum").resolve(),
            sparse_points_path=(resolved_root / "slam" / "sparse_points.ply").resolve(),
            dense_points_path=(resolved_root / "dense" / "dense_points.ply").resolve(),
            native_output_dir=(resolved_root / "native").resolve(),
            native_rerun_rrd_path=(resolved_root / "native" / "rerun_recording.rrd").resolve(),
            arcore_alignment_path=(resolved_root / "evaluation" / "arcore_alignment.json").resolve(),
            trajectory_metrics_path=(resolved_root / "evaluation" / "trajectory_metrics.json").resolve(),
            cloud_metrics_path=(resolved_root / "evaluation" / "cloud_metrics.json").resolve(),
            efficiency_metrics_path=(resolved_root / "evaluation" / "efficiency_metrics.json").resolve(),
            reference_cloud_path=(resolved_root / "reference" / "reference_cloud.ply").resolve(),
            summary_path=(resolved_root / "summary" / "run_summary.json").resolve(),
            stage_manifests_path=(resolved_root / "summary" / "stage_manifests.json").resolve(),
        )

    def plotly_scene_path(self, method_slug: str) -> Path:
        """Return the canonical Plotly scene path for one method run."""
        return (self.artifact_root / "visualization" / f"{method_slug}_scene.html").resolve()


class PathConfig(BaseConfig):
    """Centralize all repository-owned path semantics."""

    model_config = ConfigDict(frozen=True)

    root: Path = Field(default_factory=lambda: PROJECT_ROOT)
    """Repository root used to anchor relative paths."""
    artifacts_dir: Path = Field(default_factory=lambda: Path(".artifacts"))
    """Default root directory for generated benchmark artifacts."""
    captures_dir: Path = Field(default_factory=lambda: Path("captures"))
    """Default root directory for input capture videos."""
    data_dir: Path = Field(default_factory=lambda: Path(".data"))
    """Root directory for repo-owned benchmark datasets."""
    logs_dir: Path = Field(default_factory=lambda: Path(".logs"))
    """Root directory for shared runtime state such as cloned upstream repos and checkpoints."""
    configs_dir: Path = Field(default_factory=lambda: Path(".configs"))
    """Root directory for repo-owned durable TOML configuration."""
    method_repos_dir: Path = Field(default_factory=lambda: Path(".logs/repos"))
    """Directory containing checked-out upstream method repositories."""
    method_envs_dir: Path = Field(default_factory=lambda: Path(".logs/venvs"))
    """Directory containing dedicated per-method virtual environments."""
    checkpoints_dir: Path = Field(default_factory=lambda: Path(".logs/ckpts"))
    """Directory containing shared method checkpoints and weights."""

    @field_validator("root", mode="before")
    @classmethod
    def _validate_root(cls, value: str | Path) -> Path:
        """Validate that the configured repository root exists."""
        root = Path(value).expanduser().resolve()
        if not root.exists():
            raise ValueError(f"Configured project root '{root}' does not exist.")
        return root

    @field_validator(*_ROOT_DIR_FIELDS, mode="before")
    @classmethod
    def _resolve_root_relative_dirs(cls, value: str | Path, info: ValidationInfo) -> Path:
        """Resolve configured directories against the repository root."""
        return cls._resolve_path(value, root=info.data.get("root", PROJECT_ROOT))

    @staticmethod
    def _resolve_path(path: str | Path, *, root: Path) -> Path:
        """Resolve a path relative to the configured repository root."""
        return (path if isinstance(path, Path) and path.is_absolute() else root / path).expanduser().resolve()

    @staticmethod
    def _resolve_dir(path: Path, *parts: str | Path, create: bool = False) -> Path:
        """Resolve a directory and optionally create it."""
        resolved = path.joinpath(*parts).resolve() if parts else path
        if create:
            resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    def resolve_repo_path(self, path: str | Path, *, base_dir: Path | None = None) -> Path:
        """Resolve a path relative to the repository root or a provided base directory."""
        base_path = self.root if base_dir is None else self._resolve_path(base_dir, root=self.root)
        return self._resolve_path(path, root=base_path)

    def resolve_video_path(self, path: str | Path, *, must_exist: bool = False) -> Path:
        """Resolve a video path, defaulting bare filenames into the captures directory."""
        candidate = Path(path)
        base_dir = self.captures_dir if candidate.parent == Path() else None
        resolved = self.resolve_repo_path(candidate, base_dir=base_dir)
        if must_exist and not resolved.exists():
            raise FileNotFoundError(f"Video path '{resolved}' does not exist.")
        return resolved

    def resolve_output_dir(self, path: str | Path | None = None, *, create: bool = False) -> Path:
        """Resolve an output directory, defaulting to the configured artifacts root."""
        return self._resolve_dir(self.artifacts_dir if path is None else self.resolve_repo_path(path), create=create)

    def resolve_data_dir(self, *, create: bool = False) -> Path:
        """Resolve the repo-owned dataset root directory."""
        return self._resolve_dir(self.data_dir, create=create)

    def resolve_dataset_dir(self, dataset_slug: str, *, create: bool = False) -> Path:
        """Resolve one dataset directory under the shared data root."""
        return self._resolve_dir(self.data_dir, dataset_slug, create=create)

    def resolve_logs_dir(self, *, create: bool = False) -> Path:
        """Resolve the shared runtime logs directory."""
        return self._resolve_dir(self.logs_dir, create=create)

    def resolve_configs_dir(self, *, create: bool = False) -> Path:
        """Resolve the shared repo-owned config directory."""
        return self._resolve_dir(self.configs_dir, create=create)

    def resolve_pipeline_configs_dir(self, *, create: bool = False) -> Path:
        """Resolve the shared pipeline config directory under the repo config root."""
        return self._resolve_dir(self.configs_dir, "pipelines", create=create)

    def resolve_method_repo_dir(self, method_repo_name: str, *, create: bool = False) -> Path:
        """Resolve one upstream method checkout path under the shared logs directory."""
        return self._resolve_dir(self.method_repos_dir, method_repo_name, create=create)

    def resolve_method_env_dir(self, method_slug: str, *, create: bool = False) -> Path:
        """Resolve one dedicated virtual environment path for an external backend."""
        return self._resolve_dir(self.method_envs_dir, method_slug, create=create)

    def resolve_checkpoint_dir(self, method_slug: str, *, create: bool = False) -> Path:
        """Resolve one shared checkpoint directory for an external backend."""
        return self._resolve_dir(self.checkpoints_dir, method_slug, create=create)

    def resolve_toml_path(
        self,
        path: str | Path,
        *,
        base_dir: str | Path | None = None,
        must_exist: bool = False,
        create_parent: bool = False,
    ) -> Path:
        """Resolve a TOML file path relative to the repository root."""
        resolved = self.resolve_repo_path(path, base_dir=base_dir)
        if resolved.suffix != ".toml":
            raise ValueError(f"Config path must be a .toml file, got {resolved}")
        if create_parent:
            resolved.parent.mkdir(parents=True, exist_ok=True)
        if must_exist and not resolved.exists():
            raise FileNotFoundError(f"Config file not found: {resolved}")
        return resolved

    def resolve_pipeline_config_path(
        self,
        path: str | Path,
        *,
        must_exist: bool = False,
        create_parent: bool = False,
    ) -> Path:
        """Resolve a pipeline config TOML path.

        Bare filenames are placed under `.configs/pipelines/`. Explicit relative
        or absolute paths keep their original anchoring.
        """
        candidate = Path(path)
        base_dir = (
            self.resolve_pipeline_configs_dir() if not candidate.is_absolute() and candidate.parent == Path() else None
        )
        return self.resolve_toml_path(
            candidate,
            base_dir=base_dir,
            must_exist=must_exist,
            create_parent=create_parent,
        )

    def slugify_experiment_name(self, experiment_name: str) -> str:
        """Convert a human-readable experiment name into a filesystem-safe slug."""
        slug = re.sub(r"[^a-z0-9]+", "-", experiment_name.strip().lower())
        return slug.strip("-") or "experiment"

    def plan_run_paths(
        self, *, experiment_name: str, method_slug: str, output_dir: str | Path | None = None
    ) -> RunArtifactPaths:
        """Build the canonical artifact layout for one benchmark run."""
        return RunArtifactPaths.build(
            self.resolve_output_dir(output_dir) / self.slugify_experiment_name(experiment_name) / method_slug
        )


@lru_cache(maxsize=1)
def get_path_config() -> PathConfig:
    """Return the process-wide default path configuration."""
    return PathConfig()


__all__ = ["PROJECT_ROOT", "PathConfig", "RunArtifactPaths", "get_path_config"]
