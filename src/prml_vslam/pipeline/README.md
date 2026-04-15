# Pipeline

This package owns the typed run contracts, normalized manifest boundary,
artifact/provenance contracts, and the two execution strategies used by the
repository pipeline.

## Current Structure

- `contracts/request.py`
  - `PipelineMode`, source specs, `SlamStageConfig`, `RunRequest`
- `contracts/plan.py`
  - `RunPlanStageId`, `RunPlanStage`, `RunPlan`
- `contracts/sequence.py`
  - `SequenceManifest`
- `contracts/artifacts.py`
  - `ArtifactRef`, `SlamArtifacts`
- `contracts/provenance.py`
  - `StageExecutionStatus`, `StageManifest`, `RunSummary`
- `state.py`
  - `RunState`, `RunSnapshot`, `StreamingRunSnapshot`
- `benchmark`
  - prepared benchmark inputs such as available reference trajectories
- `run_service.py`
  - public façade used by CLI and app surfaces
- `offline.py`
  - offline runner over materialized sequence manifests
- `streaming.py`
  - incremental runner over packet streams
- `ingest.py`
  - canonical offline ingest/materialization helpers
- `finalization.py`
  - shared stage-manifest and run-summary persistence

## Execution Model

`ingest -> slam -> [trajectory_evaluation] -> summary` is the executable
stage slice today. Trajectory evaluation runs only when the request enables it
and the source prepares the requested benchmark trajectory input.

- offline
  - resolve or materialize a `SequenceManifest`
  - canonicalize `rgb_dir`, timestamps, calibration, and rotation sidecars
  - run one offline backend over the materialized manifest
  - optionally compute trajectory metrics from prepared benchmark inputs
  - persist stage manifests and the final run summary
- streaming
  - prepare a manifest
  - open a packet stream
  - start a streaming session and consume `FramePacket` updates
  - optionally compute trajectory metrics from prepared benchmark inputs
  - persist stage manifests and the final run summary

Reference reconstruction, cloud evaluation, and efficiency evaluation remain
plannable but are not yet executable in the current runner slice.

## TOML-First Run Planning

Persist durable pipeline requests as `RunRequest` TOML files under
`.configs/pipelines/`. The Streamlit Pipeline page discovers these files for the
Pipeline Config selector, and the CLI can plan or run them directly.

```toml
experiment_name = "vista-full-tuning"
mode = "streaming"
output_dir = ".artifacts"

[source]
dataset_id = "advio"
sequence_id = "advio-15"

[slam]
method = "vista"

    [slam.outputs]
    emit_dense_points = true
    emit_sparse_points = true

    [slam.backend]
    max_frames = 1000

        [slam.backend.slam]
        flow_thres = 5.0
        max_view_num = 400

[benchmark.trajectory]
enabled = false

[visualization]
connect_live_viewer = true
export_viewer_rrd = true
```

The TOML shape mirrors the nested `RunRequest` model: top-level fields configure
the run itself, while `[source]`, `[slam]`, `[benchmark]`, and `[visualization]`
map onto nested config objects. Method-private controls live under
`[slam.backend]`, and output policy lives under `[slam.outputs]`.

Use the committed examples for runnable starting points:

```bash
uv run prml-vslam plan-run-config .configs/pipelines/advio-15-offline-vista.toml
uv run prml-vslam run-config .configs/pipelines/advio-15-offline-vista.toml
```

`plan-run-config` loads a persisted request and prints the canonical plan.
`run-config` executes offline requests. `pipeline-demo` remains the bounded ADVIO
streaming demo entry point.

A fuller ViSTA tuning example is available at
[`.configs/pipelines/vista-full.toml`](../../../.configs/pipelines/vista-full.toml).

## Boundary Rules

- `SequenceManifest` is the normalized offline ingest boundary.
- Benchmark-owned prepared inputs such as reference trajectories are kept
  separate from the sequence manifest.
- `SlamArtifacts` are the normalized SLAM outputs.
- `RunSummary` and `StageManifest` are the authoritative provenance records.
- Offline ingest stays source-faithful; method-specific workspace shaping stays
  inside method adapters.
- `prml_vslam.pipeline` is the curated public import surface. The internal
  `pipeline/contracts/` package is an implementation namespace, not a public
  convenience API.
