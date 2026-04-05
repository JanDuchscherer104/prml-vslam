# PRML VSLAM Pipeline Guide

This package owns the typed planning contracts, stage protocols, and
artifact-boundary definitions for the repository pipeline.

## Current State

Today `prml_vslam.pipeline` is primarily a typed planning surface:

- [`contracts.py`](./contracts.py) defines the public request, plan, manifest,
  and artifact DTOs
- [`services.py`](./services.py) turns a
  [`RunRequest`](./contracts.py#L99) into an ordered
  [`RunPlan`](./contracts.py#L166)
- [`interfaces.py`](./interfaces.py) defines the protocol surface that future
  runners and backends must satisfy
- [`workspace.py`](./workspace.py) defines prepared-input and capture-manifest
  helper models

The generic `OfflineRunner` and `StreamingRunner` described in
[`REQUIREMENTS.md`](./REQUIREMENTS.md) are target architecture, not implemented
package surfaces yet.

There is one executable demo today:

- the Streamlit `Pipeline` page builds a real
  [`RunRequest`](./contracts.py#L99), materializes a real
  [`SequenceManifest`](./contracts.py#L194), replays ADVIO frames, and feeds
  them into the repository-local
  [`MockTrackingRuntime`](../methods/mock_tracking.py#L33)

That demo lives in `prml_vslam.app`, not in `prml_vslam.pipeline`, because it
is a bounded monitoring surface rather than the final reusable runner API.

## Key Source Map

- [`PipelineMode`](./contracts.py#L16),
  [`VideoSourceSpec`](./contracts.py#L23),
  [`DatasetSourceSpec`](./contracts.py#L34),
  [`LiveSourceSpec`](./contracts.py#L45),
  [`TrackingConfig`](./contracts.py#L59),
  [`RunRequest`](./contracts.py#L99),
  [`RunPlanStageId`](./contracts.py#L140),
  [`RunPlanStage`](./contracts.py#L153),
  [`RunPlan`](./contracts.py#L166),
  [`SequenceManifest`](./contracts.py#L194),
  [`TrackingArtifacts`](./contracts.py#L213),
  [`DenseArtifacts`](./contracts.py#L224),
  [`ReferenceArtifacts`](./contracts.py#L231),
  [`TrajectoryMetrics`](./contracts.py#L245),
  [`CloudMetrics`](./contracts.py#L249),
  [`EfficiencyMetrics`](./contracts.py#L253),
  [`StageManifest`](./contracts.py#L265),
  [`RunSummary`](./contracts.py#L280)
- [`TrackingUpdate`](./interfaces.py#L24),
  [`OfflineTrackerBackend`](./interfaces.py#L40),
  [`StreamingTrackerBackend`](./interfaces.py#L54),
  [`DenseBackend`](./interfaces.py#L69),
  [`ReferenceBuilder`](./interfaces.py#L76),
  [`TrajectoryEvaluator`](./interfaces.py#L88),
  [`CloudEvaluator`](./interfaces.py#L100)
- [`RunPlannerService`](./services.py#L19) and
  [`RunPlannerService.build_run_plan(...)`](./services.py#L27)
- [`FrameSample`](./workspace.py#L13),
  [`CaptureManifest`](./workspace.py#L29),
  [`PreparedInput`](./workspace.py#L48)
- [`RunArtifactPaths`](../utils/path_config.py#L20) and
  [`PathConfig.plan_run_paths(...)`](../utils/path_config.py#L185)
- [`FramePacket`](../interfaces/runtime.py#L17) and
  [`FramePacketStream`](../interfaces/runtime.py#L35)
- [`MethodId`](../methods/interfaces.py#L18)
- [`MockTrackingRuntimeConfig`](../methods/mock_tracking.py#L18) and
  [`MockTrackingRuntime`](../methods/mock_tracking.py#L33)
- [`AdvioDatasetService.build_sequence_manifest(...)`](../datasets/advio_service.py#L68)
  and [`AdvioDatasetService.open_preview_stream(...)`](../datasets/advio_service.py#L71)
- [`PipelineDemoRuntimeController`](../app/pipeline_runtime.py#L106)

## Two Pipeline Modes

The pipeline supports two top-level modes through
[`PipelineMode`](./contracts.py#L16).

### Offline

Use [`PipelineMode.OFFLINE`](./contracts.py#L19) when the input is already
bounded and replayable:

- a raw video file
- a dataset sequence such as ADVIO
- a previously captured live session that has already been materialized

Offline runs are artifact-first. The caller defines a
[`RunRequest`](./contracts.py#L99), builds a
[`RunPlan`](./contracts.py#L166), materializes or resolves a
[`SequenceManifest`](./contracts.py#L194), and then executes the enabled
stages in order.

### Streaming

Use [`PipelineMode.STREAMING`](./contracts.py#L20) when the input arrives
incrementally:

- a live camera feed
- a device stream such as Record3D USB or Wi-Fi
- an offline replay that should behave like a stream for monitoring purposes

Streaming mode still uses the same stage vocabulary, but its hot path is
frame-driven. The shared runtime unit is
[`FramePacket`](../interfaces/runtime.py#L17), and the
[`StreamingTrackerBackend`](./interfaces.py#L54) consumes packets one at a time
via `open(...)`, `step(...)`, and `close()`.

The intended long-term flow is:

1. live ingress produces [`FramePacket`](../interfaces/runtime.py#L17)
2. streaming tracking produces [`TrackingUpdate`](./interfaces.py#L24)
3. capture or replay is materialized into [`SequenceManifest`](./contracts.py#L194)
4. downstream artifact stages consume materialized outputs, not live frames

## Core Contracts

### Entry Contract

- [`RunRequest`](./contracts.py#L99)
  - the config-defined entry point for both offline and streaming pipelines
  - owns `mode`, `source`, `tracking`, optional `dense`, optional `reference`,
    and `evaluation`

### Source Contracts

- [`VideoSourceSpec`](./contracts.py#L23)
  - offline video input
- [`DatasetSourceSpec`](./contracts.py#L34)
  - offline dataset-backed input
- [`LiveSourceSpec`](./contracts.py#L45)
  - streaming input with explicit capture persistence semantics

### Planned Execution

- [`RunPlan`](./contracts.py#L166)
  - ordered list of `RunPlanStage`
  - owns `run_id`, `artifact_root`, `method`, `mode`, and selected `source`
- [`RunPlanStage`](./contracts.py#L153)
  - one typed stage row in the ordered plan
- [`RunPlanStageId`](./contracts.py#L140)
  - canonical stage ids such as `ingest`, `slam`, `dense_mapping`, and
    `summary`

### Shared Normalization Boundary

- [`SequenceManifest`](./contracts.py#L194)
  - the single normalized boundary between source-specific ingestion and the
    main benchmark stages
  - points to materialized or resolved inputs such as video, frames,
    timestamps, intrinsics, and optional reference trajectories

### Stage Outputs

- [`TrackingArtifacts`](./contracts.py#L213)
- [`DenseArtifacts`](./contracts.py#L224)
- [`ReferenceArtifacts`](./contracts.py#L231)
- [`TrajectoryMetrics`](./contracts.py#L245)
- [`CloudMetrics`](./contracts.py#L249)
- [`EfficiencyMetrics`](./contracts.py#L253)

Large outputs must cross stage boundaries as artifact references, not large
in-memory payloads.

### Provenance And Summary

- [`StageManifest`](./contracts.py#L265)
  - one record per stage containing config hash, input fingerprint, output
    paths, and execution status
- [`RunSummary`](./contracts.py#L280)
  - final top-level summary containing the artifact root and stage status map

## Runtime Interfaces

[`interfaces.py`](./interfaces.py) defines the stage-level protocol surface.

### Tracking

- [`OfflineTrackerBackend`](./interfaces.py#L40)
  - `run_sequence(sequence, cfg, artifact_root) -> TrackingArtifacts`
  - used when tracking consumes a fully materialized `SequenceManifest`
- [`StreamingTrackerBackend`](./interfaces.py#L54)
  - `open(cfg, artifact_root) -> None`
  - `step(frame) -> TrackingUpdate`
  - `close() -> TrackingArtifacts`
  - used when tracking consumes `FramePacket` incrementally

### Other Stages

- [`DenseBackend`](./interfaces.py#L69)
  - consumes `TrackingArtifacts`
- [`ReferenceBuilder`](./interfaces.py#L76)
  - consumes `SequenceManifest`
- [`TrajectoryEvaluator`](./interfaces.py#L88)
  - consumes `TrackingArtifacts` plus `SequenceManifest`
- [`CloudEvaluator`](./interfaces.py#L100)
  - consumes `DenseArtifacts` plus `ReferenceArtifacts`

The important boundary rule is simple:

- streaming logic may consume [`FramePacket`](../interfaces/runtime.py#L17)
- downstream stages should consume typed artifact bundles or
  `SequenceManifest`, not live packets

## Artifact Layout

[`PathConfig.plan_run_paths(...)`](../utils/path_config.py#L185) returns the
canonical artifact layout for one run through
[`RunArtifactPaths`](../utils/path_config.py#L20).

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

The smallest offline pipeline is a [`RunRequest`](./contracts.py#L99) with an
offline source and a [`TrackingConfig`](./contracts.py#L59).

```python
from pathlib import Path

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import (
    BenchmarkEvaluationConfig,
    DenseConfig,
    PipelineMode,
    ReferenceConfig,
    RunRequest,
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

A dataset-backed offline request uses
[`DatasetSourceSpec`](./contracts.py#L34) instead of
[`VideoSourceSpec`](./contracts.py#L23).

```python
from pathlib import Path

from prml_vslam.datasets.interfaces import DatasetId
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import DatasetSourceSpec, RunRequest, TrackingConfig

request = RunRequest(
    experiment_name="advio-office-vista",
    output_dir=Path("artifacts"),
    source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id="advio-15"),
    tracking=TrackingConfig(method=MethodId.VISTA),
)
```

## Defining A Streaming Pipeline

A streaming plan uses [`PipelineMode.STREAMING`](./contracts.py#L20) together
with [`LiveSourceSpec`](./contracts.py#L45).

```python
from pathlib import Path

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import LiveSourceSpec, PipelineMode, RunRequest, TrackingConfig

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

[`prml_vslam.main.plan_run`](../main.py#L60) constructs a
[`RunRequest`](./contracts.py#L99) from CLI arguments and prints the resulting
[`RunPlan`](./contracts.py#L166). This is the current offline planning
entrypoint.

### Streamlit Monitoring Demo

The `Pipeline` page demonstrates the same contracts in an executable but
bounded way:

1. build a `RunRequest`
2. build a `RunPlan`
3. materialize an ADVIO-backed [`SequenceManifest`](./contracts.py#L194)
   through
   [`AdvioDatasetService.build_sequence_manifest(...)`](../datasets/advio_service.py#L68)
4. open an ADVIO replay stream through
   [`AdvioDatasetService.open_preview_stream(...)`](../datasets/advio_service.py#L71)
5. run the repository-local
   [`MockTrackingRuntime`](../methods/mock_tracking.py#L33)
6. display frames, trajectory, stage manifests, artifacts, and summary

This demo supports:

- `offline` as one replay pass
- `streaming` as looped replay with the same incremental tracking interface

## How To Add A Stage

When adding a stage, change the typed contracts first and the runner wiring
second.

1. Decide whether the new stage is a major artifact boundary.
   - If yes, define or extend a typed artifact bundle in
     [`contracts.py`](./contracts.py).
2. Add or extend the enabling config in `RunRequest`.
   - Optional stages should be config-gated, not implied by side effects.
3. Add a new [`RunPlanStageId`](./contracts.py#L140) value in
   [`contracts.py`](./contracts.py).
4. Add canonical output path ownership in
   [`RunArtifactPaths`](../utils/path_config.py#L20).
   - The path layout belongs to
     [`PathConfig.plan_run_paths(...)`](../utils/path_config.py#L185), not to
     the app or backend.
5. Insert the stage into
   [`RunPlannerService._build_stages(...)`](./services.py#L55).
   - Give it a stable title, summary, and explicit outputs.
6. Define the execution protocol in [`interfaces.py`](./interfaces.py) if the
   stage introduces a new reusable execution seam.
7. Wire the executor surface.
   - For the current demo this means
     [`PipelineDemoRuntimeController`](../app/pipeline_runtime.py#L106).
   - For the target architecture this means a reusable offline or streaming
     runner under `prml_vslam.pipeline`.
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
- [`interfaces.py`](./interfaces.py)
- [`services.py`](./services.py)
- [`workspace.py`](./workspace.py)
- [`REQUIREMENTS.md`](./REQUIREMENTS.md)
