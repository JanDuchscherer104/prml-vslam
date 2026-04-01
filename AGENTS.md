# PRML VSLAM Agent Guidance

This repository owns the configuration, artifact layout, evaluation, and reporting layers for an
off-device monocular VSLAM benchmark on smartphone video with unknown intrinsics.

## Sources Of Truth

<<<<<<< HEAD
- `README.md`: repository workflow, setup, developer commands, and high-level deliverables.
- `docs/Questions.md`: high-quality human-maintained ground truth for challenge intent, clarified
  requirements, operator-facing scope, and product constraints. Consult it whenever a task touches
  project scope, assumptions, or evaluation intent.
- `.agents/references/agent_reference.md`: lookup material for Context7 library IDs and primary
  sources relevant to this project.
- The nearest nested `AGENTS.md` overrides this file for its subtree.
=======
- `README.md`
- `docs/Questions.md`
- `.github/CODEOWNERS`
- The nearest nested `AGENTS.md`
>>>>>>> fb26801 (refactor: shrink metrics app PR scope)

## Repo Map

- `src/prml_vslam/`: installable package and pipeline code
- `tests/`: pytest suite
- `docs/report/main.typ`: report entry point
- `docs/slides/update-meetings/`: update-meeting slides

## Repo-Wide Rules

- Read the nearest nested `AGENTS.md` before editing.
<<<<<<< HEAD
  - Python/package rules: `src/prml_vslam/AGENTS.md`
  - App-specific Streamlit rules: `src/prml_vslam/app/AGENTS.md`
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
=======
- Stay within the requested task scope.
- Use conventional commits with concise, focused messages.
- Do not use destructive git commands unless explicitly requested.
- Prefer existing external tools and libraries over local reimplementation.
- Keep external wrappers thin and fail clearly when a dependency is missing or misconfigured.
>>>>>>> fb26801 (refactor: shrink metrics app PR scope)

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
