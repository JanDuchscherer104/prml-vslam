# PRML VSLAM App Requirements

## Purpose

This document is the concise source of truth for the packaged Streamlit app in `src/prml_vslam/app/`.

Use this file for current app behavior, target app constraints, and package-local ownership. Use the package README files and code for deeper implementation detail.

## Current State

- The app currently exposes five top-level pages: `Record3D`, `Datasets`, `Pipeline`, `Artifacts`, and `Metrics`.
- The `Record3D` page supports both the `USB` transport and the `Wi-Fi Preview` transport through one selector.
- The `Pipeline` page can show example request shapes, a generated `RunPlan`, one mock executed run, and the current offline plus bounded streaming demo surface.
- The `Pipeline` page may run offline ADVIO requests plus bounded Record3D live flows through pipeline-owned services.
- The `Pipeline` page currently renders an explicit `evo` APE preview when both reference and estimate TUM trajectories are available for the bounded demo result.
- The `Artifacts` page inspects persisted method-level run roots and keeps heavy trajectory, PLY, and Rerun artifact loading behind explicit user actions.
- The `Metrics` page keeps evaluation explicit and renders persisted `evo` trajectory results.

## Target State

- Keep the app as a thin launch, inspection, and monitoring surface.
- Keep both Record3D transports available while making their capability differences explicit to users.
- Keep app state typed and session-safe.
- Keep evaluation execution explicit rather than page-load-driven.

## Responsibilities

- The app owns Streamlit pages, packaged bootstrap code, typed page state, app-local controllers, and UI composition.
- The app owns rendering and user-facing interaction flow for the Record3D, ADVIO, Pipeline, and Metrics pages.
- The app does not own transport decoding, dataset normalization, pipeline semantics, backend orchestration, benchmark-policy logic, or viewer artifact semantics.

## Non-Negotiable Requirements

- App modules must stay small and typed instead of collapsing back into one monolithic file.
- The app must render only with Streamlit-native primitives; it must not embed raw HTML, oe CSS components.
- One adapter must remain the only app code that touches raw `st.session_state`.
- App-facing state must remain Pydantic-backed and JSON-friendly across reruns.
- The same session-state adapter must continue to own the opaque runtime controllers.
- `PathConfig` remains the authoritative source of repo paths and defaults.
- Heavy capture and decoding work must stay in `prml_vslam.io`.
- Runtime objects launched by the app must still consume typed repo-owned contracts rather than transport-specific browser state.
- `Start` and `Stop` actions on live pages must remain mutually exclusive and share the same action slot.
- Camera intrinsics should remain rendered as LaTeX instead of plain JSON.

## Explicit Non-Goals

- Implicit metric computation on load, selector changes, or reruns.
- General-purpose pipeline orchestration from the app layer.
- Duplicating dataset, pipeline, method, utils, or evaluation policy in page code.

## Validation

- Selecting `USB` or `Wi-Fi Preview` and starting a stream shows transport status, received frames, frame rate, intrinsics, RGB, depth, and confidence when available.
- Switching to `Metrics` renders a matching persisted `evo` result without recomputing it.
- Switching to `Artifacts` can inspect typed run metadata, canonical paths, stage output paths, and small raw metadata without loading heavy geometry or `.rrd` files.
- Switching to `Pipeline` shows the direct `RunRequest(...)` workflow, a generated `RunPlan` preview, one mock executed run, and an `evo` APE preview when the required trajectories are available.
- On live pages, only one of `Start` or `Stop` is visible in the shared action slot at a time.
- The file stays aligned with the shared section structure used by the other existing `REQUIREMENTS.md` files.
