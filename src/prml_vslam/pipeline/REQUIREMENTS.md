# PRML VSLAM Pipeline Requirements

## Purpose

This file is the concise source of truth for the `prml_vslam.pipeline` package.

## Current State

- `prml_vslam.pipeline` now owns run/artifact/provenance contracts through an
  internal `contracts/` package rather than one monolithic `contracts.py`.
- The package exposes one authoritative runtime path through
  `PipelineBackend`, `RayPipelineBackend`, and `RunService`.
- The current executable slice uses target persisted stage keys: `source`,
  `slam`, optional `gravity.align`, optional `evaluate.trajectory`, optional
  `reconstruction`, diagnostic `evaluate.cloud`, and `summary`.
- Runtime execution flows through stage-owned bindings plus lazy runtime
  construction. Ray is a backend/deployment option, not the semantic owner of
  stage behavior.

## Responsibilities

- own run configs, plans, events, projected snapshots, manifests, artifacts,
  and summary persistence
- own pipeline lifecycle, generic stage planning, runtime envelopes, status,
  artifact references, transient payload references, and source-normalization
  boundaries
- remain separate from benchmark reference identifiers, app state, and
  method-wrapper internals

## Non-Negotiable Requirements

- `SequenceManifest` remains the normalized offline boundary.
- Large outputs stay materialized as durable artifacts.
- Offline source preparation must stay source-faithful and method-agnostic.
- `prml_vslam.pipeline` is the curated public API; `pipeline/contracts/` is not
  a compatibility import hub.
- The package must not re-export method protocols through the pipeline root.
- The target executable slice must remain linear and deterministic:
  `source`, `slam`, optional `gravity.align`, optional
  `evaluate.trajectory`, optional `reconstruction`, and `summary`.
- `RunSnapshot` must project durable lifecycle/provenance state from `RunEvent`
  and live status, previews, and transient refs from `StageRuntimeUpdate`;
  it must not become a second mutable runtime truth.
- Stage manifests and run summaries must derive status from terminal
  `StageOutcome` values. Live and display status must come from
  `StageRuntimeStatus`; do not introduce or preserve a second status enum as
  canonical truth.
- Ground alignment may run only after `slam`, in offline execution and
  streaming finalize; it must never widen the streaming hot path.
- `summary` must be projection-only; it must not compute trajectory or cloud
  metrics.
- Trajectory evaluation may run only from prepared benchmark inputs and
  normalized SLAM artifacts. `evaluate.cloud` is a diagnostic binding with no
  runtime yet; performance telemetry metrics are not part of the current public
  surface.

## Pipeline Stage Refactor Requirements

- `RunConfig` is the target persisted declarative root. It owns the fixed stage
  bundle and compiles to `RunPlan`; production launch code must not depend on
  legacy request DTOs or stage-key alias maps.
- Stage configs are declarative policy contracts. They validate enablement,
  planning metadata, execution resources, telemetry, cleanup, and
  failure-provenance policy; they do not construct runtimes, proxies, Ray
  actors, sink sidecars, or payload stores.
- `RuntimeManager` is the only construction authority for stage runtimes,
  capability-typed `StageRuntimeHandle` instances, payload stores, sink sidecars,
  and placement-specific runtime wrappers.
- Runtime capability and deployment stay separate. Stage runners and the
  coordinator consume protocol-capable proxies, while Ray refs, task refs,
  mailboxes, and `.remote()` calls stay inside runtime/proxy plumbing.
- Pipeline-owned runtime DTOs stay generic: terminal `StageResult`, live
  `StageRuntimeUpdate`, queryable `StageRuntimeStatus`, artifact refs, and
  transient payload refs. Semantic payload DTOs remain with their domain owner.
- `RunSnapshot` remains a transport-safe projection derived from durable events
  plus live runtime updates/status; it must not become mutable runtime truth.
- Target public stage vocabulary is exactly `source`, `slam`,
  `gravity.align`, `evaluate.trajectory`, `reconstruction`, `evaluate.cloud`,
  and `summary`.
- Rerun SDK calls belong only in sinks/policy/helper modules. Stage runtimes,
  DTOs, proxies, and visualization adapters may expose neutral visualization
  items but must not call the Rerun SDK.
- The full target module and leaf-symbol tree is canonical in
  [Pipeline Refactor Target Directory Tree](../../../docs/architecture/pipeline-refactor-target-dir-tree.md);
  this file records only pipeline-local requirements.

## Validation

- planning remains deterministic
- offline runs no longer require injected packet streams
- streaming runs still surface truthful packet/session telemetry without
  persisting raw arrays in public contracts
- stage manifests and run summaries remain explicit and durable
- target stage keys are used without alias maps
