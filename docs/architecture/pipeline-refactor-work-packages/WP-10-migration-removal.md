# WP-10 Migration Removal

Status: Draft

Owner: Unassigned

Dependencies:
- WP-00A Baseline Acceptance
- WP-03A Telemetry Status
- WP-01 through WP-09D complete

Owned paths:
- migration wrappers and obsolete DTO/event/alias files named by prior work packages
- stale docs updated by the removal
- final cleanup tests under `tests/`

Read-only context paths:
- all prior work-package files
- `docs/architecture/pipeline-stage-present-state-audit.md`
- `docs/architecture/pipeline-stage-refactor-target.md`
- `docs/architecture/pipeline-stage-protocols-and-dtos.md`
- `docs/architecture/pipeline-dto-migration-ledger.md`

Target architecture sections:
- `DTO Simplification Targets`
- `Migration Contacts`
- `Future Implementation Inventory`


Goal:
- Delete migration-only objects after every consumer has moved to the target contracts and compatibility tests pass.
- This package is the final stale-symbol sweep after the no-backward-compat
  cutover packages have removed old config, runtime, event, handle, and
  snapshot consumers.

Out of scope:
- New target features.
- Unplanned public API changes.
- Reintroducing compatibility shims for old configs, old stage keys, old
  snapshots, or old telemetry events.

Implementation notes:
- Use [Pipeline DTO Migration Ledger](../pipeline-dto-migration-ledger.md) as
  the authoritative deletion checklist.
- Each deletion must name the replacement symbol/path.
- Delete old handles only after `TransientPayloadRef` and resolver APIs cover every current consumer.
- Delete telemetry `RunEvent` variants only after live update routing and snapshot/app consumers migrate.
- Delete stage-key aliases only after persisted/public target naming has
  replaced all production callers. Old run inspection compatibility is not a
  blocker after `WP-09A Target Config Launch Cutover` explicitly retires it.

Termination criteria:
- Stale-symbol greps are clean for retired names.
- Full CI passes.
- App, CLI, offline, and mocked streaming smoke paths pass.
- Docs no longer point implementers at deleted migration objects except in historical notes.
- `WP-09A` through `WP-09D` completion notes list the symbols they removed and
  any intentionally retained non-migration target contracts.

Required checks:
- `make ci`
- baseline acceptance matrix from `WP-00A`
- stale-symbol grep list from prior work packages
- app/CLI smoke tests
- pipeline offline and mocked streaming tests
- `git diff --check`

Known risks:
- Premature deletion is the easiest way to break old run inspection, app rendering, or streaming finalize behavior.
- Cleanup can accidentally broaden scope into refactoring unrelated package code.
