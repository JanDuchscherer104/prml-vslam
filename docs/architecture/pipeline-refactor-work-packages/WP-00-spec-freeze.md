# WP-00 Spec Freeze

Status: Frozen

Owner: Unassigned

Dependencies: None

Owned paths:
- `docs/architecture/pipeline-refactor-target-dir-tree.md`
- `docs/architecture/pipeline-refactor-work-packages/`
- selected package `REQUIREMENTS.md` files that materially conflict with the target architecture

Read-only context paths:
- `docs/architecture/pipeline-stage-present-state-audit.md`
- `docs/architecture/pipeline-stage-refactor-target.md`


Target architecture sections:
- `Target Package Ownership`
- `Future Recommended Implementation Order`


Goal:
- Freeze the implementation scaffold and work-package boundaries before production code changes.
- Align selected REQUIREMENTS.md files with the current target model (docs/architecture/pipeline-stage-refactor-target.md) by adding scoped package guidance and links where a package-local requirement materially conflicts with the target model.
- Keep the full target directory tree canonical in `docs/architecture/pipeline-refactor-target-dir-tree.md`; do not copy the full tree into package `REQUIREMENTS.md` files.
- Point baseline acceptance details to `WP-00A Baseline Acceptance`.

Out of scope:
- Production contract implementation.
- Runtime behavior changes.
- Stage-key rename implementation.
- Deleting migration objects.

Implementation notes:
- Update only requirement files that conflict with the target refactor.
- Keep `pipeline-stage-refactor-target.md` whole and canonical.
- Keep `pipeline-refactor-target-dir-tree.md` as the only full target module and leaf-symbol tree. Package `REQUIREMENTS.md` files may include scoped target guidance and links, but must not duplicate the full tree.
- Record any unresolved implementation choice in this file before assigning code work.
- Do not duplicate baseline smoke matrices here; use `WP-00A` as the
  behavior-preservation gate.

Termination criteria:
- Target directory tree exists and names one owning file for each important symbol.
- Requirement files no longer contradict declarative stage configs, `RuntimeManager`, capability-typed proxies, pipeline-owned transient refs, or Rerun sink ownership.
- `WP-00A Baseline Acceptance` exists and documents the clean-reference worktree command plus smoke matrix.
- `WP-00B DTO Class Inventory Audit` exists and defines the full DTO/class
  ledger coverage gate before implementation packages start.

Required checks:
- `git diff --check`
- `git diff --check -- docs/architecture/pipeline-refactor-target-dir-tree.md docs/architecture/pipeline-refactor-work-packages`
- stale-term grep against target docs, allowing hits only in non-target/migration sections
- link check by inspection for the three canonical architecture docs

Known risks:
- Over-editing all requirement files can create churn without reducing ambiguity.
- Central docs are high-conflict paths for parallel agents.
- Freezing the spec too late lets implementation agents invent new abstractions.
