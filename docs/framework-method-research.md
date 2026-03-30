# Framework and Method Research

This note distills the primary-source documentation and paper-source material that matter most for this repository. The two paper source trees are now available locally under:

- `literature/tex-src/arXiv-2509.01584/` for ViSTA-SLAM
- `literature/tex-src/arXiv-2412.12392/` for MASt3R-SLAM

The goal of this document is not to mirror those sources, but to decide how their ideas should shape `prml_vslam`.

## Decision Summary

- Use `pydantic-settings` for environment-derived application settings.
- Keep `BaseConfig` as the project-wide experiment and factory layer.
- Treat ViSTA-SLAM and MASt3R-SLAM as external backends with thin wrappers.
- Use Plotly for reproducible metrics artifacts.
- Use `pytransform3d` to centralize transform and frame-convention handling.
- Keep PyTorch3D optional and isolated to research-heavy geometry utilities.
- Treat Nerfstudio as an external reference-reconstruction path, not a core dependency.

## Library Roles

### `pydantic-settings`

Strong fit. The official docs position `BaseSettings` as the environment-backed configuration layer, including nested settings, prefixed environment variables, and configurable source ordering. For this repo, it should own:

- external repo roots
- environment roots
- checkpoint caches
- dataset roots
- cluster-specific defaults

Best practices:

- Use `BaseSettings` only for machine-local or deployment-local values.
- Keep experiment requests, pipeline configs, and stage configs on `BaseConfig`.
- Use one prefix such as `PRML_VSLAM_`.
- Use nested env settings with `env_nested_delimiter="__"`.
- Keep default validation enabled so broken env state fails early.

Recommended pattern:

```python
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class ToolPathsSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PRML_VSLAM_",
        env_nested_delimiter="__",
        validate_default=True,
    )

    vista_env: Path
    """Environment root for ViSTA-SLAM."""

    mast3r_env: Path
    """Environment root for MASt3R-SLAM."""

    nerfstudio_env: Path | None = None
    """Optional environment root for Nerfstudio."""

    datasets_root: Path
    """Default dataset root."""

    checkpoints_root: Path
    """Shared checkpoint cache."""
```

### Plotly

Strong fit. Plotly's own docs recommend Plotly Express as the default entry point and `graph_objects` when the figure structure matters. That maps well to this repo:

- Plotly Express for quick diagnostics over tidy metrics tables
- `graph_objects` for publication-grade figures, mixed subplots, and 3D scenes
- `.html` export for interactive review
- `.json` export for deterministic figure snapshots
- `.png` or `.svg` export for Typst documents

### `pytransform3d`

Recommended. Its value here is disciplined transformation handling, explicit conventions, and transformation-chain management. That is more important than ad-hoc helper math once we start comparing outputs from multiple SLAM backends, ARCore, COLMAP, and Nerfstudio.

Recommended role:

- keep one internal 4x4 transform convention
- convert method-specific pose outputs at the boundary
- centralize frame naming and directionality
- debug alignment mistakes explicitly

### PyTorch3D

Useful, but optional. PyTorch3D is best kept out of the base CLI path unless we are actively implementing learned geometry or differentiable rendering in-repo. It is a good research utility layer, not a requirement for basic wrapper orchestration and evaluation.

Recommended role:

- differentiable geometry experiments
- custom rendering or reprojection probes
- optional mesh and point-cloud utilities in tensor form

### Nerfstudio

Recommended as an external adjunct. Its value is strongest as a CLI-driven reference reconstruction or neural scene representation path. It should not be imported deeply into the main runtime. Instead:

- convert captures into Nerfstudio-compatible `transforms.json`
- run `ns-process-data`, `ns-train`, and `ns-export` externally
- reuse its point-cloud export and viewer tooling where helpful

## Method Notes from the Paper Sources

## ViSTA-SLAM

The paper-source tree for ViSTA-SLAM is in `literature/tex-src/arXiv-2509.01584/`. The most useful paper-specific contribution statement is in `sec/1_2_intro_contribution.tex`, and the method details are in `sec/2_method.tex`.

The contributions that matter most for this repo are:

- a lightweight symmetric two-view association frontend that predicts local pointmaps and relative pose from only two RGB images
- explicit support for operating without camera intrinsics
- a backend based on Sim(3) pose-graph optimization with loop closure
- a graph design where each view may be represented by multiple nodes, linked with scale-only edges to absorb scale inconsistency across repeated forward passes
- a release that already exposes both offline sequence mode and live camera mode

How we should use those ideas:

- ViSTA-SLAM should be our first-class uncalibrated backend.
- Its live camera mode makes it the natural first streaming backend.
- Its local pointmap plus relative-pose interface is a good model for a normalized `pairwise_prediction` artifact.
- Its multiple-node-per-view Sim(3) graph is a useful design reference when we decide how much of the backend graph state to preserve in normalized outputs.
- Its loop-closure confirmation via the model itself suggests that loop candidates and loop confirmations should be separate internal artifact types.

Recommended wrapper stance:

- call `run.py` and `run_live.py` externally
- normalize its outputs immediately
- do not reimplement its internals in `prml_vslam`

## MASt3R-SLAM

The paper-source tree for MASt3R-SLAM is in `literature/tex-src/arXiv-2412.12392/`. The main contribution statement and most method details are directly in `main.tex`.

The contributions that matter most for this repo are:

- the first real-time SLAM framework built around the MASt3R two-view 3D reconstruction prior
- efficient pointmap matching, low-latency tracking, local pointmap fusion, loop closure, and second-order global optimization
- a generic central camera assumption rather than a fixed parametric camera model
- a clear calibrated branch that improves accuracy when camera parameters are known
- a backend that jointly optimizes for large-scale consistency while maintaining real-time performance

How we should use those ideas:

- MASt3R-SLAM should be the main dense-learning batch baseline.
- Its generic central camera assumption should shape our own internal camera abstraction.
- Its separation between uncalibrated ray-space processing and calibrated pixel-space refinement maps well to explicit calibrated and uncalibrated execution branches in our planner.
- Its weighted local fusion is a strong design reference for a future normalized `canonical_pointmap` or `local_map` artifact.
- Its incremental retrieval and loop closure design suggests that retrieval state should be a distinct stage responsibility, not buried inside a generic `slam_run`.

Recommended wrapper stance:

- call `main.py` externally on either MP4 input or frame directories
- expose calibration as an explicit optional config input
- normalize trajectories, keyframes, and dense geometry into repo-owned paths

## Wrapper Strategy

The clean integration strategy is intentionally conservative:

- keep upstream repos separate
- keep upstream environments separate
- shell out to official entry points
- snapshot all run inputs and configs
- normalize all outputs into repo-owned artifact contracts
- avoid importing deep upstream internals

Recommended abstraction:

```python
from __future__ import annotations

from pathlib import Path

from prml_vslam.utils import BaseConfig


class ExternalMethodConfig(BaseConfig):
    method_root: Path
    """Checkout root of the upstream repository."""

    executable: str
    """Runner executable, usually `python` inside the external environment."""

    work_dir: Path | None = None
    """Optional working directory override."""

    checkpoint_dir: Path | None = None
    """Optional checkpoint root."""


class VistaSlamConfig(ExternalMethodConfig):
    config_path: Path
    """Path to the upstream YAML config."""

    enable_live_vis: bool = False
    """Whether to enable upstream live visualization."""

    @property
    def target_type(self) -> type["VistaSlamRunner"]:
        return VistaSlamRunner


class VistaSlamRunner:
    def __init__(self, config: VistaSlamConfig) -> None:
        self.config = config

    def run_sequence(self, *, images_glob: str, output_dir: Path) -> None:
        ...
```

That same pattern should hold for MASt3R-SLAM and Nerfstudio wrappers.

## Shared Artifact Contract

Every backend wrapper should normalize into at least:

- `run_manifest.json`
- `input/`
- `slam/trajectory.tum`
- `slam/keyframes.json`
- `slam/sparse_points.ply`
- `dense/dense_points.ply` when available
- `logs/stdout.log`
- `logs/stderr.log`
- `meta/upstream_config_snapshot.*`

This is more important than preserving each upstream directory layout.

## Primary Sources

- Pydantic settings docs: <https://docs.pydantic.dev/latest/concepts/pydantic_settings/>
- Plotly graph objects docs: <https://plotly.com/python/graph-objects/>
- PyTorch3D README: <https://github.com/facebookresearch/pytorch3d>
- PyTorch3D batching note: <https://github.com/facebookresearch/pytorch3d/blob/main/docs/notes/batching.md>
- pytransform3d docs: <https://dfki-ric.github.io/pytransform3d/>
- Nerfstudio docs: <https://docs.nerf.studio/>
- Nerfstudio data conventions: <https://docs.nerf.studio/quickstart/data_conventions.html>
- ViSTA-SLAM paper: <https://arxiv.org/abs/2509.01584>
- ViSTA-SLAM repo: <https://github.com/zhangganlin/vista-slam>
- MASt3R-SLAM paper: <https://arxiv.org/abs/2412.12392>
- MASt3R-SLAM repo: <https://github.com/rmurai0610/MASt3R-SLAM>
