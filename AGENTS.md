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
- `.agents/references/agent_reference.md`: lookup material for Context7 library IDs and primary
  sources relevant to this project.
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

## Requirements And App Guidance

- When drafting requirements or specification documents, first extract every explicit user
  requirement before translating it into product or engineering requirements.
- For requirements work, use owner-authored repo guidance as the foundation. Prioritize `README.md`,
  `docs/Questions.md`, the nearest `AGENTS.md`, and `.github/CODEOWNERS` when resolving intent.
- Resolve discoverable repo facts locally before asking questions. If uncertainty still materially
  changes the spec or architecture, ask clarifying questions before finalizing the document. In
  Plan Mode, prefer extensive clarification when ambiguity remains.
- For Streamlit app work, prefer typed architectures with app-facing typed interfaces,
  Pydantic-backed state models, and one dedicated session-state adapter as the only raw
  `st.session_state` access point.
- For Streamlit app work, keep Plotly figure construction in dedicated plotting modules rather than
  inline page code.
- For Streamlit app work, treat `PathConfig` as the authoritative owner of path discovery, path
  defaults, and path handling.
- For Streamlit app work, favor a simple modern light-first design with restrained typography,
  compact analysis surfaces, and minimal sidebar dependence over decorative hero-first layouts.
