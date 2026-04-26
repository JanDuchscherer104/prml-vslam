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

This skill supports two modes:

- default simplification: reduce redundancy and stale surface while preserving the current intended behavior
- ruthless simplification: an explicit opt-in mode for drastic LOC, type-count, public-surface, and indirection reduction while preserving the currently intended behavior

Use ruthless simplification only when the user explicitly asks for a ruthless, aggressive, or drastic reduction rather than a conservative cleanup.

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

## Ruthless Simplification

Use ruthless simplification when the goal is to drastically reduce LOC, type count, public surface, and indirection while preserving the currently intended behavior.

### Preserve Functionality

Preserve:

- behavior exercised by tests
- explicit external or public contracts listed in `AGENTS.md`
- domain invariants
- intentionally retained CLI, API, or config behavior named in the task

Do not preserve unless explicitly requested:

- backward compatibility shims
- deprecated wrappers and aliases
- internal symbol names
- transitional overloads
- dead feature flags
- duplicate DTO hierarchies
- duplicate enums for the same semantic axis
- legacy extension points with no active consumers

### Hard Bias

- Prefer deletion over abstraction.
- Prefer inlining over helper extraction.
- Prefer one canonical type per concept.
- Prefer one canonical enum per semantic axis.
- Prefer one behavior-bearing base class over multiple protocol-only internal interfaces.
- If a new abstraction is introduced, it must justify its existence.

### Abstraction Tax

A new helper, function, class, or base type is allowed only if at least one is true:

- it protects a real invariant
- it serves 3 or more meaningful call sites
- it becomes the canonical home of shared behavior
- it removes more code than it adds within the same patch

Otherwise inline, merge, or delete.

### Inline By Default When

- the function has one meaningful call site
- it only forwards or reorders arguments
- it only renames another operation
- its name adds no important domain vocabulary
- it is short and not independently tested
- it exists only to preserve an older call shape

### Convert Free Function To Method When

- it primarily reads or writes one object's state
- it uses multiple fields from the same object
- it encodes validation, normalization, or lifecycle transitions
- it is only used by that owning type
- it belongs to the object's domain language

### Convert Sibling Leaf Behavior To Base Class When

- multiple implementations are internal to this repo
- they repeat orchestration, validation, caching, or lifecycle logic
- the shared behavior reflects a real common invariant
- the current protocol carries no meaningful implementation

Use `Protocol` only for structural typing across unrelated or external implementations. If behavior is shared, move it into an ABC or base class and keep only the true variation points abstract.

### DTO And Config Rules

- Merge models with heavy overlap unless validation semantics truly differ.
- Create, update, and response splits require distinct constraints, not just tradition.
- Boundary adapters may exist only at ingress or egress.
- Delete compatibility serializers or parsers once the canonical form is chosen.
- Delete dead flags and partially consumed config.
- Prefer nested canonical configs over parallel flattened variants.
- Pipeline should compose stage configs, not own stage-internal config logic by default.

### Enum Rules

- One semantic axis means one enum.
- Collapse sibling enums that differ only by naming or package location.
- Keep conversion logic at boundaries, not as parallel enums in the core.
- Delete redundant aliases unless they are part of an explicit public contract.

### Required Work Report

When operating in ruthless simplification mode, before editing state:

- what will be deleted
- what will be merged
- what will be inlined
- what compatibility paths will be removed
- what behavior-bearing base classes will be introduced

After editing, report:

- files removed
- symbols removed
- DTOs merged
- enums collapsed
- wrappers inlined or deleted
- behavior pulled into base classes
- LOC delta
- tests or checks run
- remaining risks

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
