---
name: agents-db-and-simplification
description: Use when working with PRML VSLAM's internal agent memory (`.agents/AGENTS_INTERNAL_DB.md`, `.agents/issues.toml`, `.agents/todos.toml`, `.agents/resolved.toml`, `make agents-db`) or when the user asks to reduce redundancy, boilerplate, dead code, unused symbols, unused config fields, overcomplication, or Python source LOC through simplification, pruning, or refactoring.
---

# AGENTS DB And Simplification

## When To Use

Use this skill when work in this repo depends on either of these workflows:

- reading or updating the internal agent-memory surfaces under `.agents/`
- triaging or resolving items with `make agents-db`
- simplification, pruning, or refactoring Python source code where `make loc` and LOC-negative keep/discard rules matter
- reducing redundancy, boilerplate, dead code, stale adapters, unused symbols, unused config fields, or overcomplicated control flow

## What This Skill Owns

This skill is the canonical workflow source for:

- using `.agents/AGENTS_INTERNAL_DB.md` as stable repo memory to persist important findings that should be reflected in the repository's canonical agent guidance
- using `.agents/issues.toml`, `.agents/todos.toml`, and `.agents/resolved.toml` as working memory
- using `make agents-db` to inspect, resolve, and maintain the active backlog
- doing behavior-preserving simplification, redundancy reduction, pruning, and LOC-aware refactoring

This skill is not the canonical source for:

- general package style and architecture rules in the nearest `AGENTS.md`
- broad repository orientation and deeper overlap exploration, which belong to `repo-context-explorer`

## Grounding

Before backlog-guided or simplification work:

1. Read `README.md`, `docs/Questions.md`, and the nearest `AGENTS.md`.
2. Read `.agents/AGENTS_INTERNAL_DB.md` for mission, configuration, ownership, and stable repo facts.
3. Use `rg` and narrow file reads instead of bulk-loading the repository.
4. Keep the change scoped to the requested task; record validated new debt instead of opportunistically fixing unrelated areas.

## Internal Agent Memory Workflow

Use the repo-local files under `.agents/` as follows:

- `.agents/issues.toml`
  - active validated defects, integration gaps, and architectural debt
- `.agents/todos.toml`
  - active actionable follow-up work linked to issue IDs
  - every todo must define `loc_min`, `loc_expected`, and `loc_max`
- `.agents/resolved.toml`
  - resolved or intentionally retired issues and todos
  - move completed work here instead of deleting records

Update the DB only when the work materially changes the repo's understanding:

- add or amend an issue when you validate a new defect, integration gap, architectural debt, or materially change an existing issue
- add or amend a todo when you identify, reprioritize, shrink, complete, or retire concrete follow-up work
- do not churn the DB for tiny local cleanups that do not change the active maintenance picture

Use the backlog helper script through `make agents-db`:

- `make agents-db`
  - prints the ranked active issues and todos
- `make agents-db AGENTS_ARGS='resolve issue ISSUE-XXXX --note "..."'`
  - moves an issue into `.agents/resolved.toml`
- `make agents-db AGENTS_ARGS='resolve todo TODO-XXXX --note "..."'`
  - moves a todo into `.agents/resolved.toml`

Ranking rules:

- issues sort by priority first, then status, then ID
- todos sort by priority first, then status, then lower `loc_expected`, then ID

## Simplification Workflow

Use this workflow when the task is about simplification, pruning, redundancy reduction, or behavior-preserving refactoring:

1. Ground in repo intent and current boundaries.
   - Read `README.md`, `docs/Questions.md`, `.agents/AGENTS_INTERNAL_DB.md`, and the nearest `AGENTS.md`.
2. Inspect the active backlog.
   - Run `make agents-db` before substantial backlog-guided work.
3. Establish a baseline.
   - Use focused tests for the touched surface.
   - Use `make loc` as the canonical Python LOC measurement for `src/` and `tests/`.
4. Identify candidates.
   - Use `rg`, narrow file reads, and first-pass overlap or redundancy inspection.
   - For deeper overlap, ownership, or flow analysis, switch to `repo-context-explorer`.
5. Choose the smallest behavior-preserving cut.
   - Prefer deleting or collapsing code over introducing more abstraction.
6. Validate the result.
   - Run focused tests, `make lint`, `ruff format`, and a final `make loc`.
   - Run `make ci` before creating a commit.
7. Update the agents DB only if the work materially validates, completes, narrows, reprioritizes, or retires debt.

## High-Value Simplification Targets In This Repo

Prioritize these target classes over generic "cleanup":

- duplicated page, service, adapter, or helper boilerplate
- dead branches, stale compatibility code, and unused exports
- unused functions, methods, symbols, enum values, or config fields
- generic metadata bags or free-form identifiers that should be typed or removed
- parallel contracts, DTOs, wrappers, or helper layers around the same concept
- optional preview-only subsystems that have grown into a maintenance-heavy path
- abstractions added mainly for tests or mocks that widen the surface without reducing complexity

Examples that fit this repo well:

- packet or runtime metadata carried through untyped generic bags instead of dedicated contracts
- config fields whose meaning drifted until they became misleading or only partially consumed
- preview-only transport paths that are useful but maintenance-heavy relative to their bounded scope

See [references/redundancy-discovery.md](references/redundancy-discovery.md) for the detailed discovery workflow.

## Use MCP Python Refactoring Selectively

Use `mcp-python-refactoring` as an advisory analyzer, not as authority. Accept suggestions only when they fit repo-specific ownership rules and reduce real complexity.

Use these tools selectively:

- `find_package_issues` and `get_package_metrics`
  - locate likely hotspots for duplication, layering drift, or oversized surfaces
- `find_long_functions` and `get_extraction_guidance`
  - identify extraction candidates, but do not extract helpers that only move code around
- `tdd_refactoring_guidance` and `analyze_test_coverage`
  - add safety rails when a simplification touches fragile or weakly tested behavior
- `analyze_security_and_patterns`
  - use only when the refactor touches risky or externally facing code

Be skeptical of suggestions that:

- add indirection or helper layers without shrinking the real surface
- widen APIs or config just to make the refactor easier
- optimize for generic code smells rather than this repo's actual maintenance burdens

## Keep And Reject Heuristics

Prefer:

- lower Python LOC with preserved behavior
- less indirection, fewer stale adapters, and narrower public or semi-public surfaces
- deleting dead paths, unused fields, and duplicate helpers instead of wrapping them
- typed, explicit contracts over generic metadata escape hatches

Reject:

- refactors that only move code around
- API or config widening that is not required by the user-facing behavior
- mock-only abstractions, speculative future-proofing, and unrelated cleanup
- feature creep during a simplification task
- positive Python LOC unless the user explicitly accepts the tradeoff or tests or safety clearly justify it

## Validation

- run focused tests for the changed surface during iteration
- run `make lint` during iteration for Python changes
- run `ruff format` on touched Python files before finishing
- run `make loc` before and after simplification work when LOC is part of the decision
- run `make ci` before creating a commit
- never use destructive git commands unless the user explicitly requests them
