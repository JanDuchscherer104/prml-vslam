# PRML VSLAM Pipeline Guide

This package owns the typed planning contracts and artifact-boundary
definitions for the repository pipeline. Shared source-provider protocols live
under `prml_vslam.protocols.*`, and SLAM backend/session protocols live under
`prml_vslam.methods.protocols`.

## Current State

Today `prml_vslam.pipeline` is primarily a typed planning surface:

- `contracts.py` defines the public request, plan, manifest, artifact, and
  streaming-update DTOs
- `services.py` turns a `RunRequest` into an ordered `RunPlan`
- `workspace.py` defines the capture-manifest helper models used while
  materializing sequences

The generic `OfflineRunner` and `StreamingRunner` described in
[`REQUIREMENTS.md`](./REQUIREMENTS.md) are target architecture, not implemented
package surfaces yet.

There is one executable demo today:

- the Streamlit `Pipeline` page builds a real `RunRequest`, materializes a real
  `SequenceManifest`, replays ADVIO frames, and feeds them into the repository
  local `MockSlamBackend`

That demo lives in `prml_vslam.app`, not in `prml_vslam.pipeline`, because it
is a bounded monitoring surface rather than the final reusable runner API.

The current executable `RunService` slice only supports the `ingest`, `slam`,
and `summary` stages. The planner can still describe reference and evaluation
stages, but the bounded runtime rejects those stage ids until explicit runtime
support is added.

## Current Streaming Demo Implementation

The current runnable streaming demo is split across the following files.

- [`../app/pages/pipeline.py`](../app/pages/pipeline.py)
  - renders the `Pipeline` page, persists selector-only UI state, and drives
    the pipeline-owned session service
- [`session.py`](./session.py)
  - owns the background worker, runtime snapshot, stage-manifest updates, and
    final `RunSummary`
- [`../app/bootstrap.py`](../app/bootstrap.py)
  - wires the pipeline page and `PipelineSessionService` into the packaged
    Streamlit app
- [`../app/state.py`](../app/state.py)
  - persists the opaque pipeline session service in Streamlit session state
- [`../app/models.py`](../app/models.py)
  - defines the persisted `PipelinePageState` used by the page controls
- [`../methods/mock_vslam.py`](../methods/mock_vslam.py)
  - implements the repository-local `MockSlamBackend` and `MockSlamSession`
    used by both the streaming demo loop and the offline mock path
- [`../datasets/advio_service.py`](../datasets/advio_service.py)
  - exposes ADVIO helpers that build a pipeline-facing replay source plus the
    normalized `SequenceManifest`
- [`../datasets/advio_sequence.py`](../datasets/advio_sequence.py)
  - materializes ADVIO scenes into `SequenceManifest` and forwards replay
    requests into the adapter layer
- [`../datasets/advio_replay_adapter.py`](../datasets/advio_replay_adapter.py)
  - converts ADVIO video, timestamps, calibration, and optional reference
    poses into a `FramePacketStream`
- [`../io/cv2_producer.py`](../io/cv2_producer.py)
  - provides the replay-capable OpenCV `FramePacketStream` used by the ADVIO
    demo
- [`../interfaces/runtime.py`](../interfaces/runtime.py)
  - defines `FramePacket`, the shared live-frame datamodel used by replay and
    streaming SLAM
- [`../protocols/runtime.py`](../protocols/runtime.py)
  - defines `FramePacketStream`, the shared frame-stream protocol used by
    replay and streaming SLAM
- [`../protocols/source.py`](../protocols/source.py)
  - defines `OfflineSequenceSource` and `StreamingSequenceSource`, the shared
    source-provider seams consumed by pipeline orchestration
- [`../methods/protocols.py`](../methods/protocols.py)
  - defines `OfflineSlamBackend`, `StreamingSlamBackend`, `SlamBackend`, and
    `SlamSession`, the SLAM behavior seams consumed by the pipeline
- [`../app/plotting/record3d.py`](../app/plotting/record3d.py)
  - builds the live trajectory figure shown on the Pipeline page
- [`contracts.py`](./contracts.py)
  - defines `RunRequest`, `RunPlan`, `SequenceManifest`, `StageManifest`,
    `RunSummary`, `SlamUpdate`, and the typed artifact bundles that the
    demo exercises
- [`services.py`](./services.py)
  - defines `RunPlannerService`, which turns the page-built `RunRequest` into
    the ordered `RunPlan`
- [`../utils/path_config.py`](../utils/path_config.py)
  - defines `PathConfig.plan_run_paths(...)`, the canonical artifact layout
    used by the demo controller and runtime

## Two Pipeline Modes

The pipeline supports two top-level modes through `PipelineMode`.

### Offline

Use `PipelineMode.OFFLINE` when the input is already bounded and replayable:

- a raw video file
- a dataset sequence such as ADVIO
- a previously captured live session that has already been materialized

Offline runs are artifact-first. The caller defines a `RunRequest`, builds a
`RunPlan`, materializes or resolves a `SequenceManifest`, and then executes the
enabled stages in order.

### Streaming

Use `PipelineMode.STREAMING` when the input arrives incrementally:

- a live camera feed
- a device stream such as Record3D USB or Wi-Fi
- an offline replay that should behave like a stream for monitoring purposes

Streaming mode still uses the same stage vocabulary, but its hot path is
frame-driven. The shared runtime unit is `FramePacket`, and the streaming-capable
SLAM session consumes packets one at a time via `start_session(...)`,
`step(...)`, and `close()`.

The intended long-term flow is:

1. live ingress produces `FramePacket`
2. streaming SLAM produces `SlamUpdate`
3. capture or replay is materialized into `SequenceManifest`
4. downstream artifact stages consume materialized outputs, not live frames

## Core Contracts

### Entry Contract

- `RunRequest`
  - the config-defined entry point for both offline and streaming pipelines
  - owns `mode`, `source`, `slam`, optional `reference`, and `evaluation`

### Source Contracts

- `VideoSourceSpec`
  - offline video input
- `DatasetSourceSpec`
  - offline dataset-backed input
- `LiveSourceSpec`
  - streaming input with explicit capture persistence semantics

### Planned Execution

- `RunPlan`
  - ordered list of `RunPlanStage`
  - owns `run_id`, `artifact_root`, `method`, `mode`, and selected `source`
- `RunPlanStageId`
  - canonical stage ids such as `ingest`, `slam`, and `summary`

### Shared Normalization Boundary

- `SequenceManifest`
  - the single normalized boundary between source-specific ingestion and the
    main benchmark stages
  - points to materialized or resolved inputs such as video, frames,
    timestamps, intrinsics, and optional reference trajectories
  - must always provide a stable `sequence_id`; populate the optional artifact
    paths whenever the source knows them

### Stage Outputs

- `SlamArtifacts`

Large outputs must cross stage boundaries as artifact references, not large
in-memory payloads.

Reference-stage and evaluation-stage artifact bundles are still target-state
concepts described in [`REQUIREMENTS.md`](./REQUIREMENTS.md). They should only
be added to `contracts.py` once a real pipeline stage consumes or produces
them.

### Provenance And Summary

- `StageManifest`
  - one record per stage containing config hash, input fingerprint, output
    paths, and execution status
- `RunSummary`
  - final top-level summary containing the artifact root and stage status map

### Minimum Structural Requirements

- source adapters
  - offline sources must provide `label` and
    `prepare_sequence_manifest(output_dir) -> SequenceManifest`
  - streaming sources must additionally provide
    `open_stream(*, loop: bool) -> FramePacketStream`
- SLAM backends
  - offline backends must expose `method_id` and
    `run_sequence(sequence, cfg, artifact_root) -> SlamArtifacts`
  - streaming backends must expose `method_id` and
    `start_session(cfg, artifact_root) -> SlamSession`
- SLAM sessions
  - must implement `step(frame) -> SlamUpdate` and `close() -> SlamArtifacts`
- SLAM artifacts
  - must always include `trajectory_tum`
  - `sparse_points_ply`, `dense_points_ply`, and `preview_log_jsonl` remain
    optional

## Runtime Interfaces

The current planner and streaming session consume shared source-provider
protocols from `prml_vslam.protocols.source` and SLAM behavior seams from
`prml_vslam.methods.protocols`.

### SLAM

- `OfflineSlamBackend`
  - `run_sequence(sequence, cfg, artifact_root) -> SlamArtifacts`
  - used for materialized-sequence execution
- `StreamingSlamBackend`
  - `start_session(cfg, artifact_root) -> SlamSession`
  - used for incremental frame-driven execution
- `SlamBackend`
  - convenience combined protocol for backends that implement both execution modes
- `SlamSession`
  - `step(frame) -> SlamUpdate`
  - `close() -> SlamArtifacts`
  - used when SLAM consumes `FramePacket` incrementally

The important boundary rule is simple:

- streaming logic may consume `FramePacket`
- downstream stages should consume typed artifact bundles or
  `SequenceManifest`, not live packets

## Artifact Layout

`PathConfig.plan_run_paths(...)` returns the canonical artifact layout for one
run through `RunArtifactPaths`.

Important paths include:

- `input/sequence_manifest.json`
- `slam/trajectory.tum`
- `slam/sparse_points.ply`
- `dense/dense_points.ply`
- `reference/reference_cloud.ply`
- `evaluation/*.json`
- `summary/run_summary.json`

Stages should write into these canonical locations instead of inventing
stage-local layouts.

## Defining An Offline Pipeline

The smallest offline pipeline is a `RunRequest` with an offline source and a
SLAM config.

```python
from pathlib import Path

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts import (
    BenchmarkEvaluationConfig,
    ReferenceConfig,
    SlamConfig,
    VideoSourceSpec,
)
from prml_vslam.utils import PathConfig

request = RunRequest(
    experiment_name="office-offline-vista",
    mode=PipelineMode.OFFLINE,
    output_dir=Path(".artifacts"),
    source=VideoSourceSpec(video_path=Path("captures/office.mp4"), frame_stride=2),
    slam=SlamConfig(method=MethodId.VISTA, emit_dense_points=False),
    reference=ReferenceConfig(enabled=False),
    evaluation=BenchmarkEvaluationConfig(
        compare_to_arcore=False,
        evaluate_cloud=False,
        evaluate_efficiency=True,
    ),
)

plan = request.build(PathConfig())
```

A dataset-backed offline request uses `DatasetSourceSpec` instead of
`VideoSourceSpec`.

```python
from pathlib import Path

from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import RunRequest
from prml_vslam.pipeline.contracts import DatasetSourceSpec, SlamConfig

request = RunRequest(
    experiment_name="advio-office-vista",
    output_dir=Path(".artifacts"),
    source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id="advio-15"),
    slam=SlamConfig(method=MethodId.VISTA),
)
```

## Defining A Streaming Pipeline

A streaming plan uses `PipelineMode.STREAMING` together with `LiveSourceSpec`.

```python
from pathlib import Path

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts import LiveSourceSpec, SlamConfig

request = RunRequest(
    experiment_name="record3d-live-vista",
    mode=PipelineMode.STREAMING,
    output_dir=Path(".artifacts"),
    source=LiveSourceSpec(source_id="record3d_usb", persist_capture=True),
    slam=SlamConfig(method=MethodId.VISTA),
)
```

Planning a streaming run does not itself start the stream. It defines the
intended topology, stage set, and artifact root for a future runner.

## Current Ways To Use The Contracts

### CLI Planning

`prml_vslam.main.plan_run` constructs a `RunRequest` from CLI arguments and
prints the resulting `RunPlan`. This is the current offline planning entrypoint.

### TOML Configs

`prml_vslam.main.plan_run_config` resolves the TOML file itself through
`PathConfig.resolve_toml_path(...)`, then hydrates `RunRequest` via
`RunRequest.from_toml(...)`.

Important nuance: only the TOML file path is repo-resolved automatically.
Nested TOML paths such as `source.video_path` and `slam.config_path` are
validated as written. If a caller wants repo-relative behavior for those inner
paths, resolve them explicitly through `PathConfig`.

`prml_vslam.main.plan_run_config` loads a persisted `RunRequest` TOML from
`.configs/pipelines/*.toml` by default. Bare filenames resolve into that repo
config directory through `PathConfig.resolve_pipeline_config_path(...)`.

### Streamlit Monitoring Demo

The `Pipeline` page demonstrates the same contracts in an executable but
bounded way:

1. build a `RunRequest`
2. build a `RunPlan`
3. materialize an ADVIO-backed `SequenceManifest`
4. open an ADVIO replay stream
5. run the repository-local `MockSlamBackend`
6. display frames, trajectory, stage manifests, artifacts, and summary

This demo supports:

- `offline` as one replay pass
- `streaming` as looped replay with the same incremental SLAM interface

## Persisting A Pipeline Config

The repo-owned way to persist a durable pipeline request is:

```python
from prml_vslam.pipeline.demo import save_run_request_toml
from prml_vslam.utils import PathConfig

path_config = PathConfig()
request = ...
config_path = save_run_request_toml(
    path_config=path_config,
    request=request,
    config_path="advio-office-vista.toml",
)
```

When `config_path` is a bare filename, it is written to
`.configs/pipelines/<name>.toml`. Explicit relative paths keep their repo-root
anchoring.

## Configuring Stages Via TOML

`RunRequest` owns stage-specific config as nested config models, so the TOML
uses one table per nested config:

```toml
experiment_name = "advio-office-offline-vista"
mode = "offline"
output_dir = ".artifacts"

[source]
dataset_id = "advio"
sequence_id = "advio-15"

[slam]
method = "vista"
config_path = ".configs/methods/vista/demo.toml"
max_frames = 300
emit_dense_points = true
emit_sparse_points = true

[reference]
enabled = false

[evaluation]
compare_to_arcore = true
evaluate_cloud = false
evaluate_efficiency = true
```

The rule is simple:

- fields on `RunRequest` stay top-level
- fields on `SlamConfig` go under `[slam]`
- fields on `ReferenceConfig` go under `[reference]`
- fields on `BenchmarkEvaluationConfig` go under `[evaluation]`

`[source]` is a tagged-by-shape union. Choose exactly one source shape:

- video source: `video_path`, optional `frame_stride`
- dataset source: `dataset_id`, `sequence_id`
- live source: `source_id`, optional `persist_capture`

## Common Questions

### Which Stages Actually Execute Today?

The planner can describe:

- `ingest`
- `slam`
- `reference_reconstruction`
- `trajectory_evaluation`
- `cloud_evaluation`
- `efficiency_evaluation`
- `summary`

The current bounded `RunService` runtime only executes:

- `ingest`
- `slam`
- `summary`

Reference and evaluation stages are still planned architecture in this package.

### Which Modules Own Which Boundaries?

- `pipeline/contracts.py`
  - stage DTOs, plan DTOs, manifests, summaries, and artifact bundles
- `pipeline/services.py`
  - planner wiring and stage selection
- `pipeline/run_service.py`
  - app-facing facade for the current runnable slice
- `pipeline/session.py`
  - current bounded runtime execution and manifest finalization
- `protocols/source.py`
  - source-provider behavior seams
- `methods/protocols.py`
  - SLAM backend and session behavior seams
- `utils/path_config.py`
  - canonical artifact layout and repo-owned config-path resolution

### What Happens If I Omit Optional Stage Config?

`ReferenceConfig.enabled` defaults to `false`.

`BenchmarkEvaluationConfig` defaults to:

- `compare_to_arcore = true`
- `evaluate_cloud = false`
- `evaluate_efficiency = true`

`SlamConfig` defaults to:

- `emit_dense_points = true`
- `emit_sparse_points = true`

So a minimal `RunRequest` with only `source` and `slam` plans:

- `ingest`
- `slam`
- `trajectory_evaluation`
- `efficiency_evaluation`
- `summary`

### Which TOML Paths Are Auto-Resolved?

- the TOML file passed to `plan-run-config`
- bare filenames passed through the repo-owned pipeline-config helpers

Nested fields inside the TOML are not rewritten automatically. Paths such as:

- `source.video_path`
- `slam.config_path`
- `output_dir`

are hydrated exactly as written and should be resolved explicitly through
`PathConfig` when a runtime wants repo-relative behavior.

### What Is The Minimum Valid `SequenceManifest`?

Structurally, `SequenceManifest` only requires `sequence_id`.

Recommended population by source kind:

- video-backed sources
  - `sequence_id`, `video_path`
  - add `timestamps_path` and `intrinsics_path` when known
- dataset-backed sources
  - `sequence_id`
  - populate dataset-derived `video_path`, `timestamps_path`,
    `intrinsics_path`, `reference_tum_path`, and `arcore_tum_path` whenever
    available
- live or replay captures
  - `sequence_id`
  - include whichever persisted capture artifacts are already materialized for
    downstream stages

### Which Artifacts Are Mandatory Vs Optional?

- ingest
  - required: `input/sequence_manifest.json`
- slam
  - required: `slam/trajectory.tum`
  - optional: `slam/sparse_points.ply`
  - optional: `dense/dense_points.ply`
  - optional: live preview/event log artifact
- summary
  - required: `summary/run_summary.json`
  - required: `summary/stage_manifests.json`

Reference and evaluation artifact bundles should only become mandatory after
those stages gain real runtime support.

### Which Files Usually Change When Adding A Runnable Stage?

At minimum, expect to touch:

- `pipeline/contracts.py`
- `pipeline/services.py`
- `utils/path_config.py`
- `pipeline/run_service.py`
- `pipeline/session.py`
- the owning protocol module when a new reusable execution seam is introduced
- `tests/test_pipeline.py`
- path or CLI tests when config/layout behavior changes

## How To Add A Stage

When adding a stage, change the typed contracts first and the runner wiring
second.

1. Decide whether the new stage is a major artifact boundary.
   - If yes, define or extend a typed artifact bundle in `contracts.py`.
2. Add or extend the enabling config in `RunRequest`.
   - Optional stages should be config-gated, not implied by side effects.
3. Add a new `RunPlanStageId` value in `contracts.py`.
4. Add canonical output path ownership in `RunArtifactPaths`.
   - The path layout belongs to `PathConfig`, not to the app or backend.
5. Insert the stage into `RunPlannerService._build_stages(...)`.
   - Give it a stable title, summary, and explicit outputs.
6. Define the execution protocol in the owning package protocol module if the
   stage introduces a new reusable execution seam.
   - source-provider seams live in `prml_vslam.protocols.source`
   - SLAM backend/session seams live in `prml_vslam.methods.protocols`
   - add a new `<package>/protocols.py` only when that package truly owns a
     new reusable behavior boundary
7. Wire the executor surface.
   - For the current demo this means `prml_vslam.pipeline.session`.
   - Keep the Streamlit page as a thin client over the pipeline-owned service.
8. Persist `StageManifest` and update `RunSummary`.
9. Add tests for planning, artifact-path layout, and execution behavior.

For the current runnable slice, extending the planner is not enough. If the
new stage must execute in the bounded demo, also extend the stage support in
`RunService` and the finalization logic in `PipelineSessionService`.

If the new stage needs live `FramePacket` access, challenge that decision
first. In this repository, only ingress and streaming SLAM should normally
operate on live packets. Most later stages should run on materialized
artifacts.

## Recommended Extension Pattern

Use the following decision rule:

- if a capability consumes a full materialized sequence, model it as an
  offline stage
- if a capability must react frame by frame, model it as streaming SLAM or as
  observability around streaming SLAM
- if a capability produces reusable geometry or metrics, materialize it as a
  typed artifact bundle

## Related Files

- [`contracts.py`](./contracts.py)
- [`session.py`](./session.py)
- [`run_service.py`](./run_service.py)
- [`services.py`](./services.py)
- [`workspace.py`](./workspace.py)
- [`../methods/protocols.py`](../methods/protocols.py)
- [`../protocols/source.py`](../protocols/source.py)
- [`../app/pages/pipeline.py`](../app/pages/pipeline.py)
- [`../methods/mock_vslam.py`](../methods/mock_vslam.py)
- [`../datasets/advio_service.py`](../datasets/advio_service.py)
- [`../datasets/advio_sequence.py`](../datasets/advio_sequence.py)
- [`../datasets/advio_replay_adapter.py`](../datasets/advio_replay_adapter.py)
- [`../io/cv2_producer.py`](../io/cv2_producer.py)
- [`../interfaces/runtime.py`](../interfaces/runtime.py)
- [`../protocols/runtime.py`](../protocols/runtime.py)
- [`../utils/path_config.py`](../utils/path_config.py)
- [`REQUIREMENTS.md`](./REQUIREMENTS.md)
