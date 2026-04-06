# Methods Requirements

This document defines the intended responsibilities and boundaries for
`prml_vslam.methods`.

## Scope

The `methods` package integrates external monocular VSLAM systems into this
repository without reimplementing the underlying SLAM algorithms.

The current scope covers two upstream backends:

- ViSTA-SLAM
- MASt3R-SLAM

The package owns the shared interface layer that lets the rest of this project
switch between these backends through one typed selector.

## Core Requirements

- Backend selection must use a shared `StrEnum`.
- Shared SLAM behavior seams must live in `methods/protocols.py`.
- Offline-capable backends must expose
  `run_sequence(sequence, cfg, artifact_root) -> SlamArtifacts`.
- Streaming-capable backends must expose
  `start_session(cfg, artifact_root) -> SlamSession`.
- Shared method inputs must be repository-friendly and method-agnostic:
  `SequenceManifest`, `SlamConfig`, and `artifact_root`.
- Shared outputs must normalize method-specific artifacts into the same
  downstream paths for trajectory and reconstructed geometry.
- Repository-local mock coverage should converge on one mock SLAM backend
  surface, not parallel generic mock runtimes.

## Upstream Integration Requirements

- The package must call the upstream repositories through their native entry
  points instead of vendoring or rewriting them.
- Shared upstream state must live under `.logs/`:
  - `.logs/repos/<repo-name>` for upstream checkouts
  - `.logs/ckpts/<method>` for shared checkpoints and weights
  - `.logs/venvs/<method>` for dedicated backend environments synced from this
    repository's `pyproject.toml`
- The package must make the upstream command, working directory, and expected
  output paths explicit.
- Integration must raise clear errors when the upstream repository, config, or
  expected output artifacts are missing.
- Method wrappers must document method-specific prerequisites such as
  checkpoints or vocabulary files in returned notes.
- Backend dependency sets may be encoded as conflicting `uv` extras when the
  upstream stacks cannot coexist in one Python environment.

## Input Normalization Requirements

- ViSTA-SLAM must be able to consume project-owned video captures by decoding
  them into an image sequence, because the upstream interface expects image
  globs.
- The package must persist a capture manifest whenever it materializes an image
  sequence for downstream timestamp lookup and debugging.
- MASt3R-SLAM must support its native video or image-folder dataset interface.

## Output Normalization Requirements

- The shared trajectory artifact must be a TUM-style text file.
- The shared dense geometry artifact must be a PLY point cloud.
- Method-specific raw outputs should remain available under a native output
  folder for debugging.
- ViSTA-SLAM trajectory exports must be converted from upstream `trajectory.npy`
  into TUM text using capture timestamps when they are available.
- MASt3R-SLAM trajectory exports should be copied from the upstream text format
  into the normalized trajectory path.

## Non-Goals

- Reimplementing ViSTA-SLAM or MASt3R-SLAM internals.
- Hiding upstream installation complexity behind silent fallbacks.
- Guaranteeing CPU-only execution when the upstream methods are designed and
  documented around GPU inference.
- Defining evaluation metrics or benchmark policy; those belong in `eval` and
  higher-level pipeline orchestration.
