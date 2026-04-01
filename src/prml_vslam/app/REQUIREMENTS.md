# PRML VSLAM Metrics App Requirements

## Summary

This document is the source of truth for the metrics-first Streamlit app that lives in
`src/prml_vslam/app/`.

The app serves repo developers and researchers who need to inspect trajectory evaluation outputs.
Its primary user flow is:

`dataset -> sequence -> method/run`

The current legacy workbench in `src/prml_vslam/app.py` is out of scope for v1. The new app focuses
on trajectory metrics, persisted `evo` results, and explicit evaluation actions.

## Sources Of Truth

- `README.md`
- `docs/Questions.md`
- `AGENTS.md`
- `src/prml_vslam/AGENTS.md`
- `.github/CODEOWNERS`

## Extracted Input Requirements

- Create `REQUIREMENTS.md` in `prml_vslam/app`.
- Extract every explicit prompt requirement before interpretation.
- Use owner-authored repo guidance as the foundation for the document.
- If uncertainty materially affects the spec, ask clarifying questions in Plan Mode.
- Follow best practices for Streamlit apps with Pydantic state management.
- Use a simple modern design.
- Display `evo` metrics for the selected dataset.
- Integrate natively with `PathConfig`.
- Use Plotly for plotting.
- Define plots in separate plotting modules.
- Type all interfaces.

## Functional Requirements

- The app must be metrics-first and centered on trajectory evaluation review.
- The primary flow must be `dataset -> sequence -> method/run`.
- The app must read persisted `evo` results when they already exist.
- The app must offer an explicit action to compute `evo` metrics when reference and estimate
  trajectories are both present.
- The app must never compute metrics on page load, rerun, or selector change.
- The app must show the provenance needed to interpret a result:
  dataset, sequence, run, pose relation, alignment flag, scale-correction flag, matched pairs, and
  source paths.
- Missing artifacts must be surfaced clearly and honestly.

## Architecture Requirements

- The implementation target is `src/prml_vslam/app/`.
- `streamlit_app.py` must stay thin and delegate into packaged bootstrap code.
- The app must use small typed modules rather than one monolithic file.
- Plotly figure creation must stay outside page modules.
- `PathConfig` must remain the authoritative source of path resolution and defaults.
- The app must reuse existing repo and library contracts where possible instead of adding new
  app-local subsystems.

## State And Typing Requirements

- All app-facing interfaces must be typed.
- App state must be modeled with Pydantic.
- One adapter must be the only app code that touches raw `st.session_state`.
- Persisted state must stay JSON-friendly so reruns restore cleanly.

## UX Requirements

- The UI must be simple, modern, and light-first.
- The layout must prioritize compact analysis surfaces over decorative hero sections.
- The main content area must lead. Sidebar dependence should be minimal.
- Important actions such as evaluation must be explicit and clearly labeled.

## Acceptance Scenarios

### Persisted Review

- A user selects a dataset, sequence, and run.
- If a matching persisted `evo` result exists, the app renders it without recomputing anything.

### Explicit Evaluation

- A user selects a dataset slice with both reference and estimate TUM trajectories present.
- The app exposes a clear compute action.
- Triggering that action runs `evo`, persists the result, and renders it.

### Missing Data

- A user selects a slice without the required trajectories.
- The app explains what is missing and does not fabricate fallback behavior.

## Out Of Scope

- Recreating the full legacy workbench.
- Adding pipeline execution, streaming demos, or unrelated dataset tooling to the app change.
- Replacing `evo` with an app-local trajectory-metrics implementation.
