# Methods Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.methods`.

## Current State

- The package owns method IDs, backend config, output policy, runtime updates,
  the placeholder MASt3R backend, and the canonical ViSTA backend integration.
- `method_id` is the canonical discriminator for SLAM method variants.
- `SlamUpdate` and `BackendEvent` are method-owned and belong in `methods.contracts`.
- Method protocols no longer depend on pipeline-owned config models.
- `methods.vista` owns ViSTA-native artifact interpretation and standardization.

## Responsibilities

- define backend-private config and output policy
- define runtime session/update seams
- implement thin wrappers that consume normalized repo-owned inputs and produce
  normalized pipeline-owned artifacts
- convert method-native outputs into typed camera and geometry artifacts

## Non-Negotiable Requirements

- missing repos, configs, checkpoints, or expected native outputs must fail
  clearly
- wrappers must stay thin and importer-oriented
- upstream-native outputs may be preserved, but normalized artifacts remain the
  repo contract
- method code must not own stage policy or viewer orchestration
- method backends consume normalized `Observation` iterables in offline mode;
  source manifest dematerialization belongs to source/stage helpers
- `methods.vista` must persist ViSTA preprocessing metadata needed to know
  that estimated intrinsics live in the 224x224 model raster
- Estimated-intrinsics standardization (e.g., `CameraIntrinsicsSeries`) belongs
  to the package that understands the native raster semantics
