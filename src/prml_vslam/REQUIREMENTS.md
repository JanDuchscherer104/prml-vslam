# PRML VSLAM Package Requirements

## Purpose

This document is the concise source of truth for the top-level package architecture in `src/prml_vslam/`.

Use this file for package-root ownership rules and cross-package constraints. Use package-local `README.md` or `REQUIREMENTS.md` files for deeper, package-specific explanations. Streamlit app requirements live in [`app/REQUIREMENTS.md`](./app/REQUIREMENTS.md), not here.

## Current State

- The repository already has stable top-level package slices: `app`, `datasets`, `eval`, `interfaces`, `io`, `methods`, `pipeline`, `plotting`, `protocols`, and `utils`.
- This file is the current canonical location for top-level module ownership.
- Package-local `README.md` and `REQUIREMENTS.md` files already carry the deeper package-level guidance.
- The current architecture is typed and artifact-first, with offline benchmark execution as the core and bounded live streaming around it.

## Target State

- Keep top-level package ownership centralized in this file.
- Keep package-local `README.md` files explanatory and package-local `REQUIREMENTS.md` files concise and normative.
- Keep one semantic concept attached to one owning module or namespace.
- Keep the app as a launch and monitoring surface rather than a second pipeline implementation.

## Responsibilities

- `app`
  - owns Streamlit pages, typed page state, UI composition, and launch surfaces
  - does not own pipeline semantics, transport decoding, dataset normalization, or benchmark-policy logic
- `datasets`
  - owns dataset catalogs, dataset-facing contracts, fetch/extract flows, and normalization into repository contracts
  - does not own evaluation policy or method-specific execution
- `eval`
  - owns explicit evaluation logic and typed evaluation contracts
  - does not own method execution, source normalization, or app state
- `interfaces`
  - owns repo-wide shared datamodels only
  - examples include `CameraIntrinsics`, `SE3Pose`, and `FramePacket`
- `io`
  - owns transport adapters, packet ingestion, replay mechanics, and transport-level normalization
  - does not own app session state or benchmark policy
- `methods`
  - owns backend-specific execution seams and thin method-wrapper integration
  - does not own pipeline planning or evaluation policy
- `pipeline`
  - owns orchestration, run contracts, artifact layout, stage planning, manifests, summaries, and pipeline-owned session/runtime coordination
  - does not own transport decoding, app rendering, or benchmark metrics logic
- `plotting`
  - owns reusable figure construction helpers
  - does not own orchestration or domain-policy decisions
- `protocols`
  - owns repo-wide shared behavior seams only
  - examples include `FramePacketStream`, `OfflineSequenceSource`, and `StreamingSequenceSource`
- `utils`
  - owns shared low-level infrastructure such as config helpers, path handling, logging, and generic geometry/runtime helpers
  - does not own package-specific workflow policy

## Non-Negotiable Requirements

- One semantic concept must have one owning module.
- Shared repo-wide datamodels belong in `prml_vslam.interfaces.*`.
- Shared repo-wide behavior seams belong in `prml_vslam.protocols.*`.
- Package-local DTOs, configs, manifests, requests, and results belong in `<package>/contracts.py`.
- Package-local `Protocol` seams belong in `<package>/protocols.py` when a package truly owns that behavior boundary.
- `services.py` modules own implementations only; they must not become the home of public contract types.
- The app must stay a launch and monitoring surface rather than a second pipeline implementation.
- External-method wrappers must stay thin and normalize into repo-owned pipeline artifacts instead of inventing parallel public result shapes.
- `PathConfig` remains the single owner of repo-owned path semantics.

## Explicit Non-Goals

- This file is not the home for app UX requirements.
- This file is not a package-by-package implementation guide.
- This file must not duplicate package-local architecture notes that already belong in lower-level docs.
- This file must not become a second copy of the human-facing ownership rationale from [`docs/architecture/interfaces-and-contracts.md`](../docs/architecture/interfaces-and-contracts.md).

## Validation

- It stays consistent with [`docs/architecture/interfaces-and-contracts.md`](../docs/architecture/interfaces-and-contracts.md).
- It gives one clear answer to “which top-level package owns this concern?”
- It does not restate package-local requirements that already belong in lower package docs.
- It stays aligned with the shared section structure used by the other existing `REQUIREMENTS.md` files.
