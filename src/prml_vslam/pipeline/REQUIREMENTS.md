# PRML VSLAM Pipeline Requirements

## Summary

This document is the source of truth for the target pipeline architecture in
`src/prml_vslam/pipeline/`.

The pipeline serves two connected modes:

- offline benchmark execution
- live streaming, capture, and preview

The architectural core is offline, artifact-first benchmark execution. Live
streaming is still a required supported mode, but it must remain a smaller
runtime surface with bounded ingress and explicit persistence boundaries.

Both modes meet at one normalized, materialized boundary:
`SequenceManifest`. Capture, import, and dataset adapters must normalize inputs
into that shared manifest before the main benchmark stages run.

## Sources of Truth

- [README.md](../../../README.md)
- [Questions.md](../../../docs/Questions.md)
- [pipeline/README.md](README.md)
- [contracts.py](contracts.py)
- [services.py](services.py)
- [app/REQUIREMENTS.md](../app/REQUIREMENTS.md)
- [REQUIREMENTS.md](../REQUIREMENTS.md)

The app requirements documents are downstream consumer guidance only. They do
not own pipeline semantics or architecture decisions.

## Current-State Findings

- The current `pipeline/` package is only a lightweight typed planning surface.
  It currently contains planner-oriented contracts and one planner service, not
  a full runtime architecture.
- A package-local `README.md` now documents the current contracts, usage
  patterns, and stage-extension workflow. This requirements document remains
  the source of truth for the target architecture rather than the current demo
  behavior.
- The current executable pipeline demo lives in `prml_vslam.app`, where the
  Streamlit `Pipeline` page uses ADVIO replay plus `MockTrackingRuntime` to
  exercise the shared contracts. That demo is intentionally not the final
  reusable runner API for `prml_vslam.pipeline`.
- The repo already has stable top-level seams for `app`, `io`, `methods`,
  `eval`, `pipeline`, and `utils`. The target pipeline architecture must stay
  close to that package layout.
- `methods/` already exists at top level, so pipeline-local method wrappers
  should not be introduced.
- `eval/` already exists at top level, so evaluation logic should not become
  app-owned or be duplicated under `pipeline/`.
- There is no evidence in the current repo for Burr, Dagster, or any other
  workflow-framework dependency. The visible dependency set is standard Python
  tooling plus method/evaluation/capture integrations.

## Architecture Requirements

- The pipeline must be described as a linear, config-gated benchmark pipeline,
  not a general graph engine.
- Stage selection must be driven by typed config and ordered plans, not by a
  stateful graph core.
- The architecture must explicitly reject:
  - Dagster
  - Burr
  - a generic stateful graph core
  - an async-first core
  - a generic untyped envelope carrying `dict[str, Any]`
- The architecture must explicitly require:
  - typed Pydantic contracts at stage boundaries
  - deterministic artifact workspaces
  - cache reuse only at artifact boundaries
  - one bounded queue for live ingress, and nowhere else
  - a synchronous offline runner
  - a small queue-backed streaming runner
- The pipeline must optimize for inspectable, reproducible artifacts rather
  than generalized workflow flexibility.
- The hot frame path may stay in memory, but every major artifact boundary must
  be materialized explicitly and deterministically.

## Package Ownership

- `pipeline/` owns orchestration only.
- `io/` owns capture, import, readers, live ingress adapters, and input
  normalization helpers.
- `methods/` owns backend wrappers and method-specific integrations.
- `eval/` owns trajectory, cloud, and efficiency evaluation logic.
- `app/` owns Streamlit UI, page state, and rendering only.
- `utils/` owns shared infrastructure such as config patterns, logging, and
  common helpers.
- `datasets/` already exists and owns ADVIO plus future custom-dataset
  adapters. Those adapters must normalize inputs into the shared pipeline
  boundary instead of letting dataset-specific types leak into orchestration.

## Target Public Contracts

The target pipeline architecture should converge on the following public
contracts. These names describe the required shape and responsibilities; future
implementations may add supporting types, but should not weaken these boundary
contracts.

- `RunRequest`
  - config-defined entry contract for pipeline execution
  - includes mode, source specification, tracking config, optional dense config,
    optional reference config, and evaluation config
- `RunPlan`
  - ordered stage plan derived from `RunRequest`
  - contains `run_id`, `artifact_root`, selected mode, and ordered stage list
- `SequenceManifest`
  - normalized artifact boundary between capture/import and benchmark execution
  - references the materialized input sequence and related metadata
- Artifact bundles
  - separate typed bundles for tracking, dense mapping, reference
    reconstruction, and evaluation outputs
  - large data should flow by artifact paths, not giant serialized payloads
- `StageManifest`
  - per-stage cache and provenance record
  - records stage identity, config fingerprint, input fingerprint, output
    locations, and execution status
- `RunSummary`
  - final persisted outcome for one run, including stage status and artifact
    root
- `FramePacket`
  - the only lightweight shared runtime unit between live ingress and streaming
    processing
  - suitable for both offline replay and live capture feeds
- Runtime event DTOs
  - `RunEvent`, `PreviewEvent`, `StageEvent`, and `ErrorEvent`
  - intended for app and CLI observability only, not for moving stage payloads
    through the pipeline

Large artifacts must be passed across major stages by path-backed typed
contracts. `FramePacket` is the only shared in-memory runtime unit that should
cross the live ingress boundary.

## Target Runtime Surfaces

The target runtime should expose exactly two runners:

- `OfflineRunner`
- `StreamingRunner`

The target runtime should expose only a small set of boundary services:

- planner or builder service
- workspace service
- cache service
- run service
- session service

One service per stage is explicitly forbidden. Stages are execution units, not
service boundaries.

The intended responsibilities are:

- planner or builder service
  - turns `RunRequest` into `RunPlan`
- workspace service
  - owns deterministic path layout and workspace manifests
- cache service
  - owns stage fingerprints and artifact-boundary cache hits
- run service
  - single façade consumed by CLI and app
- session service
  - owns active streaming sessions and their bounded live state

## Materialization and Queueing Rules

Materialize only after major artifact boundaries:

- ingest or normalize
- tracking
- dense mapping
- reference reconstruction
- evaluation outputs
- summary

The hot path stays in memory. The pipeline must not materialize every micro-step
or every frame-level computation.

Only the live ingress path gets a bounded queue. Offline mode must not use
queue-based inter-stage plumbing.

No inter-stage queues are allowed between tracking, export, evaluation, or
summary stages. Queueing is only justified between live capture ingress and the
streaming worker.

## App and CLI Integration

- The app and CLI should consume a `RunService` façade.
- The app must not instantiate stages or define orchestration semantics.
- The CLI must not embed pipeline topology rules beyond constructing typed
  requests and invoking pipeline services.
- Streamlit session state should hold only lightweight UI and session values.
  Long-lived streaming sessions belong to pipeline session services, not to raw
  `st.session_state`.
- Runtime event DTOs should support app polling and CLI status reporting without
  leaking pipeline internals into UI state models.

## Acceptance Scenarios

### Offline Benchmark Run

- A user provides a video-backed source and a typed `RunRequest`.
- The pipeline plans and executes an ordered offline run.
- The run persists normalized inputs, stage artifacts, stage manifests, and a
  final summary.

### Dataset-Backed Run

- A dataset adapter provides ADVIO or custom-dataset inputs.
- Those inputs are normalized into the same `SequenceManifest` used by other
  sources.
- Downstream tracking, mapping, and evaluation stages consume the same manifest
  contract regardless of origin.

### Live Streaming Session

- A live source feeds `FramePacket` objects through one bounded ingress queue.
- The streaming runtime emits preview and stage events for UI or CLI consumers.
- The session can persist captured data and hand off to the offline-core
  pipeline through a materialized sequence boundary.

### Cache Reuse

- Re-running a compatible stage with the same relevant inputs and config can
  reuse artifact-boundary outputs from cache.
- Cache decisions are driven by typed stage manifests and fingerprints, not by
  ad hoc file existence checks.

### App Polling

- The app polls runtime events and status through pipeline services.
- Pipeline orchestration logic does not leak into app-local UI state models.

## Explicit Non-Goals

- No workflow framework
- No generic envelope payloads
- No inter-stage queues beyond live ingress
- No async core
- No browser or UI concerns inside `pipeline/`
- No duplication of `methods/` or `eval/` under `pipeline/`

## Important Interface Decisions To Lock In

- `RunRequest` is the config-defined entry contract, not a loose planner-only
  input.
- `SequenceManifest` is the normalization boundary between capture or import and
  benchmark execution.
- `FramePacket` is the shared runtime unit for offline replay and live ingress.
- The pipeline must separate offline tracker capability from streaming tracker
  capability.
- Downstream dense, reference, and evaluation stages should consume typed
  artifact bundles, not live frame packets.
- Runtime events are for app and CLI observability only, not for moving stage
  payloads through the system.

## Validation

The requirements document is valid only if it satisfies all of the following:

- It clearly separates current implementation findings from target architecture
  requirements.
- It does not claim that future modules like `messages.py`, `runners.py`, or
  `cache.py` already exist.
- It stays consistent with the current top-level package layout in this repo.
- It reconciles the repo's artifact-first benchmark focus with the confirmed
  requirement that live streaming is still a supported pipeline mode.

## Assumptions and Defaults

- Offline benchmark execution is the architectural core.
- Live streaming is still a required supported mode, but it should remain a
  smaller bounded runtime surface.
- This requirements document is normative for future refactors, not just a
  description of the current minimal planner implementation.
- Future package and module additions may be specified here as target
  architecture, but they must always be labeled as target additions rather than
  current facts.
