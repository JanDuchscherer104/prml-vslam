# Interfaces And Contracts

This note is the human-facing architecture guide for the repository's interface and contract restructuring. [`src/prml_vslam/REQUIREMENTS.md`](../../src/prml_vslam/REQUIREMENTS.md) is the canonical source for top-level package ownership and cross-package contract placement rules. This document owns the minimal public surface to preserve, the wrapper-normalization rationale, and the incremental migration rules.

`.agents/references/agent_reference.md` remains the compact lookup-only reference sheet for library IDs and upstream sources.

## Current State

- `prml_vslam.interfaces` already contains the canonical shared data models: `CameraIntrinsics`, `SE3Pose`, and `FramePacket`.
- Trajectory objects now use `PoseTrajectory3D` from `evo.core.trajectory` directly instead of a repository-owned trajectory wrapper.
- `prml_vslam.protocols.runtime` now defines the shared `FramePacketStream` protocol, so repo-wide datamodel and shared protocol layers are separated in code.
- `prml_vslam.protocols.source` now defines the shared `OfflineSequenceSource` and `StreamingSequenceSource` seams used across dataset adapters and pipeline orchestration.
- Package DTO, enum, config, manifest, request, and result types now live in `src/prml_vslam/methods/contracts.py`, `src/prml_vslam/datasets/contracts.py`, `src/prml_vslam/eval/contracts.py`, and `src/prml_vslam/pipeline/contracts.py`.
- `src/prml_vslam/methods/protocols.py` now defines the currently implemented SLAM backend and session seams, while `src/prml_vslam/pipeline/contracts.py` defines the planner surface, artifact bundles, stage manifests, and `SlamUpdate`.
- Method-local mocks now emit pipeline-owned `SlamArtifacts` directly, so the normalized trajectory and point-cloud boundary stays owned by the pipeline instead of a parallel method-local result type.
- The repo previously duplicated contract-reference guidance across the compact agent reference, enforcement-oriented agent instructions, and package-level documentation. That overlap made it too easy for current-state facts and target-state naming to drift, so top-level ownership rules now live in `src/prml_vslam/REQUIREMENTS.md` and this note carries the shared public-surface and migration rationale.

## Canonical Split

- Use [`src/prml_vslam/REQUIREMENTS.md`](../../src/prml_vslam/REQUIREMENTS.md) as the canonical human-facing source for top-level package ownership and cross-package contract placement rules.
- Use this document as the canonical human-facing source for the shared minimal public surface, migration rules, and wrapper-normalization rationale.
- Keep [`.agents/references/agent_reference.md`](../../.agents/references/agent_reference.md) lookup-only.

## Minimal Public Surfaces

The repo should preserve a deliberately small public surface during and after the restructuring.

- Shared datamodels: `CameraIntrinsics`, `SE3Pose`, `FramePacket`
- Pipeline data: `RunRequest`, `RunPlan`, `SequenceManifest`, `SlamArtifacts`, `RunSummary`
- Behavior seams: `SlamBackend`, `SlamSession`
- Method selector: `MethodId`

All other types are package-local unless they are later promoted under the shared-type rule.

The `prml_vslam.io` and `prml_vslam.pipeline` package roots now match this minimal surface. New root-level re-exports should be treated as deliberate API additions rather than migration defaults.

## Migration Rules

- This restructuring is incremental even after the first namespace sweep.
- The shared protocol namespace and the first package `contracts.py` and `protocols.py` owners now exist, but not every package needs both files.
- New work should follow the target naming immediately.
- Do not reintroduce mixed `interfaces.py` owner modules for new work.
- If a package later needs a new behavior seam, add it to `<package>/protocols.py` instead of mixing it into a DTO module.
- Preserve the minimal public surface while migrating. Temporary re-exports are acceptable only when they are explicitly intentional, documented, and have a clear removal plan.
- Do not create parallel public result shapes when a pipeline-owned artifact contract already exists.
- Wrapper-private transport payloads, native CLI argument objects, and upstream-native debug outputs should stay private unless they satisfy the shared-type rule.

## Upstream Method-Wrapper Implications

- ViSTA-SLAM exposes an image-glob plus config plus output-dir offline seam. The wrapper should consume repo-owned inputs, materialize image folders through pipeline or workspace helpers when needed, invoke the upstream CLI, validate the native artifacts, and normalize them into repo-owned outputs.
- MASt3R-SLAM exposes a dataset, video, or folder input plus config and optional calibration. The wrapper should map `SequenceManifest` into the native shape required for that run, pass calibration only when available, and normalize the resulting trajectory and point cloud into the same repo-owned artifact boundary.
- The pipeline owns one SLAM-stage config and one SLAM artifact bundle per backend; dense output remains a capability of that stage rather than a second backend contract.
- Because those upstream seams are materially different, the repository should not mirror either upstream CLI as a shared public interface.
- Upstream live-camera or preview modes should not become repo-wide streaming interfaces. They remain wrapper-private unless later work proves a true shared protocol that belongs to the repository rather than to one upstream backend.
- Wrapper outputs should converge on pipeline-owned artifacts instead of inventing parallel public result types for each method.
