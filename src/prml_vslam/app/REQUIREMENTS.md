# PRML VSLAM App Requirements

## Purpose

This document is the concise source of truth for the packaged Streamlit app in `src/prml_vslam/app/`.

Use this file for current app behavior, target app constraints, and package-local ownership. Use the package README files and code for deeper implementation detail.

## Current State

- The app currently exposes four top-level pages: `Record3D`, `ADVIO`, `Pipeline`, and `Metrics`.
- `Record3D` is the default landing page.
- `Metrics` remains reachable as the persisted trajectory-evaluation surface.
- The `Record3D` page supports both the canonical `USB` transport and the optional `Wi-Fi Preview` transport through one selector.
- The `Pipeline` page can show example request shapes, a generated `RunPlan`, one mock executed run, and the bounded demo pipeline surface.
- The `Pipeline` page may run the bounded ADVIO replay plus mock-SLAM demo and bounded Record3D live flows through pipeline-owned services.
- The `Pipeline` page currently renders an explicit `evo` APE preview when both reference and estimate TUM trajectories are available for the bounded demo result.
- The `Metrics` page keeps evaluation explicit and renders persisted `evo` trajectory results.

## Target State

- Keep the app as a thin launch, inspection, and monitoring surface.
- Keep both Record3D transports available while making their capability differences explicit to users.
- Keep app state typed and session-safe.
- Keep evaluation execution explicit rather than page-load-driven.

## Responsibilities

- The app owns Streamlit pages, packaged bootstrap code, typed page state, app-local controllers, and UI composition.
- The app owns rendering and user-facing interaction flow for the Record3D, ADVIO, Pipeline, and Metrics pages.
- The app does not own transport decoding, dataset normalization, pipeline semantics, backend orchestration, or benchmark-policy logic.

## Non-Negotiable Requirements

- `streamlit_app.py` must stay thin and delegate into packaged bootstrap code.
- App modules must stay small and typed instead of collapsing back into one monolithic file.
- The app must render only with Streamlit-native primitives; it must not embed raw HTML, CSS, or JavaScript custom components for Record3D.
- One adapter must remain the only app code that touches raw `st.session_state`.
- App-facing state must remain Pydantic-backed and JSON-friendly across reruns.
- The same session-state adapter must continue to own the opaque Record3D runtime controller for the current browser session.
- `PathConfig` remains the authoritative source of repo paths and defaults.
- Heavy capture and decoding work must stay in `prml_vslam.io`.
- Runtime objects launched by the app must still consume typed repo-owned contracts rather than transport-specific browser state.
- Important actions such as `Start`, `Stop`, and `Compute evo metrics` must remain explicit.
- `Start` and `Stop` actions on live pages must remain mutually exclusive and share the same action slot.
- Camera intrinsics should remain rendered as LaTeX instead of plain JSON.
- Switching Record3D transports or leaving the Record3D page must stop the active live stream and clear the live snapshot.

## Explicit Non-Goals

- Browser-owned Record3D widgets or browser-side frame decoding.
- Implicit metric computation on load, selector changes, or reruns.
- General-purpose pipeline orchestration from the app layer.
- Replacing `evo` with an app-local trajectory-metrics implementation.
- Duplicating dataset, pipeline, method, or evaluation policy in page code.

## Validation

- Opening the app lands on the `Record3D` page.
- Selecting `USB` or `Wi-Fi Preview` and starting a stream shows transport status, received frames, frame rate, intrinsics, RGB, depth, and confidence when available.
- Switching to `Metrics` renders a matching persisted `evo` result without recomputing it.
- Switching to `Pipeline` shows the direct `RunRequest(...)` workflow, a generated `RunPlan` preview, one mock executed run, and an `evo` APE preview when the required trajectories are available.
- On live pages, only one of `Start` or `Stop` is visible in the shared action slot at a time.
- The file stays aligned with the shared section structure used by the other existing `REQUIREMENTS.md` files.
