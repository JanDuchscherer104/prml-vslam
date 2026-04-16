# Visualization Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.visualization`.

## Current State

- repo-owned Rerun live export exists for streaming runs
- offline runs currently preserve upstream-native visualization artifacts but do
  not synthesize a repo-owned offline `.rrd`
- the current repo-owned stream logs:
  - root world coordinates
  - aligned reference clouds
  - live camera and keyframe transforms
  - per-keyframe pointmaps as `rr.Points3D`
  - one diagnostic preview image per keyframe
- the current repo-owned stream does not yet log:
  - `rr.Pinhole`
  - `rr.DepthImage`
  - trajectory polylines
  - a world-space fused dense cloud separate from per-keyframe pointmaps
- the current ViSTA preview payload is a colorized pointmap preview, not raw RGB
  and not metric depth
- the current transform export is likely incorrect because repo
  `T_world_camera` poses are emitted with
  `rr.TransformRelation.ChildFromParent`

### Current Issues

The main issue is the likely transform-relation bug: rerun.py logs repo T_world_camera poses with rr.TransformRelation.ChildFromParent, while the repo pose contract and upstream ViSTA usage imply parent-from-child semantics. The current preview_rgb coming from ViSTA is a pseudo-colored pointmap preview, not a true depth image, and that the repo currently omits rr.Pinhole, which makes frame/intrinsics debugging much harder.

## Responsibilities

- own viewer policy and typed visualization artifacts
- own the thin repo-owned Rerun wrapper
- preserve upstream-native `.rrd` files when requested
- export repo-owned `.rrd` files from repo-owned contracts when enabled
- stay separate from Streamlit widgets, runner orchestration, and method math

## Required Frame Conventions

- repo camera poses use world <- camera (`T_world_camera`)
- frame-labelled transforms crossing into visualization must keep explicit source
  and target frame names
- the root 3D scene must declare one right-handed world convention exactly once;
  the current repo standard is `rr.ViewCoordinates.RIGHT_HAND_Y_UP`
- `rr.Pinhole.image_from_camera` uses row-major intrinsics with
  `X = Right`, `Y = Down`, `Z = Forward`
- camera entities should use `camera_xyz = rr.ViewCoordinates.RDF` unless a
  different camera basis is explicitly documented
- `rr.Pinhole.resolution` is `[width, height]`
- metric depth rasters use `rr.DepthImage`; if the array is in meters,
  `meter = 1.0`
- camera-local pointmaps remain camera-local until composed through the camera
  transform in the entity tree
- left-handed coordinate systems must not be used

## Required Modalities

- aligned reference clouds in world coordinates
- keyframe camera poses
- per-keyframe camera intrinsics and frusta
- actual RGB keyframe images when available
- metric depth maps when available
- per-keyframe camera-local pointmaps and/or per-run world-space dense clouds
- trajectory visualization
- optional diagnostic previews and future BEV/operator views

## Non-Negotiable Requirements

- visualization must not own Streamlit widgets, session state, or runner
  orchestration
- repo-owned `.rrd` export must be generated from repo-owned contracts, not by
  transcoding upstream-native viewer state
- preserved upstream `.rrd` files must remain separate artifacts
- pseudo-colored pointmap previews must never be labeled as depth
- a repo `T_world_camera` transform logged to Rerun must use parent-from-child
  semantics or an explicitly inverted matrix; `ChildFromParent` is invalid
  unless the matrix is inverted first
- intrinsics, images, depth, and pointmaps logged for one camera must refer to
  the same raster resolution and crop
- camera-local pointmaps must not be mislabeled as world coordinates

## Validation

- one synthetic camera-plus-depth case round-trips correctly through the Rerun
  scene tree
- per-keyframe points align with the corresponding camera frustum and image
  plane
- aligned reference clouds only are logged under `world/reference/...`
- docs and code stay aligned with the pinned `rerun-sdk==0.24.1`
