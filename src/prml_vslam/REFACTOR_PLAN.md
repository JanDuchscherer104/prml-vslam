# Refactor Plan


This is a historical planning scratchpad. The current implementation target is
[`docs/architecture/pipeline-stage-refactor-target.md`](../../docs/architecture/pipeline-stage-refactor-target.md).

Current resolved direction:

- Stage configs are declarative policy contracts, not factories for stage
  runtimes or Ray actors.
- `RuntimeManager` constructs stage runtimes, capability-typed
  `StageRuntimeHandle` instances, sidecars, and payload stores.
- Backend/source/reconstruction variant configs may use `FactoryConfig` when
  they construct concrete domain or source implementations.
- `LiveUpdateStageRuntime` is the optional live-update drain capability,
  orthogonal to offline and streaming execution.
- Stage-local visualization adapters, such as
  `pipeline/stages/slam/visualization.py`, translate semantic stage updates plus
  runtime-created named payload refs into neutral `VisualizationItem` values.
  Rerun sinks and `RerunLoggingPolicy` remain the only SDK callers.


---

## CODEX Plan

The old pre-UML decision register has been superseded by
[`docs/architecture/pipeline-stage-refactor-target.md`](../../docs/architecture/pipeline-stage-refactor-target.md).
Keep this file as a pointer only; do not treat the historical sketch as current
implementation guidance.
