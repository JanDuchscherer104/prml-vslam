# PRML VSLAM Agent Guidance

This repository owns the configuration, artifact layout, evaluation, and reporting layers for an
off-device monocular VSLAM benchmark on smartphone video with unknown intrinsics.

## Sources Of Truth

- `README.md`: repository workflow, setup, developer commands, and high-level deliverables.
- `docs/Questions.md`: high-quality human-maintained ground truth for challenge intent, clarified
  requirements, operator-facing scope, and product constraints. Consult it whenever a task touches
  project scope, assumptions, or evaluation intent.
- `.github/CODEOWNERS`: ownership hints for code paths, review surfaces, and intent resolution when
  repo responsibilities are ambiguous.
- `.agents/AGENTS_INTERNAL_DB.md`: compact internal alignment database for stable repo facts,
  workflow constraints, and configuration policy.
- `.agents/issues.toml`: structured backlog of validated defects, architectural debts, and
  integration gaps.
- `.agents/todos.toml`: structured action list linked to the validated issues backlog.
- `.agents/resolved.toml`: archive of resolved or retired issues and todos moved out of the active
  backlogs.
- `.agents/references/agent_reference.md`: lookup material for Context7 library IDs and primary
  sources relevant to this project.
- The nearest nested `AGENTS.md` overrides this file for its subtree.

## Repo Map

- `src/prml_vslam/`: installable package and pipeline code
- `tests/`: pytest suite
- `docs/report/main.typ`: report entry point
- `docs/slides/update-meetings/`: update-meeting slides

## Repo-Wide Rules

- Use the internal `.agents` databases as working memory:
  - read `.agents/AGENTS_INTERNAL_DB.md` before substantial repo work
  - update `.agents/issues.toml` when you validate a new issue or materially change an existing one
  - update `.agents/todos.toml` when you identify, reprioritize, or complete concrete follow-up work
  - move resolved or retired work into `.agents/resolved.toml` instead of deleting it
  - every todo must define `loc_min`, `loc_expected`, and `loc_max` in lines of code
  - use `make agents-db` to review the ranked active backlog
  - pass `AGENTS_ARGS="..."` to `make agents-db` for filtered ranking or resolve actions
- Read the nearest nested `AGENTS.md` before editing.
  - Python/package rules: `src/prml_vslam/AGENTS.md`
  - App-specific Streamlit rules: `src/prml_vslam/app/AGENTS.md`
  - Documentation and Typst rules: `docs/AGENTS.md`
- Stay within the requested task scope. Do not implement adjacent features or speculative cleanup
  unless the user explicitly asks for it.
- Use `make loc` as the canonical Python LOC measurement for `src/` and `tests/` when reasoning
  about code size, simplification, pruning, or boilerplate removal.
- When tasked to prune code, prefer removing redundancy, dead paths, duplicated logic, stale
  adapters, and boilerplate over moving code around without reducing complexity.
- When tasked to simplify code, the `make loc` result should not move in the positive direction for
  Python code unless the user explicitly approves that tradeoff.
  - Prefer a flat-or-negative `code` delta, not just a flat total-line delta.
  - If safety requires adding tests or scaffolding, offset that growth by removing more redundancy
    than you add, or explicitly call out the LOC tradeoff before finishing.
- Use conventional commits with concise, focused messages. Split larger changes into multiple
  logical commits when appropriate.
- Before creating a commit, run `make ci`.
- After editing a file, run `ruff format` on touched Python files before finishing the task.
- Do not use destructive git commands unless explicitly requested. This includes `git restore`,
  `git reset --hard`, and similar commands.
- Never disable the formatter with inline pragmas; refactor code to satisfy structure and
  formatting constraints without turning formatting off for a file or block.
- Prefer existing external tools and libraries over local reimplementation when the repo already
  depends on them.
- Keep external wrappers thin and fail clearly when a dependency is missing or misconfigured.
  For external-method wrappers:
  - use official upstream entry points where practical
  - fail early when an external dependency is unavailable or misconfigured
  - document unsupported cases explicitly
  - do not hide fallback behavior inside wrappers
- Treat ARCore, reference reconstructions, and benchmark tools as explicit external baselines, not
  hidden parts of a method wrapper.
- For repo-owned persisted configuration, prefer TOML for `BaseConfig` derivatives.
  - use `BaseConfig.from_toml()`, `BaseConfig.to_toml()`, and `BaseConfig.save_toml()`
  - use `PathConfig.resolve_toml_path()` for repo-relative config files
  - avoid inventing parallel ad hoc config formats for durable workflows

## Requirements And App Guidance

- When drafting requirements or specs, first extract every explicit user requirement before
  translating it into product or engineering requirements.
- For requirements work, prioritize `README.md`, `docs/Questions.md`, the nearest `AGENTS.md`, and
  `.github/CODEOWNERS` when resolving intent.
- Resolve discoverable repo facts locally before asking questions. If ambiguity still materially
  changes the spec, ask clarifying questions before finalizing it. In Plan Mode, prefer extensive
  clarification when ambiguity remains.
- For Streamlit app work, keep app-facing interfaces typed, use Pydantic-backed state, and route
  all raw `st.session_state` access through one dedicated adapter.
- For Streamlit app work, keep Plotly figure construction in dedicated plotting modules.
- For Streamlit app work, treat `PathConfig` as the authoritative owner of path discovery and path
  defaults.
- For Streamlit app work, favor a simple modern light-first design with compact analysis surfaces
  and minimal sidebar dependence.
