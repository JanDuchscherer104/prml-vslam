# PRML VSLAM Pipeline Requirements

## Purpose

This file is the concise source of truth for the `prml_vslam.pipeline` package.

## Current State

- `prml_vslam.pipeline` now owns run/artifact/provenance contracts through an
  internal `contracts/` package rather than one monolithic `contracts.py`.
- The package exposes a true offline path and a streaming path through
  `OfflineRunner`, `StreamingRunner`, and `RunService`.
- The current executable slice remains `ingest`, `slam`, and `summary`.

## Responsibilities

- own run requests, plans, manifests, artifacts, runner snapshots, and summary
  persistence
- own offline canonical ingest and execution orchestration
- remain separate from benchmark policy, evaluation execution, app state, and
  method-wrapper internals

## Non-Negotiable Requirements

- `SequenceManifest` remains the normalized offline boundary.
- Large outputs stay materialized as durable artifacts.
- Offline ingest must stay source-faithful and method-agnostic.
- `prml_vslam.pipeline` is the curated public API; `pipeline/contracts/` is not
  a compatibility import hub.
- The package must not re-export method protocols through the pipeline root.
- The executable slice must remain linear and deterministic.

## Validation

- planning remains deterministic
- offline runs no longer require injected packet streams
- streaming runs still surface truthful packet/session telemetry
- stage manifests and run summaries remain explicit and durable
