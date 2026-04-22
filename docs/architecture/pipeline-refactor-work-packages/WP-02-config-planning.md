# WP-02 Config Planning

Status: Draft

Owner: Unassigned

Dependencies:
- WP-00 Spec Freeze
- WP-00A Baseline Acceptance
- WP-00B DTO Class Inventory Audit
- WP-01 Contracts

Owned paths:
- `src/prml_vslam/pipeline/config.py`
- `src/prml_vslam/pipeline/stages/base/config.py`
- planning/config tests under `tests/`

Read-only context paths:
- `src/prml_vslam/pipeline/contracts/request.py`
- `src/prml_vslam/pipeline/contracts/plan.py`
- `src/prml_vslam/pipeline/contracts/stages.py`
- `src/prml_vslam/pipeline/stage_registry.py`
- `src/prml_vslam/pipeline/placement.py`
- stage-owned config modules under `src/prml_vslam/pipeline/stages/*/config.py`
- `.configs/pipelines/`
- `src/prml_vslam/methods/configs.py`
- `src/prml_vslam/utils/base_config.py`
- `docs/architecture/pipeline-stage-protocols-and-dtos.md`
- `docs/architecture/pipeline-refactor-target-dir-tree.md`
- `docs/architecture/pipeline-dto-migration-ledger.md`
- `docs/architecture/pipeline-stage-artifact-cleanup-policy.md`

Target architecture sections:
- `RunConfig Stage Bundle And Plan Compilation`
- `Target Config Shape`
- `Config Hierarchy`
- `Backend And Source Muxing`


Goal:
- Introduce target `RunConfig`, `StageBundle`, stage config sections, and stage-key/config-section mapping while preserving current request/config compatibility.
- Provide generic config scaffolding and compatibility adapters only. Full
  executable target `[stages.*]` parsing is completed by
  [WP-02B Target Config Completion](./WP-02B-target-config-completion.md).

Out of scope:
- Runtime construction.
- RuntimeManager preflight implementation.
- Stage runtime factory implementation or Ray allocation.
- Stage body migration.
- Public stage-key rename enforcement.
- Removing `RunRequest`.
- Mutating committed `.configs/pipelines/*.toml` files into the target shape.

Implementation notes:
- Stage configs are declarative policy contracts only.
- This package intentionally does not implement stage-specific config sections
  such as `SourceStageConfig`, `SlamStageConfig`, or
  `ReconstructionStageConfig`. The generic `StageBundle` accepts only shared
  `StageConfig` fields until WP-02B integrates those stage-specific modules.
- `RunConfig.compile_plan()` may delegate through `RunRequest` in this package
  because current source/backend/output policy still lives on legacy request
  fields. Direct `RunConfig -> RunPlan` compilation belongs to WP-02B after
  stage-specific config modules can describe source/backend/output policy.
- Stage configs must not inherit `FactoryConfig`, implement `setup_target()`,
  construct runtimes, open sources, allocate Ray, or create sink sidecars.
- WP-02 owns shared planning/config scaffolding and stage-key/config-section
  mapping. Individual stage packages own their stage-specific `config.py`
  implementations.
- WP-02 owns the base stage config and execution-policy contracts:
  `StageConfig`, `StageExecutionConfig`, `ResourceSpec`,
  `PlacementConstraint`, `StageTelemetryConfig`, and `StageCleanupPolicy`.
- `StageConfig.cleanup` is config/provenance policy only in this package;
  runtime cleanup behavior lands in later runtime packages.
- RuntimeManager preflight belongs to WP-03. WP-02 may only provide
  planning/launch-time unavailable-stage diagnostics needed for fail-fast
  checks before runtime allocation.
- Backend/source/reconstruction variant configs may use `FactoryConfig.setup_target()` for domain/source implementation targets.
- Add alias/projection policy for current-to-target stage key differences while
  keeping current executable keys and old-run inspection working in the first
  slice:
  - `ingest -> source`
  - `trajectory.evaluate -> evaluate.trajectory`
  - `reference.reconstruct -> reconstruction`
  - `cloud.evaluate -> evaluate.cloud`
  - `efficiency.evaluate -> evaluate.efficiency`
- The DTO migration ledger owns all six alias rows; keep alias deletion
  deferred to WP-10.
- Use Pydantic v2 patterns and existing `BaseConfig` / `BaseData` conventions.

DTO migration scope:
- Use [Pipeline Stage Protocols And DTOs](../pipeline-stage-protocols-and-dtos.md)
  for current request/source/stage-key behavior and
  [Pipeline DTO Migration Ledger](../pipeline-dto-migration-ledger.md) for
  target ownership/deletion gates.
- Own compatibility and target planning rows for `RunRequest`, `SourceSpec`,
  `StagePlacement`, `PlacementPolicy`, `StageDefinition`, `RayRuntimeConfig`,
  `RunRuntimeConfig`, current `SlamStageConfig`, and stage-key aliases.
- Own compatibility references to `BenchmarkConfig`,
  `TrajectoryBenchmarkConfig`, `ReferenceReconstructionConfig`,
  `BackendDescriptor`, and `BackendCapabilities` for planning only.
- Own reconstruction backend config references only as stage config fields;
  reconstruction implementation config remains reconstruction-owned.
- Do not remove `RunRequest`, current stage keys, or old config paths in this
  package; follow deletion gates in
  [Pipeline DTO Migration Ledger](../pipeline-dto-migration-ledger.md).

Termination criteria:
- Current TOML configs still load through existing launch paths.
- `plan-run-config` works for current configs.
- Target stage sections can be parsed and projected into a deterministic plan shape.
- Stage-key/config-section mapping projects target names while preserving
  current executable keys and old-run inspectability.
- Enabled unavailable stages fail during planning or launch checks before
  runtime allocation.
- Stage execution, resource, placement, telemetry, and cleanup configs
  serialize and round-trip.
- Stage configs do not expose runtime factory behavior.

Required checks:
- `uv run prml-vslam plan-run-config .configs/pipelines/vista-full.toml`
- targeted planning/config pytest tests
- tests for target `[stages.*]` TOML parsing into `RunConfig`
- tests for stage-key/config-section alias projection
- tests for enabled unavailable stages failing before runtime allocation
- tests for `StageExecutionConfig`, `ResourceSpec`, `PlacementConstraint`,
  `StageTelemetryConfig`, and `StageCleanupPolicy` serialization round-trip
- tests proving stage configs do not expose `setup_target()`
- `git diff --check`

Known risks:
- Renaming stage keys too early can break old run inspection, summaries, manifests, and app views.
- Duplicating Pydantic discriminator switches in factories can create two construction authorities.
- Letting stage configs construct runtime targets would bypass RuntimeManager
  ownership and blur config/planning with execution.
- Treating this package as full target-config completion can break WP-03,
  WP-07, or WP-09 expectations. Full target `[stages.*]` parsing and direct
  `RunConfig -> RunPlan` compilation are deferred to WP-02B.
