# Pipeline Refactor Work Packages

This directory is the shared handoff surface for the pipeline stage refactor.
It complements the target architecture and target directory tree:

- [Target architecture](../pipeline-stage-refactor-target.md)
- [Present-state audit](../pipeline-stage-present-state-audit.md)
- [Executable protocols and DTOs](../pipeline-stage-protocols-and-dtos.md)
- [DTO migration ledger](../pipeline-dto-migration-ledger.md)
- [Target directory tree](../pipeline-refactor-target-dir-tree.md)

Each work package defines owned paths, dependencies, termination criteria, and
required checks. Parallel agents should edit only their assigned work-package
file plus the code/docs paths listed under `Owned paths`.

## Coordination Rules

- Keep cross-package status in this README index.
- Do not use one work package to edit another package's owned paths unless the
  README status is updated first.
- Treat `Read-only context paths` as inspection-only.
- Do not delete migration objects until `WP-10 Migration Removal`.
- Preserve current offline, streaming, app, CLI, artifact, and old-run
  inspection behavior until a work package explicitly replaces it.
- Every completed implementation work package must pass
  [WP-R Review Simplification Gate](./WP-R-review-simplification-gate.md)
  before dependent work packages start.
- `WP-R` may review all files changed by the just-completed package, but it may
  edit only those files or the completed package's work-package docs unless
  this README is updated first or the user explicitly approves broader scope.
- Distributed-Ray cluster attach, runtime-env, storage locality, and on-prem
  deployment design are deferred; do not create a distributed-Ray work package
  until the target architecture is reopened for that scope.

## DTO Reference Rule

- Use [Executable protocols and DTOs](../pipeline-stage-protocols-and-dtos.md)
  to understand current executable DTOs, owners, and call paths.
- Use [DTO migration ledger](../pipeline-dto-migration-ledger.md) to determine
  target owner, work-package owner, compatibility requirement, deletion gate,
  and verification for each DTO/config/message.
- A work package may not delete, move, or replace a DTO unless the ledger row
  assigns that action to the package.

## Required Architecture Context

Before starting any work package, read:

- `docs/architecture/pipeline-stage-refactor-target.md`
- `docs/architecture/pipeline-refactor-target-dir-tree.md`
- the assigned work-package file
- every path listed under `Read-only context paths` in that work package

Use `pipeline-stage-refactor-target.md` as the source of truth for architectural
intent, ownership boundaries, and target behavior. Use the assigned work-package
file as the source of truth for scope, owned paths, termination criteria, and
required checks. If a work-package file appears to conflict with the target
architecture, clarify or patch the work package before implementing production
code.

## Package Index

| ID | Work package | Status | Dependencies |
| --- | --- | --- | --- |
| WP-00 | [Spec Freeze](./WP-00-spec-freeze.md) | Frozen | none |
| WP-00A | [Baseline Acceptance](./WP-00A-baseline-acceptance.md) | Draft | WP-00 |
| WP-00B | [DTO Class Inventory Audit](./WP-00B-dto-class-inventory-audit.md) | Complete | WP-00 |
| WP-01 | [Contracts](./WP-01-contracts.md) | Draft | WP-00, WP-00A, WP-00B |
| WP-02 | [Config Planning](./WP-02-config-planning.md) | Draft | WP-00, WP-00A, WP-00B, WP-01 |
| WP-03A | [Telemetry Status](./WP-03A-telemetry-status.md) | Draft | WP-00A, WP-00B, WP-01 |
| WP-03 | [Runtime Skeleton](./WP-03-runtime-skeleton.md) | Draft | WP-00A, WP-00B, WP-01, WP-02, WP-03A |
| WP-04 | [Source Runtime](./WP-04-source-runtime.md) | Draft | WP-00A, WP-00B, WP-03 |
| WP-05 | [Bounded Runtimes](./WP-05-bounded-runtimes.md) | Draft | WP-00A, WP-00B, WP-03 |
| WP-06 | [SLAM Runtime Live Updates](./WP-06-slam-runtime-live-updates.md) | Draft | WP-00A, WP-00B, WP-03, WP-03A, WP-07 |
| WP-07 | [Visualization Rerun](./WP-07-visualization-rerun.md) | Draft | WP-00A, WP-00B, WP-01, WP-03A |
| WP-08 | [Snapshot Events Payloads](./WP-08-snapshot-events-payloads.md) | Draft | WP-00A, WP-00B, WP-03, WP-03A, WP-06, WP-07 |
| WP-09 | [App CLI Compat](./WP-09-app-cli-compat.md) | Draft | WP-00A, WP-00B, WP-02, WP-08 |
| WP-10 | [Migration Removal](./WP-10-migration-removal.md) | Draft | WP-00A, WP-00B, WP-01 through WP-09 complete, WP-03A |

## Recurring Gates

| ID | Gate | When it runs | Owner |
| --- | --- | --- | --- |
| WP-R | [Review Simplification Gate](./WP-R-review-simplification-gate.md) | After each completed implementation work package and before dependent packages start. | Assigned reviewer for the just-completed package |

## Shared Termination Bar

Every work package must finish with:

- owned-path diff reviewed
- `git diff --check` for touched files
- targeted tests/checks listed in the package
- no unrelated production behavior changes
- migration objects preserved unless the package explicitly owns their removal
- baseline acceptance impact understood through `WP-00A`
- `WP-R Review Simplification Gate` completed or explicitly waived with a
  recorded reason
