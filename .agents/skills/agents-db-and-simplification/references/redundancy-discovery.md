# Redundancy Discovery

Use this reference when `agents-db-and-simplification` needs a deeper workflow for finding good simplification targets before editing code.

## Discovery Order

1. Start from the maintenance context.
   - Read `.agents/AGENTS_INTERNAL_DB.md`.
   - Run `make agents-db`.
   - Prefer active issues and todos over free-form cleanup.
2. Establish a baseline.
   - Capture the relevant focused tests.
   - Run `make loc` if Python LOC reduction is part of the goal.
3. Run a quick local search pass.
   - Use `rg` for duplicate symbol names, repeated config fields, repeated conditionals, unused imports, stale adapters, and suspicious `TODO` or compatibility branches.
4. Check for structural overlap.
   - Look for multiple wrappers around the same concept, repeated DTO shaping, parallel service helpers, or preview-only paths that leak into first-class code.
5. Escalate to deeper analysis only when needed.
   - Use `repo-context-explorer` for broader overlap, ownership, module, and flow analysis.
   - Use `mcp-python-refactoring` when you need candidate generation or safety guidance, not as the final decision-maker.

## High-Signal Search Patterns

Use targeted searches such as:

- repeated config-field names across contracts, CLI, README, and page state
- duplicate label builders, path-format helpers, or adapter factories
- metadata or provenance dicts that hide structured data
- dead enum values, unused exports, and compatibility branches left after refactors
- optional preview or experimental paths that widened core interfaces

## Escalate To `repo-context-explorer` When

- local `rg` results show multiple plausible owners for the same behavior
- you need ownership mapping before collapsing duplicate logic
- a suspected redundancy spans packages rather than one file cluster
- you need flow analysis to confirm that a field, helper, or abstraction is actually unused

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
