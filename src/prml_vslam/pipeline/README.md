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
- `contracts/runtime.py`
  - `RunState`, `RunSnapshot`, `StreamingRunSnapshot`
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

`ingest -> slam -> summary` is the only executable stage slice today.

- offline
  - resolve or materialize a `SequenceManifest`
  - canonicalize `rgb_dir`, timestamps, calibration, and rotation sidecars
  - run one offline backend over the materialized manifest
  - persist stage manifests and the final run summary
- streaming
  - prepare a manifest
  - open a packet stream
  - start a streaming session and consume `FramePacket` updates
  - persist stage manifests and the final run summary

Reference and evaluation stages remain plannable but are not yet executable in
the current runner slice.

## Boundary Rules

- `SequenceManifest` is the normalized offline boundary.
- `SlamArtifacts` are the normalized SLAM outputs.
- `RunSummary` and `StageManifest` are the authoritative provenance records.
- Offline ingest stays source-faithful; method-specific workspace shaping stays
  inside method adapters.
- `prml_vslam.pipeline` is the curated public import surface. The internal
  `pipeline/contracts/` package is an implementation namespace, not a public
  convenience API.
