# WP-02 Config Planning

Status: Draft

Owner: Unassigned

Dependencies:
- WP-00 Spec Freeze
- WP-00A Baseline Acceptance
- WP-01 Contracts

Owned paths:
- `src/prml_vslam/pipeline/config.py`
- planning/config tests under `tests/`

Read-only context paths:
- `src/prml_vslam/pipeline/contracts/request.py`
- `src/prml_vslam/pipeline/stage_registry.py`
- stage-owned config modules under `src/prml_vslam/pipeline/stages/*/config.py`
- `.configs/pipelines/`
- `src/prml_vslam/methods/configs.py`
- `src/prml_vslam/utils/base_config.py`
- `docs/architecture/pipeline-stage-protocols-and-dtos.md`
- `docs/architecture/pipeline-dto-migration-ledger.md`

Target architecture sections:
- `RunConfig Stage Bundle And Plan Compilation`
- `Target Config Shape`
- `Config Hierarchy`
- `Backend And Source Muxing`


Goal:
- Introduce target `RunConfig`, `StageBundle`, stage config sections, and stage-key/config-section mapping while preserving current request/config compatibility.

Out of scope:
- Runtime construction.
- Stage body migration.
- Public stage-key rename enforcement.
- Removing `RunRequest`.

Implementation notes:
- Stage configs are declarative policy contracts only.
- WP-02 owns shared planning/config scaffolding and stage-key/config-section
  mapping. Individual stage packages own their stage-specific `config.py`
  implementations.
- Backend/source/reconstruction variant configs may use `FactoryConfig.setup_target()` for domain/source implementation targets.
- Add alias/projection policy for `ingest -> source`, `ground.align -> align.ground`, and `reference.reconstruct -> reconstruction`; keep current executable keys working in the first slice.
- Use Pydantic v2 patterns and existing `BaseConfig` / `BaseData` conventions.

DTO migration scope:
- Use [Pipeline Stage Protocols And DTOs](../pipeline-stage-protocols-and-dtos.md)
  for current request/source/stage-key behavior and
  [Pipeline DTO Migration Ledger](../pipeline-dto-migration-ledger.md) for
  target ownership/deletion gates.
- Own compatibility and target planning rows for `RunRequest`, `SourceSpec`,
  `StagePlacement`, `PlacementPolicy`, `StageDefinition`, and stage-key aliases
  for `ingest -> source`, `ground.align -> align.ground`, and
  `reference.reconstruct -> reconstruction`.
- Do not remove `RunRequest`, current stage keys, or old config paths in this
  package; follow deletion gates in
  [Pipeline DTO Migration Ledger](../pipeline-dto-migration-ledger.md).

Termination criteria:
- Current TOML configs still load through existing launch paths.
- `plan-run-config` works for current configs.
- Target stage sections can be parsed and projected into a deterministic plan shape.
- Enabled unavailable stages fail during preflight/planning before work starts.

Required checks:
- `uv run prml-vslam plan-run-config .configs/pipelines/vista-full.toml`
- targeted planning/config pytest tests
- `git diff --check`

Known risks:
- Renaming stage keys too early can break old run inspection, summaries, manifests, and app views.
- Duplicating Pydantic discriminator switches in factories can create two construction authorities.
