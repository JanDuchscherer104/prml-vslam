# Interfaces And Contracts

This note is the human-facing architecture guide for the repository's interface
and contract restructuring. It consolidates the current repo findings, the
target ownership model, the minimal public surface to preserve, and the
incremental migration rules.

`.agents/references/agent_reference.md` remains the compact agent lookup and
reference sheet. This document carries the full rationale and migration model.

## Current State

- `prml_vslam.interfaces` already owns the canonical shared data models:
  `CameraIntrinsics`, `SE3Pose`, `TimedPoseTrajectory`, and `FramePacket`.
- `prml_vslam.protocols.runtime` now owns the shared `FramePacketStream`
  protocol, so repo-wide datamodel ownership and shared protocol ownership are
  separated in code.
- Package DTO, enum, config, manifest, request, and result ownership now lives
  in `src/prml_vslam/methods/contracts.py`,
  `src/prml_vslam/datasets/contracts.py`,
  `src/prml_vslam/eval/contracts.py`, and
  `src/prml_vslam/pipeline/contracts.py`.
- `src/prml_vslam/pipeline/protocols.py` now owns the currently implemented
  pipeline behavior seams, while `src/prml_vslam/pipeline/contracts.py` owns
  the planner surface, artifact bundles, stage manifests, and
  `SlamUpdate`.
- Method-local mocks now emit pipeline-owned `SlamArtifacts` directly, so the
  normalized trajectory and point-cloud boundary stays owned by the pipeline
  instead of a parallel method-local result type.
- The repo scan found overlapping contract-reference guidance across the
  compact agent reference, enforcement-oriented agent instructions, and
  package-level documentation. That overlap made it too easy for current-state
  facts and target-state naming to drift, so this note becomes the
  human-facing source for the full rationale.

## Target State

The repository should converge on the following ownership and naming rules.
These rules describe the intended steady state. Some parts are now implemented
in code, while others remain conventions for future work.

- `prml_vslam.interfaces.*` owns repo-wide canonical shared datamodels only.
- `prml_vslam.protocols.*` owns repo-wide shared protocols only.
- `<package>/contracts.py` owns package DTOs, enums, configs, manifests,
  requests, and results.
- `<package>/protocols.py` is the preferred module for package-local
  `Protocol` seams when a package needs them.
- `prml_vslam.app.models` owns Streamlit-only UI and session state.
- `services.py` modules own implementations only. They do not own public
  contract types.

One semantic concept should have one owning module. A type should be promoted
into `prml_vslam.interfaces.*` only when multiple top-level packages import it
and the semantics are truly identical across those packages.

## Minimal Public Surfaces

The repo should preserve a deliberately small public surface during and after
the restructuring.

- Shared datamodels:
  `CameraIntrinsics`, `SE3Pose`, `TimedPoseTrajectory`, `FramePacket`
- Pipeline data:
  `RunRequest`, `RunPlan`, `SequenceManifest`, `SlamArtifacts`,
  `RunSummary`
- Behavior seams:
  `SlamBackend`, `SlamSession`
- Method selector:
  `MethodId`

All other types are package-local unless they are later promoted under the
shared-type rule.

The `prml_vslam.io` and `prml_vslam.pipeline` package roots now match this
minimal surface. New root-level re-exports should be treated as deliberate API
additions rather than migration defaults.

## Migration Rules

- This restructuring is incremental even after the first namespace sweep.
- The shared protocol namespace and the first package `contracts.py` and
  `protocols.py` owners now exist, but not every package needs both files.
- New work should follow the target naming immediately.
- Do not reintroduce mixed `interfaces.py` owner modules for new work.
- If a package later needs a new behavior seam, add it to
  `<package>/protocols.py` instead of mixing it into a DTO module.
- Preserve the minimal public surface while migrating. Temporary re-exports are
  acceptable only when they are explicitly intentional, documented, and have a
  clear removal plan.
- Do not create parallel public result shapes when a pipeline-owned artifact
  contract already exists.
- Wrapper-private transport payloads, native CLI argument objects, and
  upstream-native debug outputs should stay private unless they satisfy the
  shared-type rule.

## Upstream Method-Wrapper Implications

- ViSTA-SLAM exposes an image-glob plus config plus output-dir offline seam.
  The wrapper should consume repo-owned inputs, materialize image folders
  through pipeline or workspace helpers when needed, invoke the upstream CLI,
  validate the native artifacts, and normalize them into repo-owned outputs.
- MASt3R-SLAM exposes a dataset, video, or folder input plus config and
  optional calibration. The wrapper should map `SequenceManifest` into the
  native shape required for that run, pass calibration only when available, and
  normalize the resulting trajectory and point cloud into the same repo-owned
  artifact boundary.
- Because those upstream seams are materially different, the repository should
  not mirror either upstream CLI as a shared public interface.
- Upstream live-camera or preview modes should not become repo-wide streaming
  interfaces. They remain wrapper-private unless later work proves a true
  shared protocol that belongs to the repository rather than to one upstream
  backend.
- Wrapper outputs should converge on pipeline-owned artifacts instead of
  inventing parallel public result types for each method.
