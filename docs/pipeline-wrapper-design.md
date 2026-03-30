# Pipeline Wrapper Design

This document translates the framework research and the two local paper-source trees into a concrete architecture for `prml_vslam`. It extends the current planner toward two execution modes:

- streaming
- batch / offline

The key idea is simple: the repo owns the configuration, artifact layout, normalization, evaluation, and reporting layers. External methods own their own inference internals.

## Core Separation

There should be two distinct configuration layers.

### Application settings

Use `pydantic-settings.BaseSettings` for:

- external repo roots
- environment roots
- dataset roots
- checkpoint caches
- default output roots

These values are machine-local and should not be treated as experiment artifacts.

### Runtime configs

Use `BaseConfig` for:

- run requests
- stage configs
- method configs
- evaluation configs
- plotting configs

These values belong to the experiment contract and should be serialized with the run.

## Lightweight Factory Pattern

The existing `BaseConfig` pattern is already the right direction. The next step is to compose it consistently.

```python
from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import Field

from prml_vslam.utils import BaseConfig


class PipelineMode(str, Enum):
    STREAMING = "streaming"
    BATCH = "batch"


class ArtifactLayoutConfig(BaseConfig):
    root: Path
    """Root artifact directory for the run."""


class MethodRunnerConfig(BaseConfig):
    name: str
    """Stable method name."""

    @property
    def target_type(self) -> type["MethodRunner"] | None:
        return MethodRunner


class MethodRunner:
    def __init__(self, config: MethodRunnerConfig) -> None:
        self.config = config
```

## Canonical Stage Superset

The repo should define a superset of canonical stage IDs and let each mode select the relevant subset.

### Shared stages

- `capture_manifest`
- `ingest`
- `frame_selection`
- `metadata_normalization`
- `method_prepare`
- `slam_run`
- `trajectory_normalization`
- `dense_normalization`
- `arcore_alignment`
- `reference_reconstruction`
- `trajectory_metrics`
- `dense_metrics`
- `visualization_export`
- `report_export`

### Streaming-specific stages

- `stream_source_open`
- `online_tracking`
- `online_local_mapping`
- `online_dense_preview`
- `operator_visualization`
- `chunk_persist`
- `stream_finalize`

### Batch-specific stages

- `video_decode`
- `sequence_chunking`
- `offline_global_optimization`
- `offline_dense_export`
- `cross_method_comparison`

## How the Papers Should Shape the Stages

The two VSLAM papers should influence the stage design directly, not just the choice of benchmark backends.

### Stages strongly informed by ViSTA-SLAM

- `online_tracking`
  - ViSTA-SLAM's symmetric two-view association frontend is a clean model for pairwise relative-pose and local-pointmap prediction in streaming.
- `online_local_mapping`
  - Its local pointmaps and per-view graph representation suggest that online local mapping should stay separate from later global normalization.
- `stream_finalize`
  - Its live mode means streaming runs should be able to flush partially built graph state and geometry at the end of a capture.
- `offline_global_optimization`
  - Its Sim(3) graph with loop closure and scale-only edges is a useful reference for the backend state that may need to survive normalization.

### Stages strongly informed by MASt3R-SLAM

- `online_tracking`
  - Its ray-space tracking formulation under a generic central camera assumption is a strong blueprint for uncalibrated tracking semantics.
- `online_local_mapping`
  - Its weighted local pointmap fusion is the clearest design reference for a future canonical local-map abstraction.
- `method_prepare`
  - Its calibrated and uncalibrated branches should remain explicit in our configs and planner.
- `offline_global_optimization`
  - Its second-order global optimization suggests that we should not reduce backend work to a generic "run backend" black box in the pipeline contract.
- `arcore_alignment`
  - The paper's careful distinction between generic central-camera processing and known-calibration refinement supports keeping alignment and calibrated evaluation stages explicit and separate.

## Recommended Stage Semantics

### `capture_manifest`

Create an immutable manifest describing:

- raw video path or stream source
- timestamps
- device metadata
- ARCore side-channel paths if present
- calibration hints if present

### `method_prepare`

Resolve:

- upstream repo root
- external environment
- checkpoints
- input mode
- calibrated or uncalibrated branch
- command-line arguments

This stage must fail early if the external backend is not runnable.

### `slam_run`

Run only the external backend. Do not mix evaluation, plotting, or report generation into it.

### `trajectory_normalization`

Convert backend-specific trajectory outputs into a shared repo format such as TUM plus a richer JSON sidecar. This is where frame conventions, timestamps, and scale-alignment metadata belong.

### `dense_normalization`

Convert backend-specific dense outputs into repo-owned geometry artifacts such as PLY plus metadata describing:

- coordinate frame
- units
- color availability
- point count
- calibration assumptions

### `arcore_alignment`

Treat ARCore as an external baseline source. It should never be a hidden part of a method wrapper.

### `reference_reconstruction`

Run COLMAP, Nerfstudio, or another reference pipeline to create comparison targets for custom captures.

### `trajectory_metrics`

Compute ATE, RPE, drift summaries, and alignment diagnostics. `evo` should sit behind this stage.

### `dense_metrics`

Compute dense alignment and quality metrics using Open3D, CloudCompare, or both.

### `visualization_export`

Generate Plotly dashboards and static figure exports from normalized artifacts and metrics, not from raw backend output folders.

## Streaming Pipeline

The streaming path should prioritize latency, incremental persistence, and operator-facing outputs.

Recommended order:

1. `capture_manifest`
2. `stream_source_open`
3. `method_prepare`
4. `online_tracking`
5. `online_local_mapping`
6. `online_dense_preview`
7. `operator_visualization`
8. `chunk_persist`
9. `stream_finalize`
10. `trajectory_normalization`
11. `dense_normalization`
12. `arcore_alignment`
13. `trajectory_metrics`
14. `dense_metrics`
15. `visualization_export`

Initial method priority:

- ViSTA-SLAM first, because the upstream repo already exposes live camera mode
- MASt3R-SLAM second, if we later decide to support a lower-latency live branch

## Batch Pipeline

The batch path should prioritize reproducibility, throughput, and highest-quality global outputs.

Recommended order:

1. `capture_manifest`
2. `video_decode`
3. `frame_selection`
4. `metadata_normalization`
5. `method_prepare`
6. `slam_run`
7. `offline_global_optimization`
8. `offline_dense_export`
9. `trajectory_normalization`
10. `dense_normalization`
11. `arcore_alignment`
12. `reference_reconstruction`
13. `trajectory_metrics`
14. `dense_metrics`
15. `cross_method_comparison`
16. `visualization_export`
17. `report_export`

Initial method priority:

- MASt3R-SLAM as the main dense-learning batch baseline
- ViSTA-SLAM as the main uncalibrated and lightweight comparison backend

## Stage Config Sketch

```python
from __future__ import annotations

from enum import Enum

from pydantic import Field

from prml_vslam.utils import BaseConfig


class StageId(str, Enum):
    CAPTURE_MANIFEST = "capture_manifest"
    METHOD_PREPARE = "method_prepare"
    SLAM_RUN = "slam_run"
    TRAJECTORY_NORMALIZATION = "trajectory_normalization"
    DENSE_NORMALIZATION = "dense_normalization"
    ARCORE_ALIGNMENT = "arcore_alignment"
    REFERENCE_RECONSTRUCTION = "reference_reconstruction"
    TRAJECTORY_METRICS = "trajectory_metrics"
    DENSE_METRICS = "dense_metrics"
    VISUALIZATION_EXPORT = "visualization_export"


class StageConfig(BaseConfig):
    id: StageId
    """Stable stage identifier."""

    enabled: bool = True
    """Whether the stage is enabled."""

    depends_on: list[StageId] = Field(default_factory=list)
    """Upstream stages that must complete first."""
```

## Wrapper Contract

Each external backend wrapper should expose one narrow runtime interface.

```python
from __future__ import annotations

from pathlib import Path

from prml_vslam.utils import BaseConfig


class MethodArtifacts(BaseConfig):
    trajectory_path: Path | None = None
    """Normalized trajectory output."""

    sparse_points_path: Path | None = None
    """Normalized sparse geometry output."""

    dense_points_path: Path | None = None
    """Normalized dense geometry output."""

    keyframe_metadata_path: Path | None = None
    """Normalized keyframe metadata output."""


class MethodRunner:
    def __init__(self, config: MethodRunnerConfig) -> None:
        self.config = config

    def prepare(self) -> None:
        """Validate environment, checkpoints, and upstream repo state."""
        raise NotImplementedError

    def run_batch(self, *, input_path: Path, artifact_dir: Path) -> MethodArtifacts:
        """Run the upstream method on a video or frame directory."""
        raise NotImplementedError

    def run_stream(self, *, source_uri: str, artifact_dir: Path) -> MethodArtifacts:
        """Run the upstream method on a streaming source."""
        raise NotImplementedError
```

Wrapper rules:

- one wrapper per upstream backend
- subprocess boundary by default
- explicit calibrated versus uncalibrated inputs
- explicit input and output paths
- no hidden global state
- persist upstream stdout and stderr
- normalize outputs immediately

## Artifact Layout

Use one repo-owned artifact layout independent of backend:

```text
artifacts/
  <experiment>/
    <method>/
      run_manifest.json
      input/
      slam/
      dense/
      evaluation/
      plots/
      logs/
      reference/
```

This is the right boundary between external tools and the rest of the repo.

## Practical Next Steps

- add `pydantic-settings` once the first real settings model lands
- implement one wrapper module per backend under `src/prml_vslam/methods/`
- expand the current planner enums toward the canonical stage superset above
- add normalization helpers under `src/prml_vslam/io/`
- add tests that validate command construction and artifact discovery without running the heavy external methods in CI
