# WP-01 Contracts

Status: Draft

Owner: Unassigned

Dependencies:
- WP-00 Spec Freeze
- WP-00A Baseline Acceptance
- WP-00B DTO Class Inventory Audit

Owned paths:
- `src/prml_vslam/pipeline/stages/__init__.py`
- `src/prml_vslam/pipeline/stages/base/__init__.py`
- `src/prml_vslam/pipeline/stages/base/contracts.py`
- `src/prml_vslam/pipeline/stages/base/handles.py`
- `src/prml_vslam/pipeline/stages/base/protocols.py`
- focused contract tests under `tests/`

Read-only context paths:
- `src/prml_vslam/pipeline/contracts/`
- `src/prml_vslam/interfaces/`
- `src/prml_vslam/methods/contracts.py`
- `docs/architecture/pipeline-stage-protocols-and-dtos.md`
- `docs/architecture/pipeline-refactor-target-dir-tree.md`
- `docs/architecture/pipeline-dto-migration-ledger.md`

Target architecture sections:
- `Generic DTO And Domain Payload Architecture`
- `Canonical Stage Result`
- `Runtime Updates, Events, And Visualization Items`
- `Transient Payload Handles`


Goal:
- Add generic target contracts and protocols without changing runtime behavior.

Out of scope:
- `RunConfig` loading.
- `RuntimeManager`, `StageRuntimeProxy`, or stage runtime implementation.
- Snapshot/event cleanup.
- Rerun sink changes.

Implementation notes:
- Define `StageResult`, `StageRuntimeStatus`, `StageRuntimeUpdate`, `VisualizationItem`, `VisualizationIntent`, and `TransientPayloadRef`.
- Define `BaseStageRuntime`, `OfflineStageRuntime`, `LiveUpdateStageRuntime`, and `StreamingStageRuntime`.
- Keep `TransientPayloadRef` out of pure domain DTOs.
- Keep `VisualizationItem` sink-facing and SDK-free.
- Stage config and execution-policy contracts belong to WP-02 unless the
  work-package README changes ownership first. This includes `StageConfig`,
  `StageExecutionConfig`, `ResourceSpec`, `PlacementConstraint`,
  `StageTelemetryConfig`, and `StageCleanupPolicy`.

DTO migration scope:
- Use [Pipeline Stage Protocols And DTOs](../pipeline-stage-protocols-and-dtos.md)
  for current executable DTO behavior and
  [Pipeline DTO Migration Ledger](../pipeline-dto-migration-ledger.md) for
  target ownership/deletion gates.
- Own target additions only: `StageResult`, `StageRuntimeStatus`,
  `StageRuntimeUpdate`, `VisualizationItem`, `VisualizationIntent`,
  `TransientPayloadRef`, and runtime protocols.
- Do not delete current DTOs in this package; deletion gates are defined in
  [Pipeline DTO Migration Ledger](../pipeline-dto-migration-ledger.md).

Termination criteria:
- Contract tests cover DTO construction, serialization/projection expectations, and protocol typing where practical.
- Existing pipeline tests still pass for untouched behavior.
- No Rerun SDK imports appear in DTOs, protocols, methods, or stage runtimes.
- No pure domain DTO imports `TransientPayloadRef`.

Required checks:
- `uv run pytest tests/test_pipeline.py -k "contract or runtime or snapshot"`, adjusted to the tests added in this package
- grep/import-boundary check for `TransientPayloadRef` in pure domain DTO modules
- grep/import-boundary check for `rerun` outside sink/policy/visualization test modules
- `git diff --check`

Known risks:
- Creating generic `StageInput` / `StageOutput` base classes would reintroduce a public semantic wrapper layer.
- Embedding transient refs in `SlamUpdate` would recreate the current layering smell.
