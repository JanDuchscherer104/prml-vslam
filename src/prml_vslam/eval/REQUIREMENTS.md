# Eval Requirements

This document defines the intended responsibilities and boundaries for
`prml_vslam.eval`.

## Summary

The `eval` package owns the repository-local evaluation surface used by the app
and tests. Its current scope is intentionally small: discover available runs,
resolve reference and estimate trajectory artifacts, compute and persist a
deterministic local trajectory-comparison result, and expose typed evaluation
contracts to downstream consumers.

The package does not currently own a full benchmark-policy implementation or a
complete `evo` integration.

## Necessary Requirements

- The package must own typed evaluation controls, result payloads, discovery
  DTOs, and plotting-facing data contracts.
- The package must discover repository-local runs from normalized artifact
  layouts rather than from app-local path heuristics.
- The package must resolve reference and estimate trajectories explicitly and
  fail clearly when required artifacts are missing.
- The package must persist evaluation results in a deterministic, reloadable
  repository-owned format.
- The package must keep evaluation execution explicit. App consumers must call
  evaluation services intentionally rather than triggering evaluation as an
  implicit side effect of selection changes.
- The package must remain compatible with the current lightweight local
  trajectory-delta mock used by the app and tests until the project explicitly
  expands the evaluation scope.
- The package must keep evaluation logic separate from method wrappers,
  dataset adapters, and pipeline orchestration.

## Nice To Have

- A thin adapter to `evo` that preserves the same typed contracts and explicit
  execution semantics.
- Additional typed evaluation surfaces for dense-cloud and efficiency metrics
  once those artifact contracts stabilize elsewhere in the repo.
- Provenance metadata that records how an evaluation result was produced,
  including alignment flags, scale-correction settings, and source artifact
  paths.
- Small helper utilities for comparing persisted evaluation results across runs
  without pushing selection logic into the app layer.

## Non-Goals

- Defining benchmark policy for the full project.
- Reimplementing `evo` or a complete SLAM-metrics framework inside this
  package.
- Owning app state, Streamlit rendering, or page-local selection widgets.
- Owning dataset normalization, method execution, or pipeline-stage planning.
- Hiding missing references, malformed trajectories, or unsupported evaluation
  cases behind silent fallbacks.
