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
- Each backend must be represented by a typed config object that follows the
  repository `BaseConfig` factory pattern.
- Each backend runtime must expose one shared inference surface.
- Shared inference inputs must be repository-friendly and method-agnostic:
  source capture path, artifact root, frame stride, and display mode.
- Shared inference outputs must normalize method-specific artifacts into the
  same downstream paths for trajectory and reconstructed geometry.

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
  folder for debugging and for launching the upstream viewer when possible.
- ViSTA-SLAM trajectory exports must be converted from upstream `trajectory.npy`
  into TUM text using capture timestamps when they are available.
- MASt3R-SLAM trajectory exports should be copied from the upstream text format
  into the normalized trajectory path.

## Visualization Requirements

- The package must provide one repository-owned visualization path that works
  across both methods.
- Plotly is the default repository-owned visualization surface for normalized
  results.
- Open3D should be available for an idiomatic local 3D scene viewer.
- When an upstream repository already provides a native viewer, the wrapper
  must expose that capability through notes or a native viewer command instead
  of searching for a third-party replacement.
- A Nerfstudio integration is out of scope for this package unless a later task
  explicitly asks for scene-representation integration beyond SLAM output
  inspection.

## Non-Goals

- Reimplementing ViSTA-SLAM or MASt3R-SLAM internals.
- Hiding upstream installation complexity behind silent fallbacks.
- Guaranteeing CPU-only execution when the upstream methods are designed and
  documented around GPU inference.
- Defining evaluation metrics or benchmark policy; those belong in `eval` and
  higher-level pipeline orchestration.
