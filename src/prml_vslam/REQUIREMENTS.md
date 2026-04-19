# PRML VSLAM Package Requirements

## Purpose

This document is the concise source of truth for the top-level package architecture in `src/prml_vslam/`.

Use this file for package-root ownership rules and cross-package contract constraints. Use package-local `README.md` or `REQUIREMENTS.md` files for deeper, package-specific explanations. Streamlit app requirements live in [`app/REQUIREMENTS.md`](./app/REQUIREMENTS.md), not here. Human-facing minimal-public-surface and migration rationale live in [`../../docs/architecture/interfaces-and-contracts.md`](../../docs/architecture/interfaces-and-contracts.md).

## Current State

- The repository already has stable top-level package slices: `app`, `datasets`, `eval`, `interfaces`, `io`, `methods`, `pipeline`, `plotting`, `protocols`, and `utils`.
- This file is the current canonical location for top-level module ownership and cross-package contract placement rules.
- Package-local `README.md` and `REQUIREMENTS.md` files already carry the deeper package-level guidance.
- The current architecture is typed and artifact-first, with offline benchmark execution as the core and bounded live streaming around it.

## Target State

- Keep top-level package ownership and cross-package contract placement rules centralized in this file.
- Keep package-local `README.md` files explanatory and package-local `REQUIREMENTS.md` files concise and normative.
- Keep one semantic concept attached to one owning module or namespace.
- Keep the app as a launch and monitoring surface rather than a second pipeline implementation.

## Responsibilities

- `app`
  - owns Streamlit pages, typed page state (`prml_vslam.app.models`), UI composition, and launch surfaces
  - does not own pipeline semantics, transport decoding, dataset normalization, or benchmark-policy logic
- `datasets`
  - owns dataset catalogs, dataset-facing contracts, fetch/extract flows, and normalization into repository contracts
  - does not own evaluation policy or method-specific execution
- `eval`
  - owns explicit evaluation logic and typed evaluation contracts
  - does not own method execution, source normalization, or app state
- `interfaces`
  - owns repo-wide shared datamodels only
  - examples include `CameraIntrinsics`, `FrameTransform`, and `FramePacket`
- `benchmark`
  - owns thin benchmark-policy composition such as evaluation enablement and baseline selection
- `visualization`
  - owns viewer policy, preserved native viewer artifacts, and the repo-owned Rerun integration layer
- `io`
  - owns transport adapters, packet ingestion, replay mechanics, and transport-level normalization
  - does not own app session state or benchmark policy
- `methods`
  - owns backend-specific execution seams and thin method-wrapper integration
  - `prml_vslam.methods.protocols` owns package-local SLAM behavior seams such as `SlamBackend` and `SlamSession`
  - does not own pipeline planning or evaluation policy
- `pipeline`
  - owns orchestration, run contracts, artifact layout, stage planning, events,
    projected snapshots, manifests, summaries, one SLAM-stage config and one
    SLAM artifact bundle per backend, pipeline-owned Ray coordination, and
    repo-local execution-lifecycle policy on `RunRequest`
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
- Promote a type into `prml_vslam.interfaces.*` only when multiple top-level packages import it and the semantics are truly identical across those packages.
- Shared repo-wide datamodels belong in `prml_vslam.interfaces.*`.
- Shared repo-wide behavior seams belong in `prml_vslam.protocols.*`.
- `prml_vslam.protocols.runtime` owns `FramePacketStream`.
- `prml_vslam.protocols.source` owns shared source-provider seams such as `OfflineSequenceSource` and `StreamingSequenceSource`.
- Package-local DTOs, configs, manifests, requests, and results belong in `<package>/contracts.py` or
  `<package>/contracts/` when a package owns several distinct contract slices.
- Package-local `Protocol` seams belong in `<package>/protocols.py` when a package truly owns that behavior boundary.
- `prml_vslam.methods.protocols` owns `SlamBackend` and `SlamSession`.
- `prml_vslam.app.models` owns Streamlit-only UI and session state.
- `services.py` modules own implementations only; they must not become the home of public contract types.
- The app must stay a launch and monitoring surface rather than a second pipeline implementation.
- The pipeline owns one SLAM-stage request and one SLAM artifact bundle per backend; backend-private config and output
  policy belong in `methods`.
- The pipeline owns public runtime events, projected snapshots, stage registry
  semantics, and backend placement policy; Ray-specific refs and mailboxes stay
  backend-private.
- External-method wrappers must stay thin and normalize into repo-owned pipeline artifacts instead of inventing parallel public result shapes.
- Record3D live pipeline requests must use a transport-aware typed source contract instead of encoding USB or Wi-Fi details into ad hoc `source_id` strings alone.
- `PathConfig` remains the single owner of repo-owned path semantics.

## Explicit Non-Goals

- This file is not the home for app UX requirements.
- This file is not a package-by-package implementation guide.
- This file must not duplicate package-local architecture notes that already belong in lower-level docs.
- This file must not become a second copy of the human-facing minimal-public-surface and migration rationale from [`docs/architecture/interfaces-and-contracts.md`](../../docs/architecture/interfaces-and-contracts.md).

## Validation

- It stays consistent with [`docs/architecture/interfaces-and-contracts.md`](../../docs/architecture/interfaces-and-contracts.md).
- It gives one clear answer to “which top-level package owns this concern?”
- It does not restate package-local requirements that already belong in lower package docs.
- It stays aligned with the shared section structure used by the other existing `REQUIREMENTS.md` files.
