# PRML VSLAM Pipeline Guide

This package owns the typed planning contracts, the currently implemented
tracking/runtime protocols, and the artifact-boundary definitions for the
repository pipeline.

## Current State

Today `prml_vslam.pipeline` is primarily a typed planning surface:

- `contracts.py` defines the public request, plan, manifest, artifact, and
  streaming-update DTOs
- `services.py` turns a `RunRequest` into an ordered `RunPlan`
- `protocols.py` defines the currently implemented streaming-source and
  tracking-backend seams
- `workspace.py` defines the capture-manifest helper models used while
  materializing sequences

The generic `OfflineRunner` and `StreamingRunner` described in
[`REQUIREMENTS.md`](./REQUIREMENTS.md) are target architecture, not implemented
package surfaces yet.

There is one executable demo today:

- the Streamlit `Pipeline` page builds a real `RunRequest`, materializes a real
  `SequenceManifest`, replays ADVIO frames, and feeds them into the repository
  local `MockTrackingRuntime`

That demo lives in `prml_vslam.app`, not in `prml_vslam.pipeline`, because it
is a bounded monitoring surface rather than the final reusable runner API.

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
  - implements the repository-local `MockTrackingRuntime` used by both the
    streaming demo loop and the offline mock path
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
    streaming tracking
- [`../protocols/runtime.py`](../protocols/runtime.py)
  - defines `FramePacketStream`, the shared frame-stream protocol used by
    replay and streaming tracking
- [`../app/plotting/record3d.py`](../app/plotting/record3d.py)
  - builds the live trajectory figure shown on the Pipeline page
- [`contracts.py`](./contracts.py)
  - defines `RunRequest`, `RunPlan`, `SequenceManifest`, `StageManifest`,
    `RunSummary`, `TrackingUpdate`, and the typed artifact bundles that the
    demo exercises
- [`protocols.py`](./protocols.py)
  - defines `StreamingSequenceSource`, `OfflineTrackerBackend`, and
    `StreamingTrackerBackend`, the only currently implemented package-local
    behavior seams
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
tracking backend consumes packets one at a time via `open(...)`, `step(...)`,
and `close()`.

The intended long-term flow is:

1. live ingress produces `FramePacket`
2. streaming tracking produces `TrackingUpdate`
3. capture or replay is materialized into `SequenceManifest`
4. downstream artifact stages consume materialized outputs, not live frames

## Core Contracts

### Entry Contract

- `RunRequest`
  - the config-defined entry point for both offline and streaming pipelines
  - owns `mode`, `source`, `tracking`, optional `dense`, optional `reference`,
    and `evaluation`

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
  - canonical stage ids such as `ingest`, `slam`, `dense_mapping`, and
    `summary`

### Shared Normalization Boundary

- `SequenceManifest`
  - the single normalized boundary between source-specific ingestion and the
    main benchmark stages
  - points to materialized or resolved inputs such as video, frames,
    timestamps, intrinsics, and optional reference trajectories

### Stage Outputs

- `TrackingArtifacts`
- `DenseArtifacts`

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

## Runtime Interfaces

`protocols.py` defines the behavior seams that are actually consumed by the
current planner and streaming session.

### Tracking

- `OfflineTrackerBackend`
  - `run_sequence(sequence, cfg, artifact_root) -> TrackingArtifacts`
  - used when tracking consumes a fully materialized `SequenceManifest`
- `StreamingTrackerBackend`
  - `open(cfg, artifact_root) -> None`
  - `step(frame) -> TrackingUpdate`
  - `close() -> TrackingArtifacts`
  - used when tracking consumes `FramePacket` incrementally

The important boundary rule is simple:

- streaming logic may consume `FramePacket`
- downstream stages should consume typed artifact bundles or
  `SequenceManifest`, not live packets

Future dense, reference, and evaluation stages can introduce additional
protocols later, but those seams should be added only when a concrete runtime
or service needs them.

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
tracking config.

```python
from pathlib import Path

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts import (
    BenchmarkEvaluationConfig,
    DenseConfig,
    ReferenceConfig,
    TrackingConfig,
    VideoSourceSpec,
)
from prml_vslam.utils import PathConfig

request = RunRequest(
    experiment_name="office-offline-vista",
    mode=PipelineMode.OFFLINE,
    output_dir=Path("artifacts"),
    source=VideoSourceSpec(video_path=Path("captures/office.mp4"), frame_stride=2),
    tracking=TrackingConfig(method=MethodId.VISTA),
    dense=DenseConfig(enabled=False),
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
from prml_vslam.pipeline.contracts import DatasetSourceSpec, TrackingConfig

request = RunRequest(
    experiment_name="advio-office-vista",
    output_dir=Path("artifacts"),
    source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id="advio-15"),
    tracking=TrackingConfig(method=MethodId.VISTA),
)
```

## Defining A Streaming Pipeline

A streaming plan uses `PipelineMode.STREAMING` together with `LiveSourceSpec`.

```python
from pathlib import Path

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts import LiveSourceSpec, TrackingConfig

request = RunRequest(
    experiment_name="record3d-live-vista",
    mode=PipelineMode.STREAMING,
    output_dir=Path("artifacts"),
    source=LiveSourceSpec(source_id="record3d_usb", persist_capture=True),
    tracking=TrackingConfig(method=MethodId.VISTA),
)
```

Planning a streaming run does not itself start the stream. It defines the
intended topology, stage set, and artifact root for a future runner.

## Current Ways To Use The Contracts

### CLI Planning

`prml_vslam.main.plan_run` constructs a `RunRequest` from CLI arguments and
prints the resulting `RunPlan`. This is the current offline planning entrypoint.

### Streamlit Monitoring Demo

The `Pipeline` page demonstrates the same contracts in an executable but
bounded way:

1. build a `RunRequest`
2. build a `RunPlan`
3. materialize an ADVIO-backed `SequenceManifest`
4. open an ADVIO replay stream
5. run the repository-local `MockTrackingRuntime`
6. display frames, trajectory, stage manifests, artifacts, and summary

This demo supports:

- `offline` as one replay pass
- `streaming` as looped replay with the same incremental tracking interface

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
6. Define the execution protocol in `protocols.py` if the stage introduces a
   new reusable execution seam.
7. Wire the executor surface.
   - For the current demo this means `prml_vslam.pipeline.session`.
   - Keep the Streamlit page as a thin client over the pipeline-owned service.
8. Persist `StageManifest` and update `RunSummary`.
9. Add tests for planning, artifact-path layout, and execution behavior.

If the new stage needs live `FramePacket` access, challenge that decision
first. In this repository, only ingress and streaming tracking should normally
operate on live packets. Most later stages should run on materialized
artifacts.

## Recommended Extension Pattern

Use the following decision rule:

- if a capability consumes a full materialized sequence, model it as an
  offline stage
- if a capability must react frame by frame, model it as streaming tracking or
  as observability around streaming tracking
- if a capability produces reusable geometry or metrics, materialize it as a
  typed artifact bundle

## Related Files

- [`contracts.py`](./contracts.py)
- [`protocols.py`](./protocols.py)
- [`session.py`](./session.py)
- [`services.py`](./services.py)
- [`workspace.py`](./workspace.py)
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
