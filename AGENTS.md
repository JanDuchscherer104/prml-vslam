# PRML VSLAM Agent Guidance

This repository owns the configuration, artifact layout, normalization, evaluation, and reporting
layers for an off-device monocular VSLAM benchmark on smartphone video with unknown intrinsics.
External systems such as ViSTA-SLAM, MASt3R-SLAM, ARCore, COLMAP, Meshroom, Open3D, CloudCompare,
and `evo` are integrated as thin wrappers or documented external tools rather than reimplemented in
this repo.

## Sources of Truth

- `README.md`: repository workflow, setup, developer commands, and high-level deliverables.
- `docs/Questions.md`: high-quality human-maintained ground truth for challenge intent, clarified
  requirements, operator-facing scope, and product constraints. Consult it whenever a task touches
  project scope, assumptions, or evaluation intent.
- `docs/agent_reference.md`: binding detailed benchmark contract and agent lookup reference.
- The nearest nested `AGENTS.md` overrides this file for its subtree.

## Repo Map

- `src/prml_vslam/`: installable Python package and pipeline code
- `tests/`: pytest suite
- `docs/report/main.typ`: report entry point
- `docs/slides/update-meetings/update-slides.typ`: unified weekly update-meeting deck
- `docs/slides/update-meetings/meeting-0X/*.typ`: meeting-local slide fragments
- `.venv/bin/python`: local project interpreter

## Repo-Wide Rules

- Read the nearest nested `AGENTS.md` before editing.
  - Python/package rules: `src/prml_vslam/AGENTS.md`
  - Documentation and Typst rules: `docs/AGENTS.md`
- Stay within the requested task scope. Do not implement adjacent features or speculative cleanup
  unless the user explicitly asks for it.
- Use conventional commits with concise, focused messages. Split larger changes into multiple
  logical commits when appropriate.
- Do not use `git restore`, `git reset --hard`, or other destructive commands unless explicitly
  requested.
- Prefer existing external tools over reimplementation when the repo already depends on them.
- Keep external-method wrappers thin:
  - use official upstream entry points where practical
  - fail early when an external dependency is unavailable or misconfigured
  - document unsupported cases explicitly
  - do not hide fallback behavior inside wrappers
- Treat ARCore, reference reconstructions, and benchmark tools as explicit external baselines, not
  hidden parts of a method wrapper.
- When changing benchmark assumptions, artifact contracts, alignment policy, or evaluation protocol,
  update the relevant documentation in the same change. At minimum, sync `docs/agent_reference.md`
  and any affected user-facing docs in `README.md`, `docs/Questions.md`, or `docs/report/`.
- When the user asks for an overview of changes, provide a concise, scan-friendly summary grounded
  in current repo state. Prefer a short outcome summary plus a compact index using `git status
  --short`, `git diff --stat`, and targeted `rg -n` hits for the most relevant new terms, files, or
  policy phrases.
