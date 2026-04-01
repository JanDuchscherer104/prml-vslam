# PRML VSLAM Agent Guidance

This repository owns the configuration, artifact layout, evaluation, and reporting layers for an
off-device monocular VSLAM benchmark on smartphone video with unknown intrinsics.

## Sources Of Truth

- `README.md`
- `docs/Questions.md`
- `.github/CODEOWNERS`
- The nearest nested `AGENTS.md`

## Repo Map

- `src/prml_vslam/`: installable package and pipeline code
- `tests/`: pytest suite
- `docs/report/main.typ`: report entry point
- `docs/slides/update-meetings/`: update-meeting slides

## Repo-Wide Rules

- Read the nearest nested `AGENTS.md` before editing.
- Stay within the requested task scope.
- Use conventional commits with concise, focused messages.
- Do not use destructive git commands unless explicitly requested.
- Prefer existing external tools and libraries over local reimplementation.
- Keep external wrappers thin and fail clearly when a dependency is missing or misconfigured.

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
