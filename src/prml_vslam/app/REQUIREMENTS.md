# PRML VSLAM App Requirements

## Summary

This document is the source of truth for the packaged Streamlit app in
`src/prml_vslam/app/`.

The app now exposes four top-level pages:

- `Record3D`
- `ADVIO`
- `Pipeline`
- `Metrics`

`Record3D` is the default landing page. `Metrics` remains the trajectory-evaluation
surface for persisted `evo` results.

## Functional Requirements

- The app must default to the `Record3D` page on first load.
- The app must keep the `Metrics` page reachable without removing any existing
  trajectory-evaluation functionality.
- The app must expose a `Pipeline` page that explains the typed run-planning
  surface, the direct request pattern, and concrete usage examples without
  executing a pipeline.
- The `Pipeline` page must also show one mock completed run with stage status,
  artifact contracts, and serialized output examples so users can inspect what
  the planner hands to downstream execution surfaces.
- The `Record3D` page must support both `USB` and `Wi-Fi` transports through one
  transport selector.
- The `Record3D` page must show:
  - transport status
  - received frames
  - measured frame rate
  - camera intrinsics
  - RGB preview
  - depth preview
  - uncertainty or confidence preview when available
- The `Metrics` page must keep explicit `evo` computation semantics:
  never compute on selector changes or reruns.

## Architecture Requirements

- The implementation target remains `src/prml_vslam/app/`.
- `streamlit_app.py` must stay thin and delegate into packaged bootstrap code.
- The app must use small typed modules rather than one monolithic file.
- The app must render only with Streamlit-native primitives.
- The app must not embed raw HTML, CSS, or JavaScript custom components for the
  Record3D flow.
- `PathConfig` must remain the authoritative source of repo paths and defaults.
- Heavy capture and decoding work must stay in `prml_vslam.io`.
- The app may orchestrate background runtime objects, but those runtime objects
  must still consume typed `io` contracts rather than transport-specific browser
  state.

## State And Typing Requirements

- All app-facing interfaces must be typed.
- App state must be modeled with Pydantic.
- One adapter must be the only app code that touches raw `st.session_state`.
- Persisted state must stay JSON-friendly so reruns restore cleanly.
- The same session-state adapter must also own the opaque Record3D runtime
  controller for the current browser session.

## UX Requirements

- The UI must stay simple, modern, and light-first.
- The layout must prioritize compact analysis and monitoring surfaces over
  decorative sections.
- Important actions such as `Start`, `Stop`, and `Compute evo metrics` must be
  explicit and clearly labeled.
- Camera intrinsics should be rendered as LaTeX rather than plain JSON.
- When the selected transport changes, or when the user leaves the Record3D
  page, the current live stream must stop and the live snapshot must be cleared.

## Acceptance Scenarios

### Record3D Preview

- A user opens the app and lands on `Record3D`.
- They select `USB` or `Wi-Fi`.
- Starting the stream shows transport status, received frames, frame rate,
  intrinsics, RGB, depth, and uncertainty when available.

### Metrics Review

- A user switches to `Metrics`.
- If a matching persisted `evo` result exists, the app renders it without
  recomputing anything.

### Pipeline Guide

- A user switches to `Pipeline`.
- The app shows example pipeline shapes, the direct `RunRequest(...)` workflow
  with nested stage configs, one generated `RunPlan` table, and one mock
  executed run.
- The page does not execute any backend or write artifacts as a side effect.

### Explicit Evaluation

- A user selects a dataset slice with both reference and estimate TUM
  trajectories present.
- The app exposes a clear compute action.
- Triggering that action runs `evo`, persists the result, and renders it.

## Out Of Scope

- Browser-owned Record3D widgets or browser-side frame decoding.
- Implicit metric computation on load or selector changes.
- Pipeline execution or unrelated dataset tooling from the app layer.
- Replacing `evo` with an app-local trajectory-metrics implementation.
