# PRML VSLAM Pipeline Requirements

## Purpose

This document is the concise source of truth for the pipeline package architecture in `src/prml_vslam/pipeline/`.

Use [README.md](./README.md) for the fuller explanation of contracts, runtime flow, artifacts, and TOML semantics. Use [`../REQUIREMENTS.md`](../REQUIREMENTS.md) for top-level package ownership rules. This file is only for pipeline-local architecture constraints.

## Current State

- `prml_vslam.pipeline` is currently a typed planning layer plus a bounded runnable slice.
- [`contracts.py`](./contracts.py) owns the current pipeline DTOs and payload bundles, including `RunRequest`, `RunPlan`, `SequenceManifest`, `ArtifactRef`, `SlamArtifacts`, `StageManifest`, `RunSummary`, and `SlamUpdate`.
- [`services.py`](./services.py) owns planning through `RunPlannerService`.
- [`workspace.py`](./workspace.py) owns capture-manifest helpers such as `CaptureManifest`.
- [`demo.py`](./demo.py) owns request-template helpers only. It is not the runtime.
- [`run_service.py`](./run_service.py) and [`session.py`](./session.py) own the bounded executable runtime that the app and CLI currently launch.
- The current executable stage subset is `ingest`, `slam`, and `summary`.
- Reference and evaluation stages are already plannable, but they are not yet executable in the bounded runtime.
- The current bounded runtime uses the streaming execution seam even for the demo's offline single-pass replay mode.
- Record3D live runs can already be planned and launched through `Record3DLiveSourceSpec` and `Record3DStreamingSourceConfig` for both `USB` and `Wi-Fi Preview`.
- The live Record3D path still only materializes `SequenceManifest(sequence_id=...)` from `prepare_sequence_manifest(...)`, so full manifest convergence at the live boundary remains partial today.

## Target State

- Offline execution remains the architectural core and streaming remains a bounded runtime surface around it.
- The runtime should converge on a real `OfflineRunner` and a real `StreamingRunner` fronted by pipeline-owned services.
- All sources should converge on a richer `SequenceManifest` boundary before downstream benchmark stages run.
- Stage outputs should stay typed and artifact-first through `ArtifactRef`-backed bundles such as `SlamArtifacts`.

## Responsibilities

- The package owns orchestration, run contracts, artifact layout, stage planning, stage provenance, summaries, and the bounded executable runtime.
- The package owns pipeline DTOs, manifests, and artifact bundles in [`contracts.py`](./contracts.py).
- The package consumes shared `FramePacket` and `FramePacketStream` runtime seams plus shared `SlamBackend` and `SlamSession` behavior seams, but it does not own those shared namespaces.
- The package does not own transport decoding, app rendering, benchmark metrics logic, or backend-specific wrapper logic.

## Non-Negotiable Requirements

- Stage selection must remain typed, ordered, and deterministic.
- Every major boundary must use typed contracts.
- Large outputs must be materialized as durable artifacts instead of moving as large in-memory payloads.
- Stage provenance must remain explicit through stage manifests and run summaries.
- Artifact paths must stay deterministic and owned by `PathConfig` and `RunArtifactPaths`.
- `ArtifactRef` and `SlamArtifacts` must remain the current concrete payload contracts for pipeline stage outputs.
- Shared `FramePacket` objects may cross the live ingress boundary, but later stages should consume manifests and artifact bundles instead of live packets.
- Only the live ingress path may justify a bounded queue.
- Offline mode must not become queue-driven inter-stage plumbing.
- The app and CLI must not redefine pipeline semantics; they should launch or preview pipeline work through pipeline-owned services.
- `BenchmarkEvaluationConfig` must clearly separate trajectory evaluation enablement (via `evaluate_trajectory`) from optional baseline selections (such as `compare_to_arcore`).

## Explicit Non-Goals

- A generic workflow framework or graph engine.
- Browser or UI concerns inside `pipeline/`.
- Queue-driven offline stage plumbing.
- Duplicating `methods/` or `eval/` ownership under `pipeline/`.
- Hidden fallback behavior that blurs artifact or contract boundaries.

## Validation

- It stays consistent with [README.md](./README.md) and the current code in `contracts.py`, `services.py`, `run_service.py`, `session.py`, and `../io/record3d_source.py`.
- It clearly separates current executable behavior from target architecture.
- It keeps top-level ownership rules in [`../REQUIREMENTS.md`](../REQUIREMENTS.md) instead of restating them here.
- It documents both implemented Record3D transports and their current capability asymmetry truthfully.
- It keeps the partial live `SequenceManifest` materialization explicit.
- It stays aligned with the shared section structure used by the other existing `REQUIREMENTS.md` files.
