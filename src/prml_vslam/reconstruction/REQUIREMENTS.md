# Reconstruction Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.reconstruction`.

## Current State

- The package owns reconstruction backends (e.g., Open3D TSDF) and mode variants.
- The pipeline exposes the single `reconstruction` umbrella stage; reference,
  3DGS, and future reconstruction methods are backend/mode variants under that
  umbrella.
- `ReconstructionArtifacts` and `ReconstructionMetadata` are the canonical outputs.
- The repository currently pins `open3d>=0.19.0,<0.20`.

## Responsibilities

- own reconstruction backend IDs (`method_id`) and reconstruction-private config variants
- own reconstruction artifact DTOs and consume shared RGB-D observation DTOs
- own typed backend configs and protocol seams that switch between
  reconstruction methods
- own thin library-backed reconstruction adapters
- stay separate from stage policy, benchmark reference identifiers, pipeline
  orchestration, and Rerun logging policy

## Non-Negotiable Requirements

- the reconstruction umbrella stage handles all variants (reference/3DGS/future);
  do not add separate public stage keys for each reconstruction flavor
- the package must provide one elegant method-selection seam, analogous to
  `prml_vslam.methods`, instead of scattering method switches through pipeline
  code
- `ReconstructionRuntime` selects the deployment target (in-process vs Ray-hosted)
  based on the backend's resource needs (e.g., GPU for 3DGS)
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
- the first executable reconstruction method must be a minimal Open3D TSDF
  backend based on `ScalableTSDFVolume`
- the public execution seam must stay minimal and offline-first until a real
  streaming reconstruction use case exists

## Validation

- one Open3D TSDF implementation can consume typed reconstruction observations
  and produce the normalized `reference_cloud.ply`
- adding a future second reconstruction method requires touching the config
  union and protocol implementation, not widening the pipeline contract
- DTOs remain usable by the existing Rerun sink without introducing
  reconstruction-owned viewer types
- target stage keys are used without reconstruction stage-key aliases
