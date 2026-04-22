# Pipeline Stage Refactor Pruning Proposal

This note is a complexity-reduction companion to
[pipeline-stage-refactor-target.md](./pipeline-stage-refactor-target.md) and
[pipeline-stage-artifact-cleanup-policy.md](./pipeline-stage-artifact-cleanup-policy.md).
It identifies target-plan features that are not strictly necessary for the
first implementation slice and can be deferred without losing the main
simplification benefit.

The core problem to solve first is the current split across
`RuntimeStageProgram`, `stage_execution.py`, `stage_actors.py`, mutable runtime
state, and coordinator-owned observer policy. Features that do not directly
reduce that split should wait until the runtime boundary is cleaner.

## Keep In The First Slice

These are necessary because they directly simplify the current runtime path:

- `StageResult` replacing `StageCompletionPayload`
- keyed `dict[StageKey, StageResult]` replacing `RuntimeExecutionState`
- stage runtime protocols: `BaseStageRuntime`, `OfflineStageRuntime`, and
  `StreamingStageRuntime`
- stage-local runtime classes replacing free `run_*` helpers
- unified `SlamStageRuntime` reached through `StageRuntimeHandle`, with
  `SlamStageActor` as the Ray worker
- minimal hybrid-lazy `RuntimeManager`
- direct `StageRuntimeUpdate` routing for current streaming SLAM
- `SourceRuntime` wrapper around existing source behavior

## Prune Or Defer

| Feature | Recommendation | Why |
| --- | --- | --- |
| Full `RunConfig` replacement of `RunRequest` | Defer | Config migration is broad and can distract from runtime simplification. Keep adapter compatibility first. |
| Full TOML `[stages.*]` migration | Defer | Existing request shape can feed the new runtime internals initially. |
| Full source config/factory parity for every source | Defer partially | Add `SourceRuntime`, but do not rewrite all source configs immediately. |
| `evaluate.cloud` runtime | Defer | Placeholder; not needed for the current executable slice. |
| `evaluate.efficiency` runtime | Defer | Better after runtime/status model stabilizes. |
| `reconstruction` umbrella implementation | Defer implementation | Keep target vocabulary, but do not implement reference/3DGS variants in the runtime refactor unless already needed. |
| 3DGS actor/runtime | Defer | Long-term product-relevant, but high complexity and not needed to clean current stage execution. |
| Full `TransientPayloadRef` replacement everywhere | Defer partially | Add target DTO or adapter, but do not migrate every handle path in the first slice. |
| Full `StageOutputSummary` snapshot redesign | Defer | Snapshot cleanup can follow after `StageResult` works. |
| Full `StageRuntimeStatus` telemetry fields | Start minimal | Use lifecycle/progress/error and submitted/completed/failed/in-flight counters first; queue depth is reported only for owned queues or credits. |
| Full `VisualizationEnvelope` modality system | Defer partially | Support current SLAM/Rerun needs only; avoid designing every future modality now. |
| Remote Ray head / multi-machine placement tests | Defer | Keep local/single-node execution stable first. |
| Full typed resource model with memory, node labels, affinity, retries | Start minimal | CPU, GPU, and restart fields are enough for the first implementation. |
| Full artifact cleanup implementation | Defer implementation, document policy now | Needs `StageConfig` and final provenance support, but should not block the first runtime simplification slice. |
| Moving `PipelineBackend` to `pipeline/protocols.py` | Defer | Ownership cleanup, not on the critical runtime path. |
| Moving serialization helpers out of `pipeline.finalization` | Defer | Useful cleanup, unrelated to stage execution complexity. |
| Removing `io.datasets` aliases | Defer | Import cleanup, unrelated to runtime simplification. |
| Moving Rerun validation DTOs | Defer | Localized cleanup, not core pipeline runtime. |

## Lean First Refactor

The smallest useful refactor should:

1. Keep current `RunRequest` and `RunPlan` externally.
2. Introduce `StageResult` and a keyed result store.
3. Introduce runtime protocols and stage-local runtime objects.
4. Move bounded `run_*` functions behind runtime classes.
5. Merge SLAM runtime/actor surfaces behind `SlamStageRuntime`.
6. Keep current source configs and handles behind adapters.
7. Keep Rerun and snapshot behavior mostly compatible, but route new
   `StageRuntimeUpdate` directly for streaming SLAM.

This gives the biggest reduction in complexity without pulling in config
migration, reconstruction, cloud metrics, full telemetry, or remote placement.

## Acceptance Boundary

The first slice is successful when the current executable path still supports:

- offline source-to-SLAM-to-summary execution
- streaming source credits, SLAM updates, and finalization
- optional ground alignment and trajectory evaluation
- existing app/CLI launch surfaces through current request/plan contracts

It does not need to finish:

- full `[stages.*]` config migration
- future cloud/efficiency/reconstruction stages
- full snapshot schema cleanup
- full remote placement support
- complete transient payload handle migration
