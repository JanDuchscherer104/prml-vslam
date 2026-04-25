# PRML VSLAM Pipeline Guide

This package owns the planning, runtime orchestration, event, snapshot,
artifact, and provenance surfaces for repository pipeline runs. Shared source
protocols live in [`prml_vslam.protocols.source`](../protocols/source.py) and
[`prml_vslam.sources.replay`](../protocols/runtime.py). SLAM backend and
session protocols live in [`prml_vslam.methods.protocols`](../methods/protocols.py).
Package constraints live in [REQUIREMENTS.md](./REQUIREMENTS.md).

The pipeline is a linear benchmark runtime, not a generic workflow engine. The
current executable order is:

```text
source -> slam -> [gravity.align] -> [evaluate.trajectory] -> [reconstruction] -> [evaluate.cloud] -> summary
```

`evaluate.cloud` is a diagnostic planning binding without a runtime. Efficiency
evaluation is intentionally out of the current public pipeline surface.

## Current Entry Points

- [`RunConfig`](./config.py) is the target persisted root for TOML launch,
  planning, and stage-section configuration.
- [`RunPlan`](./contracts/plan.py) is the side-effect-free ordered plan.
- [`RunService`](./run_service.py) is the app/CLI facade over the active backend.
- [`RayPipelineBackend`](./backend_ray.py) owns Ray lifecycle and coordinator
  attachment.
- [`RunCoordinatorActor`](./ray_runtime/coordinator.py) owns one run's event
  log, live snapshot, stage sequencing, payload cache, sinks, and streaming
  credit loop.

Launch code accepts `RunConfig` and target stage sections only.

## Runtime Model

Runtime execution is driven by target runtime objects, not by a separate
function-pointer stage program:

- [`RuntimeManager`](./runtime_manager.py) preflights available stage runtimes
  and constructs [`StageRuntimeHandle`](./stages/base/proxy.py) instances lazily.
- [`StageRunner`](./runner.py) invokes bounded and streaming runtime protocol
  methods and stores [`StageResult`](./stages/base/contracts.py) values in
  `StageResultStore`.
- Stage-local runtime adapters live under [`stages/`](./stages/):
  source, SLAM, ground alignment, trajectory evaluation, reconstruction, and
  summary each own their runtime input shape and stage result production.
- [`PacketSourceActor`](./ray_runtime/stage_actors.py) is the remaining Ray
  sidecar for credit-gated streaming source reads. SLAM execution itself is
  handled by `SlamStageRuntime` through the runtime proxy path.

The legacy runtime-program layer has been removed. Stage bodies should not be
added as free `run_*` helpers or as new central phase-router entries.

## Event, Snapshot, And Payload State

The coordinator records durable run lifecycle and stage lifecycle events, then
projects a live [`RunSnapshot`](./contracts/runtime.py) for app and CLI reads.
Target runtime telemetry flows through
[`StageRuntimeUpdate`](./stages/base/contracts.py), and live bulk payloads should
use [`TransientPayloadRef`](./stages/base/handles.py).

Live telemetry and previews stay in `StageRuntimeUpdate`; durable events remain
limited to lifecycle and provenance.

## Artifact Ownership

Durable run outputs are artifacts, manifests, and summaries:

- source preparation writes the normalized sequence manifest and benchmark
  inputs under the run artifact root;
- SLAM writes normalized trajectory/point-cloud/viewer artifacts;
- derived stages write their own domain artifacts;
- summary writes `run_summary.json`, `stage_manifests.json`, and durable event
  logs.

Downstream app or CLI code should inspect artifacts through explicit artifact
inspection helpers instead of treating transient live payloads as durable
scientific outputs.

## Extension Rules

- Add new executable stage behavior as a stage-local runtime under
  `pipeline/stages/<stage>/`.
- Keep domain computation in the domain package; pipeline runtimes adapt that
  computation into `StageResult`, `StageRuntimeStatus`, and
  `StageRuntimeUpdate`.
- Keep Rerun SDK calls inside sink/policy modules, not in core DTOs or stage
  result models.
- Keep launch/config additions in `RunConfig` and stage-owned config modules.
- Update focused runtime tests and architecture docs when changing a stage
  boundary.
