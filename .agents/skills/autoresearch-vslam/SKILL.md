---
name: autoresearch-vslam
description: Adapt Karpathy's autoresearch loop to PRML VSLAM. Use when the user wants Codex to run bounded, evidence-driven research iterations in this repo with a fixed evaluation harness, a dedicated research branch, an experiment log under `.logs/autoresearch/`, non-destructive keep-or-discard decisions, and repo-specific validation such as `make lint`, targeted `pytest`, `make ci`, `make loc`, `plan-run-config`, and persisted `evo` metrics.
---

# Autoresearch For PRML VSLAM

## Summary

This skill adapts the core `autoresearch` idea from
[karpathy/autoresearch](https://github.com/karpathy/autoresearch):

- define a narrow research question
- freeze an evaluation harness
- run repeated experiments
- keep only winning changes
- log the outcome of every trial

The adaptation for this repository is intentionally stricter than the
upstream loop:

- research loops are **bounded**, not infinite
- destructive git flows such as `git reset --hard` are **not allowed**
- the repo has multiple valid evaluation surfaces, so each run must declare
  its own frozen harness
- accepted changes must still respect repo rules such as `make lint`,
  focused tests during iteration, and `make ci` before a final commit

Read [references/upstream-autoresearch.md](references/upstream-autoresearch.md)
for the upstream mechanics and the exact adaptation notes.

## When To Use

Use this skill when the user wants Codex to act like an autonomous researcher
inside this repo, for example:

- iterating on one benchmark or evaluation surface with a clear success metric
- trying several alternative implementations and keeping only the winner
- running a small series of method-wrapper, pipeline, dataset, or app
  experiments with a shared log
- exploring simplification work where `make loc` is part of the keep/discard
  decision

Do not use this skill for:

- one-off bug fixes
- open-ended architecture brainstorming without a fixed evaluation harness
- broad refactors that touch many unrelated subsystems at once

## Setup

Before starting a loop:

1. Read the local sources of truth:
   - `README.md`
   - `docs/Questions.md`
   - `AGENTS.md`
   - the nearest nested `AGENTS.md` for the code you expect to edit
   - any relevant package `README.md` / `REQUIREMENTS.md`
2. Define a **research brief** with all of the following:
   - research question
   - primary metric
   - secondary guardrails
   - mutable surface
   - immutable surface
   - max experiment count or time budget
3. Create a dedicated branch, for example
   `codex/autoresearch-2026-04-06-evo-harness`.
4. Initialize the run log:

```bash
uv run python .agents/skills/autoresearch-vslam/scripts/init_run.py \
  --tag 2026-04-06-evo-harness \
  --question "Reduce pipeline evo-preview failures from timestamp mismatch handling." \
  --primary-metric "targeted pytest pass count" \
  --evaluation-cmd "uv run pytest tests/test_app.py -k evo_preview" \
  --mutable "src/prml_vslam/app/pages/pipeline.py" \
  --mutable "tests/test_app.py" \
  --immutable "docs/Questions.md" \
  --immutable "src/prml_vslam/interfaces/*"
```

This creates:

- `.logs/autoresearch/<tag>/brief.md`
- `.logs/autoresearch/<tag>/results.tsv`

## Research Brief Rules

Every run must freeze these decisions up front.

### Research Question

Good:

- "Can we simplify ADVIO download mechanics without changing app-facing behavior?"
- "Can we improve the pipeline demo evo preview without widening the public API?"

Bad:

- "Make the repo better"
- "Try some stuff"

### Primary Metric

Choose one objective metric that decides winners. Typical choices in this repo:

- targeted `pytest` pass/fail
- `make ci` pass/fail for end-state verification
- `trajectory_metrics.json` RMSE or matched-pair counts
- explicit artifact existence and shape checks
- `make loc` delta for simplification work

### Secondary Guardrails

Guardrails do not define the winner, but they prevent bad wins:

- no public API widening unless required
- no new undeclared dependencies
- no drift from `README.md` / `docs/Questions.md`
- no positive Python LOC delta unless justified by tests or safety

### Mutable Surface

Keep the editable surface small. Prefer one module cluster such as:

- one package contract plus its tests
- one dataset adapter plus its tests
- one Streamlit page/controller pair plus its tests

### Immutable Surface

At minimum, freeze the evaluation harness and unrelated source-of-truth docs.
Like upstream `prepare.py`, these are not edited during the run unless the
research question explicitly targets them.

## Safe Git Flow

Do **not** use `git reset --hard`.

Use a winner branch plus ephemeral trial branches:

1. Keep the current best state on `codex/autoresearch-<tag>`.
2. For each experiment, create a short-lived branch from that winner, for
   example `codex/autoresearch-<tag>-trial-03`.
3. Make one focused change and commit it.
4. Run the frozen evaluation harness.
5. If the experiment wins:
   - switch back to the winner branch
   - cherry-pick the winning commit
   - log `keep`
6. If the experiment loses:
   - log `discard` or `crash`
   - abandon the trial branch

If the worktree is already dirty with unrelated user changes, stop and isolate
the work before starting a loop. Do not let a research loop trample unrelated
local edits.

## Experiment Loop

Repeat until the declared budget is exhausted:

1. Re-read the research brief.
2. Form exactly one experiment hypothesis.
3. Edit only the mutable surface.
4. Run `make lint`.
5. Run the frozen evaluation command(s).
6. If the idea changes config contracts, artifact formats, or benchmark
   assumptions, update `.agents/references/agent_reference.md` in the same
   winning change.
7. Decide:
   - `keep` if the primary metric improves
   - `keep` if the primary metric is equal and the result is materially simpler
   - `discard` otherwise
8. Record the outcome in `.logs/autoresearch/<tag>/results.tsv`.

When the loop ends and the user wants a final deliverable:

- run `make ci`
- update `.agents/issues.toml` / `.agents/todos.toml` for validated new debt
- move completed or retired backlog items into `.agents/resolved.toml`

## Logging Format

`results.tsv` uses these columns:

```text
experiment_id	commit	status	primary_metric	secondary_metric	description
```

Status must be one of:

- `keep`
- `discard`
- `crash`

The description should state the exact hypothesis, not a vague summary.

Good:

- `simplify SessionStateStore via one generic loader helper`
- `replace manual ADVIO archive fetch with pooch-backed retrieval`

Bad:

- `cleanup`
- `refactor`

## Keep/Discard Heuristics

Prefer:

- equal or better metric with less code
- narrower ownership boundaries
- thinner wrappers around external tools
- tighter alignment with `README.md`, `docs/Questions.md`, and `AGENTS.md`

Be skeptical of:

- wins that depend on widened mock-only abstractions
- wins that add boilerplate without measurable benefit
- wins that quietly change the benchmark question

## Suggested Evaluation Surfaces

Choose one and freeze it in the brief:

- Planner and config work:
  - `uv run pytest tests/test_main.py`
  - `uv run prml-vslam plan-run-config <config.toml>`
- App/runtime work:
  - targeted `tests/test_app.py`
- Dataset work:
  - targeted `tests/test_advio.py`
- Package API work:
  - `tests/test_package_exports.py`
- Simplification work:
  - `make loc`
- Trajectory evaluation work:
  - persisted `evaluation/trajectory_metrics.json`
  - targeted app/tests around `evo`

## Repo-Specific Differences From Upstream

The upstream autoresearch loop edits one file, runs one fixed training script,
and can safely discard experiments with destructive resets. This repo is
different:

- multiple subsystems are in play
- `make ci` is much heavier than one 5-minute train run
- destructive rollback is disallowed
- repo memory lives in `.agents/issues.toml`, `.agents/todos.toml`, and
  `.agents/resolved.toml`

That means this skill favors short, explicit, reproducible loops over the
upstream "never stop" autonomy model.
