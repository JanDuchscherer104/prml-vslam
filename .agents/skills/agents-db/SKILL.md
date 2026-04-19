---
name: agents-db
description: Use when working with PRML VSLAM's internal agent memory (`.agents/AGENTS_INTERNAL_DB.md`, `.agents/issues.toml`, `.agents/todos.toml`, `.agents/refactors.toml`, `.agents/resolved.toml`) or triaging, resolving, and maintaining the backlog with `make agents-db`.
---

# AGENTS DB

## When To Use

Use this skill when work in this repo depends on any of these:

- reading or updating the internal agent-memory surfaces under `.agents/`
- triaging or resolving issues, todos, and refactor candidates with `make agents-db`
- validating new repo facts, defects, integration gaps, or architectural debt that should be recorded in the agents DB
- backlog-guided work that needs the current ranked issue or todo state

For behavior-preserving code cleanup, pruning, or LOC reduction, also use `simplification`.

## What This Skill Owns

This skill is the canonical workflow source for:

- using `.agents/AGENTS_INTERNAL_DB.md` as stable repo memory that should eventually be reflected in canonical repo guidance when appropriate
- using `.agents/issues.toml`, `.agents/todos.toml`, `.agents/refactors.toml`, and `.agents/resolved.toml` as working memory
- using `make agents-db` to inspect, resolve, and maintain the active backlog

This skill is not the canonical source for general package style or architecture rules; use the nearest `AGENTS.md` for that.

## Grounding

Before DB work:

1. Read `README.md`, `docs/Questions.md`, and the nearest `AGENTS.md`.
2. Read `.agents/AGENTS_INTERNAL_DB.md` for mission, configuration, ownership, and stable repo facts.
3. Use `rg` and narrow file reads instead of bulk-loading the repository.
4. Keep the change scoped to the requested task; record validated debt instead of opportunistically editing unrelated code.

## DB Workflow

Use the repo-local files under `.agents/` as follows:

- `.agents/issues.toml`
  - active validated defects, integration gaps, and architectural debt
- `.agents/todos.toml`
  - active actionable follow-up work linked to issue IDs
  - every todo must define `loc_min`, `loc_expected`, and `loc_max`
- `.agents/refactors.toml`
  - active suggested refactors and simplifications that are worth considering but are not necessarily defect-driven
  - every refactor must define `loc_min`, `loc_expected`, and `loc_max`
- `.agents/resolved.toml`
  - resolved or intentionally retired issues, todos, and refactors
  - move completed work here instead of deleting records

Update the DB only when the work materially changes the repo's maintenance picture:

- add or amend an issue when you validate a new defect, integration gap, architectural debt, or materially change an existing issue
- add or amend a todo when you identify, reprioritize, shrink, complete, or retire concrete follow-up work
- add or amend a refactor when you identify, reprioritize, shrink, complete, or retire a high-value cleanup or simplification candidate that materially changes the maintenance picture
- do not churn the DB for tiny local cleanups that do not change the active maintenance picture

Use the backlog helper through `make agents-db`:

- `make agents-db`
  - prints the ranked active issues, todos, and refactors
- `make agents-db AGENTS_ARGS='resolve issue ISSUE-XXXX --note "..."'`
  - moves an issue into `.agents/resolved.toml`
- `make agents-db AGENTS_ARGS='resolve todo TODO-XXXX --note "..."'`
  - moves a todo into `.agents/resolved.toml`
- `make agents-db AGENTS_ARGS='resolve refactor REFACTOR-XXXX --note "..."'`
  - moves a refactor into `.agents/resolved.toml`

Ranking rules:

- issues sort by priority first, then status, then ID
- todos sort by priority first, then status, then lower `loc_expected`, then ID
- refactors sort by priority first, then status, then lower `loc_expected`, then ID

## Validation

- run `make agents-db` after DB edits to confirm the files still parse and rank correctly
- never delete records outright; resolve or retire them with history
- never use destructive git commands unless the user explicitly requests them
