"""Dataset × method sweep expansion and sequential execution support.

This module owns the sweep configuration schema, expansion logic, and the factory
that converts one expanded sweep item into a concrete :class:`RunConfig`.  It does
not own execution; the CLI commands in ``prml_vslam.main`` call
``_run_config_loaded`` (the existing single-run boundary) for each item.

Schema overview::

    [sweep]
    name       = "my-sweep"
    output_dir = ".artifacts/sweeps"

    [[datasets]]
    dataset_id          = "tum_rgbd"        # "tum_rgbd" | "advio" | "record3d_dataset"
    sequence_id         = "freiburg1_xyz"
    frame_stride        = 1
    target_fps          = 30.0
    baseline_source     = "ground_truth"
    align_ground        = false
    align_trajectory    = true
    evaluate_trajectory = true

    [methods.vista]
    config_path = ".configs/templates/vista-slam.toml"

Method templates contribute **only** ``[stages.slam]``; all other sections are
silently ignored.  Source selection, baseline policy, and downstream stage
enablement are owned by the sweep ``[[datasets]]`` entries.

Non-goals: aggregation, dashboards, W&B integration, or new external dependencies.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any, Self

from pydantic import ConfigDict, Field, model_validator

from prml_vslam.align.gravity.config import GroundAlignmentStageConfig
from prml_vslam.align.icp.config import CloudAlignmentStageConfig
from prml_vslam.align.trajectory_sim3.config import TrajectoryAlignmentStageConfig
from prml_vslam.eval.stage_cloud.config import CloudEvaluationStageConfig
from prml_vslam.eval.stage_trajectory.config import (
    TrajectoryEvaluationPolicy,
    TrajectoryEvaluationStageConfig,
)
from prml_vslam.methods.stage.config import SlamStageConfig
from prml_vslam.pipeline.config import RunConfig, StageBundle, default_trajectory_baseline_for_source
from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.stages.summary.config import SummaryStageConfig
from prml_vslam.reconstruction.stage.config import ReconstructionStageConfig
from prml_vslam.sources.config import (
    AdvioSourceConfig,
    Record3DDatasetSourceConfig,
    SourceBackendConfig,
    TumRgbdSourceConfig,
)
from prml_vslam.sources.contracts import ReferenceSource
from prml_vslam.sources.stage.config import SourceStageConfig
from prml_vslam.utils import BaseConfig, PathConfig
from prml_vslam.visualization.contracts import VisualizationConfig

_SLUG_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _assert_slug(value: str, label: str) -> None:
    """Raise ValueError when *value* is not safe for use in a run ID.

    Args:
        value: The string to validate.
        label: Human-readable label used in the error message.

    Raises:
        ValueError: When *value* contains characters outside ``[a-zA-Z0-9_-]``.
    """
    if not _SLUG_RE.match(value):
        raise ValueError(
            f"{label} {value!r} contains characters that are not safe in a run ID. "
            "Use only letters, digits, hyphens, and underscores."
        )


def _load_toml_payload(path: Path) -> dict[str, Any]:
    """Read a TOML file and return its raw dict.

    Args:
        path: Absolute or relative path to a TOML file.

    Returns:
        Parsed TOML as a plain dict.

    Raises:
        FileNotFoundError: When *path* does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"TOML file not found: {path}")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _load_slam_stage_from_template(path: Path) -> SlamStageConfig:
    """Extract only ``[stages.slam]`` from a method template TOML.

    All sections other than ``[stages.slam]`` are silently ignored, which lets
    template authors annotate their file with comments about the runner command
    without breaking sweep validation.

    Args:
        path: Path to the method template TOML file.

    Returns:
        Validated :class:`SlamStageConfig` built from the ``[stages.slam]`` section.

    Raises:
        FileNotFoundError: When *path* does not exist.
        ValueError: When ``[stages.slam]`` is absent from the template.
    """
    raw = _load_toml_payload(path)
    slam_raw = raw.get("stages", {}).get("slam")
    if slam_raw is None:
        raise ValueError(
            f"Method template {path} has no [stages.slam] section. "
            "Each method template must define exactly one [stages.slam] block."
        )
    slam_stage = SlamStageConfig.model_validate(slam_raw)
    if slam_stage.backend is None:
        raise ValueError(
            f"Method template {path} has [stages.slam] but no [stages.slam.backend] section. "
            "Each method template must declare a backend (e.g. [stages.slam.backend] with method_id)."
        )
    return slam_stage


def _build_source_backend_for_sweep(dataset: SweepDataset) -> SourceBackendConfig:
    """Map a :class:`SweepDataset` to the matching :class:`SourceBackendConfig`.

    Args:
        dataset: Validated sweep dataset entry.

    Returns:
        Concrete source backend config keyed by *dataset.dataset_id*.

    Raises:
        ValueError: When *dataset.dataset_id* is not a supported source.
    """
    match dataset.dataset_id:
        case "tum_rgbd":
            return TumRgbdSourceConfig(
                sequence_id=dataset.sequence_id,
                frame_stride=dataset.frame_stride,
                target_fps=dataset.target_fps,
            )
        case "advio":
            return AdvioSourceConfig(
                sequence_id=dataset.sequence_id,
                frame_stride=dataset.frame_stride,
                target_fps=dataset.target_fps,
            )
        case "record3d_dataset":
            return Record3DDatasetSourceConfig(
                sequence_id=dataset.sequence_id,
                frame_stride=dataset.frame_stride,
                target_fps=dataset.target_fps,
            )
        case _:
            raise ValueError(
                f"Unknown dataset_id {dataset.dataset_id!r}. Supported values: tum_rgbd, advio, record3d_dataset."
            )


class SweepMeta(BaseConfig):
    """Top-level sweep identity and output routing.

    Attributes:
        name: Human-readable sweep name used as the prefix for all run IDs.
            Must be slug-safe (letters, digits, hyphens, underscores only).
        output_dir: Root directory where per-run artifact directories are written.
            Defaults to ``.artifacts/sweeps``.
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    """Sweep name — used as the run-ID prefix and for human display."""

    output_dir: Path = Path(".artifacts/sweeps")
    """Root artifact directory shared by all runs in this sweep."""

    @model_validator(mode="after")
    def validate_name_is_slug(self) -> Self:
        """Ensure *name* is safe to embed in run IDs."""
        _assert_slug(self.name, "sweep.name")
        return self


class SweepDataset(BaseConfig):
    """One dataset entry in a sweep, including downstream stage-enablement policy.

    Each ``[[datasets]]`` block pairs a dataset with its frame-selection config
    and the set of pipeline stages that should run after SLAM.  The sweep owns
    all source and downstream decisions; method templates may not override them.

    Attributes:
        dataset_id: Source backend discriminator.  Supported: ``tum_rgbd``, ``advio``, ``record3d_dataset``.
        sequence_id: Dataset-specific sequence slug passed to the source backend.
        frame_stride: Read-time stride for replaying stored normalized observations.
            ``1`` means every frame; ``2`` means every other frame, etc.
        target_fps: Read-time target FPS for replaying stored normalized observations.
        baseline_source: Reference trajectory used by trajectory evaluation.
        align_ground: Enable ground-alignment stage.
        align_trajectory: Enable trajectory Sim(3)-alignment stage.
        evaluate_trajectory: Enable trajectory evaluation stage.
        reconstruction: Enable 3-D reconstruction stage.
        align_cloud: Enable dense-cloud alignment stage.
        evaluate_cloud: Enable dense-cloud evaluation stage.
    """

    model_config = ConfigDict(extra="ignore")

    dataset_id: str
    """Source backend discriminator.  Supported: ``tum_rgbd``, ``advio``, ``record3d_dataset``."""

    sequence_id: str
    """Dataset-specific sequence slug."""

    frame_stride: int = Field(default=1, ge=1)
    """Read-time stride for replaying stored normalized observations."""

    target_fps: float | None = Field(default=None, gt=0.0)
    """Read-time target FPS for replaying stored normalized observations."""

    baseline_source: ReferenceSource | None = None
    """Reference trajectory source used by the trajectory-evaluation stage."""

    align_ground: bool = False
    """Enable ground-alignment stage."""

    align_trajectory: bool = False
    """Enable trajectory Sim(3)-alignment stage."""

    evaluate_trajectory: bool = False
    """Enable trajectory evaluation stage."""

    reconstruction: bool = False
    """Enable 3-D reconstruction stage."""

    align_cloud: bool = False
    """Enable dense-cloud alignment stage."""

    evaluate_cloud: bool = False
    """Enable dense-cloud evaluation stage."""

    @model_validator(mode="after")
    def validate_ids_are_slugs(self) -> Self:
        """Ensure *dataset_id* and *sequence_id* are safe to embed in run IDs."""
        _assert_slug(self.dataset_id, "dataset_id")
        _assert_slug(self.sequence_id, "sequence_id")
        return self

    @model_validator(mode="after")
    def validate_single_sampling_mode(self) -> Self:
        """Keep stored-profile sampling unambiguous."""
        if self.target_fps is not None and self.frame_stride != 1:
            raise ValueError("Configure either `frame_stride` or `target_fps`, not both.")
        return self


class SweepMethod(BaseConfig):
    """Reference to a method template TOML file.

    The sweeper reads only ``[stages.slam]`` from the template; all other
    sections are ignored.

    Attributes:
        config_path: Path to the method template TOML, resolved relative to the
            repo root when a :class:`PathConfig` is available.
    """

    model_config = ConfigDict(extra="ignore")

    config_path: Path
    """Path to the method template TOML."""


class SweepConfig(BaseConfig):
    """Root sweep configuration loaded from a sweep TOML file.

    A sweep TOML has three top-level sections:

    * ``[sweep]`` — identity and output routing.
    * ``[[datasets]]`` — one or more dataset entries (array of tables).
    * ``[methods.<id>]`` — one or more method entries keyed by the template backend method ID.

    The sweeper cross-joins datasets × methods in declaration order and derives
    a deterministic run ID for each combination.

    Attributes:
        sweep: Sweep identity and output directory.
        datasets: Ordered list of dataset entries (at least one required).
        methods: Mapping of backend method ID → method reference (at least one required).
    """

    model_config = ConfigDict(extra="ignore")

    sweep: SweepMeta
    """Sweep identity and output routing."""

    datasets: list[SweepDataset] = Field(min_length=1)
    """Ordered dataset entries.  At least one is required."""

    methods: dict[str, SweepMethod] = Field(min_length=1)
    """Backend method ID → template reference.  At least one is required."""

    @model_validator(mode="after")
    def validate_method_ids_are_slugs(self) -> Self:
        """Ensure every method ID is slug-safe."""
        for method_id in self.methods:
            _assert_slug(method_id, "method ID")
        return self

    @model_validator(mode="after")
    def validate_no_duplicate_dataset_sequence_pairs(self) -> Self:
        """Ensure no two ``[[datasets]]`` entries share ``(dataset_id, sequence_id)``.

        Duplicate pairs would expand to duplicate run IDs for every method,
        making the run-ID guarantee impossible to uphold.
        """
        seen: set[tuple[str, str]] = set()
        for ds in self.datasets:
            key = (ds.dataset_id, ds.sequence_id)
            if key in seen:
                raise ValueError(
                    f"Duplicate (dataset_id, sequence_id) pair "
                    f"({ds.dataset_id!r}, {ds.sequence_id!r}) in [[datasets]]. "
                    "Each dataset/sequence combination must appear at most once."
                )
            seen.add(key)
        return self


class SweepRunItem(BaseConfig):
    """One fully-expanded sweep item ready for execution.

    :func:`expand_sweep` produces one ``SweepRunItem`` per dataset × method
    combination.  The item carries everything :func:`build_run_config_from_sweep_item`
    needs to construct the corresponding :class:`RunConfig`.

    Attributes:
        run_id: Deterministic run identifier derived as
            ``{sweep_name}-{dataset_id}-{sequence_id}-{method_id}``.
        sweep_name: Name of the originating sweep (from ``[sweep].name``).
        output_dir: Artifact root directory (from ``[sweep].output_dir``).
        dataset: Dataset entry that drives source and downstream stage policy.
        method_id: Backend method ID from ``[methods]``.
        slam_stage: Validated SLAM stage config extracted from the method template.
    """

    model_config = ConfigDict(extra="ignore")

    run_id: str
    """Deterministic run identifier: ``{sweep}-{dataset_id}-{sequence_id}-{method_id}``."""

    sweep_name: str
    """Name of the originating sweep."""

    output_dir: Path
    """Artifact root directory inherited from ``[sweep].output_dir``."""

    dataset: SweepDataset
    """Dataset entry owning source selection and downstream stage flags."""

    method_id: str
    """Backend method ID as declared in ``[methods]``."""

    slam_stage: SlamStageConfig
    """SLAM stage config extracted verbatim from the method template."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_sweep_config(
    path: Path,
    path_config: PathConfig | None = None,
) -> SweepConfig:
    """Load and validate a sweep TOML file.

    Args:
        path: Path to the sweep TOML.  Resolved relative to the repo root when
            *path_config* is provided.
        path_config: Optional repo-path resolver.  When present, ``path`` is
            resolved through :meth:`PathConfig.resolve_repo_path` when the file
            cannot be found at its literal location.

    Returns:
        Validated :class:`SweepConfig`.

    Raises:
        FileNotFoundError: When the TOML file does not exist.
        pydantic.ValidationError: When the TOML content fails schema validation.
        ValueError: When sweep-level invariants (slug safety, duplicate pairs)
            are violated.
    """
    resolved = _resolve_path(path, path_config)
    raw = _load_toml_payload(resolved)
    return SweepConfig.model_validate(raw)


def expand_sweep(
    config: SweepConfig,
    path_config: PathConfig | None = None,
) -> list[SweepRunItem]:
    """Expand a :class:`SweepConfig` into a deterministic list of :class:`SweepRunItem`.

    Iteration order: datasets in declaration order (outer), methods in dict
    insertion order (inner).  The run ID for each item is:

        ``{sweep.name}-{dataset_id}-{sequence_id}-{method_id}``

    Args:
        config: Validated sweep configuration.
        path_config: Optional repo-path resolver used when method template paths
            are repo-relative.

    Returns:
        Ordered list of expanded sweep items.

    Raises:
        FileNotFoundError: When a method template file does not exist.
        ValueError: When a method template has no ``[stages.slam]`` section, or
            when the expansion produces duplicate run IDs.
    """
    items: list[SweepRunItem] = []
    seen_run_ids: set[str] = set()

    for dataset in config.datasets:
        for method_id, method in config.methods.items():
            template_path = _resolve_path(method.config_path, path_config)
            slam_stage = _load_slam_stage_from_template(template_path)
            backend = slam_stage.backend
            if backend is None:
                raise ValueError(f"Method template {template_path} has no [stages.slam.backend] section.")
            backend_method_id = backend.method_id.value
            if method_id != backend_method_id:
                raise ValueError(
                    f"Sweep method key {method_id!r} does not match template backend method_id "
                    f"{backend_method_id!r} in {template_path}. Use [methods.{backend_method_id}]."
                )

            run_id = _build_run_id(
                sweep_name=config.sweep.name,
                dataset_id=dataset.dataset_id,
                sequence_id=dataset.sequence_id,
                method_id=method_id,
            )
            if run_id in seen_run_ids:
                raise ValueError(
                    f"Expansion produced duplicate run ID {run_id!r}. "
                    "Check that all (dataset_id, sequence_id, method_id) triples are unique."
                )
            seen_run_ids.add(run_id)

            items.append(
                SweepRunItem(
                    run_id=run_id,
                    sweep_name=config.sweep.name,
                    output_dir=config.sweep.output_dir,
                    dataset=dataset,
                    method_id=method_id,
                    slam_stage=slam_stage,
                )
            )

    return items


def build_run_config_from_sweep_item(item: SweepRunItem) -> RunConfig:
    """Build a :class:`RunConfig` from one expanded :class:`SweepRunItem`.

    The resulting config:

    * Uses *item.run_id* as ``experiment_name``.
    * Routes artifacts to *item.output_dir*.
    * Injects the source backend derived from the dataset ``dataset_id`` and
      ``sequence_id``.
    * Carries the ``SlamStageConfig`` verbatim from the method template.
    * Applies downstream stage-enablement flags from the dataset entry.
    * Defaults visualization to ``connect_live_viewer=False``,
      ``export_viewer_rrd=False`` (appropriate for unattended batch runs).

    Args:
        item: A fully-expanded sweep run item produced by :func:`expand_sweep`.

    Returns:
        Validated :class:`RunConfig` ready for pipeline execution.

    Raises:
        ValueError: When the dataset's ``dataset_id`` is not a supported source.
    """
    ds = item.dataset
    source_backend = _build_source_backend_for_sweep(ds)
    baseline_source = (
        default_trajectory_baseline_for_source(source_backend) if ds.baseline_source is None else ds.baseline_source
    )
    trajectory_policy = TrajectoryEvaluationPolicy(baseline_source=baseline_source)

    return RunConfig(
        experiment_name=item.run_id,
        mode=PipelineMode.OFFLINE,
        output_dir=item.output_dir,
        stages=StageBundle(
            source=SourceStageConfig(backend=source_backend),
            slam=item.slam_stage,
            align_ground=GroundAlignmentStageConfig(enabled=ds.align_ground),
            align_trajectory=TrajectoryAlignmentStageConfig(
                enabled=ds.align_trajectory,
                baseline_source=baseline_source,
            ),
            evaluate_trajectory=TrajectoryEvaluationStageConfig(
                enabled=ds.evaluate_trajectory,
                evaluation=trajectory_policy,
            ),
            reconstruction=ReconstructionStageConfig(enabled=ds.reconstruction),
            align_cloud=CloudAlignmentStageConfig(enabled=ds.align_cloud),
            evaluate_cloud=CloudEvaluationStageConfig(enabled=ds.evaluate_cloud),
            summary=SummaryStageConfig(enabled=True),
        ),
        visualization=VisualizationConfig(
            connect_live_viewer=False,
            export_viewer_rrd=False,
        ),
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_run_id(
    *,
    sweep_name: str,
    dataset_id: str,
    sequence_id: str,
    method_id: str,
) -> str:
    """Derive the deterministic run ID for one dataset × method combination."""
    return f"{sweep_name}-{dataset_id}-{sequence_id}-{method_id}"


def _resolve_path(path: Path, path_config: PathConfig | None) -> Path:
    """Resolve *path* using *path_config* when provided, otherwise return as-is."""
    if path_config is not None:
        return path_config.resolve_repo_path(path)
    return path
