# Redundancy Discovery

Use this reference when `simplification` needs a deeper workflow for finding good simplification targets before editing code.

## Discovery Order

1. Start from the maintenance context.
   - Read `.agents/AGENTS_INTERNAL_DB.md`.
   - If the work is backlog-guided or should update debt tracking, run `make agents-db` and pair the task with `agents-db`.
2. Establish a baseline.
   - Capture the relevant focused tests.
   - Run `make loc` if Python LOC reduction is part of the goal.
3. Run a quick local search pass.
   - Use `rg` for duplicate symbol names, repeated config fields, repeated conditionals, unused imports, stale adapters, and suspicious `TODO` or compatibility branches.
   - Use `mcp__code_index__.set_project_path` + `build_deep_index` once per repo session when the search surface is broader than a quick local grep.
   - Use `mcp__code_index__.find_files` or `search_code_advanced` when indexed search is clearer than repeated shell grep.
4. Narrow the candidate.
   - Use `mcp__code_index__.get_file_summary` to decide whether a file is worth simplifying.
   - Use `mcp__code_index__.get_symbol_body` to inspect one helper or method before inlining, deleting, or moving it.
   - Use `search_code_advanced` on the helper name to estimate whether it is a one-use function or trivial wrapper candidate.
5. Escalate only when needed.
   - Look for multiple wrappers around the same concept, repeated DTO shaping, parallel service helpers, or temporary paths that still leak into first-class code.
   - Use the `graphify` skill when the simplification depends on broader ownership or architecture context.
   - Use `analyze_python_package`, `get_package_metrics`, and `find_package_issues` only after code-index narrows the package.
   - Use `analyze_python_file`, `find_long_functions`, and `get_extraction_guidance` only after code-index narrows the file.
   - Use `analyze_test_coverage` and `tdd_refactoring_guidance` before risky cleanup or when test confidence is weak.
   - Use `analyze_security_and_patterns` only for externally facing or risk-sensitive code.

## High-Signal Search Patterns

Use targeted searches such as:

- repeated config-field names across contracts, CLI, README, and page state
- duplicate label builders, path-format helpers, or adapter factories
- helper names that appear only once outside their own definition
- wrapper functions that only forward one call or rename arguments
- metadata or provenance dicts that hide structured data
- dead enum values, unused exports, and compatibility branches left after refactors
- temporary or experimental paths that widened core interfaces

Useful indexed probes:

- `find_files` for clusters like `README.md`, `REQUIREMENTS.md`, `services.py`, or `contracts.py`
- `search_code_advanced` for repeated field names, helper names, or conditionals
- `get_file_summary` for quick file triage before opening raw code
- `get_symbol_body` for one candidate helper before deciding whether to inline, delete, or move it

One-use / trivial-wrapper check:

1. `search_code_advanced` for the function name across `src/` and `tests/`
2. if the only hits are the definition plus one call site, inspect the body with `get_symbol_body`
3. if the body is only forwarding, renaming, or tiny glue logic, prefer inlining or deletion
4. if the helper is used in multiple places or provides a real semantic boundary, keep it

## Escalate To `graphify` When

- local `rg` results show multiple plausible owners for the same behavior
- you need ownership mapping before collapsing duplicate logic
- a suspected redundancy spans packages rather than one file cluster
- you need architecture context to confirm that a field, helper, or abstraction is actually redundant

## Candidate Quality Filter

Good simplification targets usually have all of these traits:

- behavior can stay the same
- ownership gets narrower or clearer
- the code path becomes shorter, more explicit, or easier to test
- the resulting Python LOC is lower or flat

Bad targets usually look like this:

- the change mostly renames or reshuffles code
- helpers or adapters are added without deleting equivalent complexity
- a generic abstraction is introduced for one call site
- a config or API surface is widened just to support the cleanup
