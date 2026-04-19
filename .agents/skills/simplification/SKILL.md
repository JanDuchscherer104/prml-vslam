---
name: simplification
description: Use when the user asks to reduce redundancy, boilerplate, dead code, unused symbols, unused config fields, overcomplication, or Python source LOC through behavior-preserving simplification, pruning, or refactoring in this repo.
---

# Simplification

## When To Use

Use this skill when the task is about:

- behavior-preserving simplification, pruning, or refactoring of the current intended surface
- reducing redundancy, boilerplate, dead code, stale adapters, unused symbols, unused config fields, or overcomplicated control flow
- lowering Python LOC without widening the public surface
- deleting obsolete compatibility layers, dead branches, or duplicate helpers



If the task also requires `.agents/` backlog reads or DB updates, use `agents-db` alongside this skill.

## Grounding

Before simplification work:

1. Read `README.md`, `docs/Questions.md`, `.agents/AGENTS_INTERNAL_DB.md`, and the nearest `AGENTS.md`.
2. Use the `graphify` skill when the simplification depends on architecture or cross-package ownership understanding.
3. Use focused `rg` searches and narrow file reads instead of bulk-loading the repo.
4. Prefer `mcp__code_index__` for indexed repo navigation when the search surface is broader than a quick local `rg` pass:
   - `set_project_path` + `build_deep_index` once per repo session before symbol-heavy exploration
   - `find_files` and `search_code_advanced` for overlap or redundancy discovery
   - `get_file_summary` and `get_symbol_body` for focused ownership and call-surface inspection
5. If the change is backlog-guided or should update repo debt tracking, run `make agents-db` and pair this skill with `agents-db`.
6. Keep the change scoped to the requested task; record validated new debt instead of opportunistically fixing unrelated areas.

## Workflow

1. Establish a baseline.
   - Use focused tests for the touched surface.
   - Use `make loc` when Python LOC reduction is part of the goal.
2. Identify candidates.
   - Use `rg`, `mcp__code_index__`, narrow file reads, and first-pass overlap or redundancy inspection.
   - Use the tool decision tree below rather than escalating ad hoc.
3. Choose the smallest behavior-preserving cut.
   - Prefer deleting or collapsing code over introducing more abstraction.
   - Unless the user explicitly asks for backwards compatibility, prefer clean cuts over preserving stale APIs, old import paths, deprecated wrappers, or transitional shims.
   - Do not keep obsolete surfaces alive through shallow re-exports, alias modules, compatibility import hubs, or thin wrapper functions added only to preserve the old shape.
   - Inline functions that have minimal logic, are only used once, and do not earn a stable name or reuse boundary.
   - Remove trivial wrapper functions whose only job is renaming or forwarding a single call.
   - If helper logic is genuinely shared, move it to the canonical shared owner instead of leaving quasi-shared helpers in leaf modules.
4. Validate the result.
   - Run focused tests, `make lint`, `ruff format`, and a final `make loc` when LOC is part of the decision.
   - Run `make ci` before creating a commit.

## Tool Decision Tree

Use tools in this order:

- Broad repo search or overlap discovery:
  - Use `rg` for tiny/local checks.
  - Use `mcp__code_index__.set_project_path` + `build_deep_index` once, then `find_files` and `search_code_advanced` for default indexed discovery.
- Decide whether a file is worth simplifying:
  - Use `mcp__code_index__.get_file_summary`.
- Inspect one helper, method, or class precisely:
  - Use `mcp__code_index__.get_symbol_body`.
- Check whether a helper should be inlined or deleted:
  - Use `search_code_advanced` on the helper name to estimate call-site count.
  - Use `get_symbol_body` to confirm the body is only minimal glue, renaming, or forwarding logic.
  - Use `get_file_summary` to see whether the containing file is accumulating low-value helper clutter.
- Rank package-level simplification candidates after code-index narrows the search surface:
  - Use `analyze_python_package`, `get_package_metrics`, and `find_package_issues`.
- Find file-local complexity cuts after code-index narrows the file:
  - Use `analyze_python_file`, `find_long_functions`, and `get_extraction_guidance`.
- Check safety before risky cleanup or when test confidence is weak:
  - Use `analyze_test_coverage` and `tdd_refactoring_guidance`.
- Use `analyze_security_and_patterns` only for auth, IO, network, shell, parsing, or other externally facing code.

Don't use tools this way:

- don't start repo-wide discovery with package/file analyzers
- don't treat analyzer suggestions as mandatory edits
- don't let generic analyzer output override repo ownership rules or simplification heuristics

## High-Value Targets In This Repo

Prioritize these targets over generic cleanup:

- duplicated page, service, adapter, or helper boilerplate
- dead branches, stale compatibility code, and unused exports
- unused functions, methods, symbols, enum values, or config fields
- generic metadata bags or free-form identifiers that should be typed or removed
- parallel contracts, DTOs, wrappers, or helper layers around the same concept
- minimal-logic functions used only once that should be inlined
- trivial wrapper functions whose only job is renaming or forwarding a single call
- temporary or experimental paths that widened core interfaces without enough value

## Guardrails

- Prefer lower Python LOC with preserved behavior.
- Prefer deletion, collapse, and narrower ownership over new abstraction.
- Keep one semantic concept under one canonical owner instead of parallel DTOs, wrappers, or re-export surfaces.
- Do not widen APIs, add compatibility scaffolding, or preserve stale surfaces unless the user explicitly asks for it.
- Treat analyzer output as advisory; repo ownership and simplification heuristics win.

See [references/redundancy-discovery.md](references/redundancy-discovery.md) for the deeper discovery workflow.

## Advisory Python Analysis

When available, Python-analysis MCP tools can be used as advisory analyzers:

- `analyze_python_file`, `analyze_python_package`
- `analyze_security_and_patterns`, `analyze_test_coverage`
- `find_long_functions`, `find_package_issues`
- `get_extraction_guidance`, `get_package_metrics`
- `tdd_refactoring_guidance`

Use them only after `mcp__code_index__` has narrowed the candidate package or file. They are not authoritative. Accept suggestions only when they fit repo-specific ownership rules and reduce real complexity. Do not widen APIs, add indirection, or preserve stale surfaces just because a generic refactoring tool flags them.

## Validation

- run focused tests for the changed surface
- run `make lint` and `ruff format` for Python changes
- run `make loc` before and after the work when LOC is part of the decision
- run `make ci` before creating a commit
