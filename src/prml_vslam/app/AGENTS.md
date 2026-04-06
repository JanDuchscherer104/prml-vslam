# Streamlit App Standards

This file applies to work under `src/prml_vslam/app/`.

## Sources of Truth

- Use `src/prml_vslam/app/REQUIREMENTS.md` for app scope, user-facing behavior, and acceptance
  criteria.
- Use `.agents/references/agent_reference.md` for lookup material on libraries and primary sources
  referenced by the app work.
- Use `src/prml_vslam/AGENTS.md` for Python/package engineering rules that still apply here.

## Architecture Rules

- Keep `streamlit_app.py` as a thin entrypoint that delegates into packaged app bootstrap code.
- Keep app modules small and typed. Page modules should focus on rendering and orchestration rather than inline domain logic.
- Reuse repo-owned evaluation contracts and artifact formats rather than inventing app-local semantics.
- The streamlit app is not responsible for pipeline orchestration, data flow or domain logic.

## State and Path Rules

- Model app-facing state with typed Pydantic-backed objects.
- One dedicated adapter is the only code allowed to read from or write to raw `st.session_state`.
- Treat `PathConfig` as the sole authority for path discovery, default roots, and path ownership.
- Do not introduce parallel ad hoc path-default logic in page code.

## Plotting and UX Rules

- Keep Plotly figure construction in [dedicated plotting modules](../plotting/__init__.py) instead of inline page code.
- Make `evo` computation an explicit user action rather than an implicit page-load side effect.
- Favor a simple modern light-first design with restrained typography, compact analysis surfaces,
  and minimal sidebar dependence over decorative hero-first layouts.
