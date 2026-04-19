# Prompt Corpus Distillation

Derived from `codex-user-messages-prml-vslam.jsonl`:

- scope: main repo plus matching `prml-vslam.worktrees/*` sessions
- corpus: 77 user messages across 20 sessions
- date range: 2026-03-26 through 2026-04-18

This file is a distilled reference, not a new policy surface. Canonical rules
belong in `AGENTS.md`, nested `AGENTS.md`, package `README.md` /
`REQUIREMENTS.md`, and the relevant skill files.

## Reusable Guidance Extracted From The Corpus

### Comment-Resolve Task Pattern

- When the user points at an inline comment or TODO directly, treat it as the
  task-local source of truth.
- Implement the narrowest change that satisfies the comment.
- Remove the stale comment in the same change.
- Keep exploration and verification proportional unless the prompt explicitly
  asks for broader analysis.

### Package And API Design

- Prefer pinned external libraries over repo-local reimplementation when the
  dependency already exists and matches the required behavior.
- Never use `object` as a convenience type at package boundaries.
- Prefer standard imports or `TYPE_CHECKING` guards over lazy repo-local import
  tricks that hide types from language servers and static tooling.
- Use `.to_posix()` when repo-owned `Path` objects must become persisted or CLI
  strings unless a native path format is explicitly required.
- Keep one semantic concept under one canonical owner; delete duplicate DTOs,
  wrappers, and shallow re-export surfaces during cleanup unless compatibility
  is explicitly required.
- Inline trivial wrappers; move genuinely shared helpers to shared owners
  instead of leaving them buried in leaf modules.
- Never fail silently for clearly invalid benchmark artifacts or geometry.

### Simplification And Cleanup

- Prefer clean cuts over backwards-compatibility scaffolding during internal
  refactors unless the prompt explicitly asks for transition support.
- Do not preserve old shapes through aliases, shallow re-exports, wrapper
  modules, or compatibility hubs.
- Treat duplicate ownership, boilerplate helpers, stale adapters, and preview-
  only widened interfaces as high-value simplification targets.

### Documentation Scope

- Keep root `README.md` focused on project framing, high-level status, and entry
  points.
- Put environment and runbook detail in `SETUP.md`.
- Put package-specific mechanics in the owning package `README.md`.
- Avoid repeating low-level commands or ownership prose across multiple docs
  surfaces.

### Rerun And Spatial Integration

- Treat Rerun as an observer sink or sidecar, not as a semantic pipeline stage.
- Keep normalization and method-specific basis handling at explicit method or
  stage boundaries, not in the coordinator hot path.
- When debugging Rerun regressions, inspect all `rr.` operations across the full
  logging path.
- Compare repo-local behavior against both the upstream ViSTA reference and the
  last known good local commit before recommending frame-convention changes.
- Preserve the distinction between camera-local geometry, world-space geometry,
  and viewer-only layout conventions.

### Maintenance Workflow

- When persisting prompt-derived guidance, keep only reusable rules and stable
  facts. Do not copy transient branch names, one-off cleanup requests, or other
  temporary task context into canonical guidance.
