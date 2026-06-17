# Sources Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.sources`.

## Current State

- The package owns dataset catalogs, sequence materialization, prepared reference
  identifiers, and source-normalization boundaries.
- `source_id` is the canonical discriminator for source variants.
- `sources.stage.SourceRuntime` owns source config/factory parity and normalized
  `SequenceManifest` preparation.
- `frame_stride` and `target_fps` are shared source backend policy fields.

## Responsibilities

- own dataset-specific loading and normalization (ADVIO, TUM RGB-D)
- own live transport adapters (Record3D)
- own prepared benchmark references (ground-truth trajectories)
- implement thin wrappers that consume raw sequences or live observations and produce
  normalized repository-owned observations

## Non-Negotiable Requirements

- `SequenceManifest` remains the normalized offline boundary.
- Source preparation must stay source-faithful and method-agnostic.
- `dataset_serving` remains ADVIO-owned because it selects ADVIO pose provider
  and frame semantics; it is not promoted to the common source backend base.
- Source reading, source credits, and transport state remain internal sidecars
  or collaborators; they are not public stages.
- Only one sampling mode (stride or FPS) may be active at once.
- Offline RGB payload loading is source-configured. `load_rgb=false` may emit
  provenance-preserving observation shells while leaving normalized RGB paths in
  the `SequenceManifest` for path-native backends.
- Missing datasets or corrupted manifests must fail clearly.
- Offline `SequenceManifest` dematerialization into RGB `Observation` values is
  source-owned and must not live in method backends.

## Validation

- dataset replay uses timestamp-aware stride selection
- raw video uses frame extraction policy
- live Record3D treats sampling as best-effort observation filtering before the SLAM hot path
- Prepared benchmark inputs include the requested trajectory baseline (ground truth)
  and source-owned reference clouds when a dataset provides enough RGB-D/depth
  geometry to materialize one without method-specific reconstruction.
- TUM RGB-D benchmark prep emits a bounded aligned reference cloud from
  registered metric depth and ground-truth RGB-camera poses when depth is
  available.
- TUM RGB-D benchmark outputs (trajectory, reference cloud, observation poses)
  are expressed in the first-camera RDF frame (`tum_rgbd_world`), relativized to
  the first ground-truth pose per the VISTA `loadtum` convention; the raw mocap
  Z-up frame is retained only as `native_frame` provenance.
