# Reconstruction Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.reconstruction`.

## Current State

- the package exists as a stub and does not yet own an executable
  reconstruction implementation
- the pipeline already reserves the stage key `reference.reconstruct`, but that
  stage remains unavailable today
- the repository currently pins `open3d>=0.19.0,<0.20`

## Responsibilities

- own reconstruction method ids and reconstruction-private config
- own reconstruction artifact DTOs and consume shared RGB-D observation DTOs
- own the thin harness / multiplexer that switches between reconstruction
  methods
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
- benchmark stage enablement stays in `prml_vslam.benchmark`
- pipeline planning, run events, and stage execution stay in
  `prml_vslam.pipeline`

## Validation

- one Open3D TSDF implementation can consume typed reconstruction observations
  and produce the normalized `reference_cloud.ply`
- adding a future second reconstruction method requires touching the harness and
  config union, not widening the pipeline contract
- DTOs remain usable by the existing Rerun sink without introducing
  reconstruction-owned viewer types
