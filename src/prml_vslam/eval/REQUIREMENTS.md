# Eval Requirements

## Purpose

This document is the concise source of truth for the repository-local evaluation package in `src/prml_vslam/eval/`.

## Current State

- `prml_vslam.eval` is intentionally a thin local evaluation surface for the app and tests.
- The implemented end-to-end flow today is explicit `evo` APE trajectory evaluation over persisted run artifacts.
- The package already owns typed controls, discovery payloads, persisted results, and plotting-facing contracts for that local flow.
- Dense-cloud and efficiency evaluation concepts exist as typed seams, but they are not yet a complete benchmark-policy implementation.

## Target State

- Keep evaluation execution explicit and separate from app interaction flow.
- Add typed dense-cloud and efficiency surfaces only once the upstream artifact contracts stabilize elsewhere in the repo.
- Keep the package thin even if more evaluation surfaces are added later.

## Responsibilities

- The package owns typed evaluation controls, result payloads, run discovery, trajectory artifact resolution, explicit trajectory evaluation execution, and persisted evaluation results.
- The package does not own benchmark policy, dataset normalization, method execution, app state, or pipeline-stage planning.

## Non-Negotiable Requirements

- The package must discover repository-local runs from normalized artifact layouts rather than app-local path heuristics.
- Required reference and estimate trajectories must be resolved explicitly and fail clearly when missing.
- Persisted evaluation results must stay deterministic and reloadable.
- App consumers must call evaluation services intentionally rather than triggering evaluation as an implicit side effect.
- Trajectory evaluation must remain a thin explicit `evo` adapter rather than a custom local metric implementation.
- Evaluation logic must remain separate from method wrappers, dataset adapters, and pipeline orchestration.

## Explicit Non-Goals

- Defining benchmark policy for the full project.
- Reimplementing `evo` or a full SLAM-metrics framework inside this package.
- Owning app state, Streamlit rendering, or page-local selection widgets.
- Owning dataset normalization, method execution, or pipeline-stage planning.
- Hiding missing references, malformed trajectories, or unsupported evaluation cases behind silent fallbacks.

## Validation

- A persisted run with matching reference and estimate TUM trajectories can be discovered, evaluated explicitly, and reloaded deterministically.
- Selection changes in the app do not trigger evaluation implicitly.
- The README and requirements stay honest about the current thin local scope.
- The file stays aligned with the shared section structure used by the other existing `REQUIREMENTS.md` files.
