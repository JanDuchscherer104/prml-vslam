# Methods Requirements

## Purpose

This document is the concise source of truth for the `prml_vslam.methods` package.

## Current State

- `prml_vslam.methods` is currently a mock interface layer used by the app and tests.
- The package already owns typed method selection enums, shared SLAM behavior seams in `methods/protocols.py`, one repository-local mock backend config, deterministic mock offline and streaming runtimes, and local path bookkeeping for mock installs.
- The package does not yet ship real ViSTA-SLAM or MASt3R-SLAM orchestration in the current codebase.

## Target State

- Keep method integration thin and wrapper-oriented rather than reimplementing upstream SLAM systems locally.
- The first real wrapper targets should remain ViSTA-SLAM and MASt3R-SLAM.
- Real wrappers should consume repo-owned inputs, call upstream entry points, validate native outputs, and normalize them into pipeline-owned artifacts.

## Responsibilities

- The package owns method selection, SLAM backend and session seams, thin method-wrapper integration, and repository-local mock execution surfaces.

## Non-Negotiable Requirements

- Backend selection must use a shared typed enum.
- Shared SLAM behavior seams must live in `methods/protocols.py`.
- Offline-capable backends must expose `run_sequence(sequence, cfg, artifact_root) -> SlamArtifacts`.
- Streaming-capable backends must expose `start_session(cfg, artifact_root) -> SlamSession`.
- Shared method inputs must stay repository-friendly and method-agnostic: `SequenceManifest`, `SlamConfig`, and `artifact_root`.
- Shared outputs must normalize method-specific artifacts into the same downstream trajectory and geometry paths.
- Shared upstream state should live under `.logs/` for checkouts, checkpoints, and dedicated method environments.
- Missing repositories, configs, checkpoints, or expected native outputs must fail clearly.

## Explicit Non-Goals

- Reimplementing ViSTA-SLAM or MASt3R-SLAM internals.
- Hiding upstream installation complexity behind silent fallbacks.
- Defining evaluation metrics or benchmark policy inside this package.

## Validation

- New method work continues to normalize outputs into pipeline-owned artifacts instead of inventing parallel public result types.
- The file stays aligned with the shared section structure used by the other existing `REQUIREMENTS.md` files.
