# Reconstruction Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.reconstruction`.

## Current State

- the package exists as a stub and does not yet own an executable
  reconstruction implementation
- the pipeline already reserves the stage key `reference.reconstruct`, but that
  stage remains unavailable today and is now only a migration contact for the
  target `reconstruction` umbrella stage
- the repository currently pins `open3d>=0.19.0,<0.20`

## Target State

- The target public pipeline stage is `reconstruction`; reference, 3DGS, and
  future reconstruction implementations are backend/mode variants under that
  umbrella rather than separate public stage keys.
- The pipeline stage config owns only stage lifecycle and policy. Backend
  config variants, backend ids, protocols, and reconstruction artifact
  semantics remain reconstruction-owned and are referenced by the stage config.
- `ReferenceReconstructionConfig` in `prml_vslam.benchmark` and
  `reference.reconstruct` in pipeline stage keys remain migration inputs until
  target `[stages.reconstruction]` config fully covers reference mode.

## Responsibilities

- own reconstruction backend ids and reconstruction-private config variants
- own reconstruction artifact DTOs and consume shared RGB-D observation DTOs
- own typed backend configs and protocol seams that switch between
  reconstruction methods
- own thin library-backed reconstruction adapters
- stay separate from benchmark policy, pipeline orchestration, and Rerun
  logging policy

## Non-Negotiable Requirements

- the first executable reconstruction method must be a minimal Open3D TSDF
  backend based on `ScalableTSDFVolume`
- the package must provide one elegant method-selection seam, analogous to
  `prml_vslam.methods`, instead of scattering method switches through pipeline
  code
- the public execution seam must stay minimal and offline-first until a real
  streaming reconstruction use case exists
- RGB-D DTOs crossing the package boundary must keep explicit frame semantics
  and use the repo convention `T_world_camera`
- `camera_intrinsics`, `image_rgb`, and `depth_map_m` for one observation must
  describe the same raster
- depth inputs must be metric depth in meters, not visualization products
- durable normalized output must include one world-space
  `reference_cloud.ply`; optional mesh/debug artifacts may exist but must not
  replace the public point-cloud contract
- reconstruction DTOs must stay Rerun-friendly, but the package must not log
  directly to the Rerun SDK; logging remains the responsibility of the Rerun
  sink
- the package must not introduce compatibility shims for arbitrary Open3D
  versions; implement directly against the repo-targeted Open3D API
- the package must not re-implement TSDF fusion locally while Open3D remains
  sufficient
- reconstruction stage enablement belongs to the pipeline stage config.
  Benchmark may remain a migration source for reference-mode policy until
  `[stages.reconstruction]` fully covers it.
- pipeline planning, run events, and stage execution stay in
  `prml_vslam.pipeline`

## Validation

- one Open3D TSDF implementation can consume typed reconstruction observations
  and produce the normalized `reference_cloud.ply`
- adding a future second reconstruction method requires touching the config
  union and protocol implementation, not widening the pipeline contract
- DTOs remain usable by the existing Rerun sink without introducing
  reconstruction-owned viewer types
- old `reference.reconstruct` run inspection remains compatible until the
  pipeline migration-removal package owns alias deletion
