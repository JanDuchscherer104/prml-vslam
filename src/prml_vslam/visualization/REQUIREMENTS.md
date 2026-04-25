# Visualization Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.visualization`.

## Current State

- repo-owned Rerun live export exists for streaming runs
- offline runs currently preserve upstream-native visualization artifacts but do not synthesize a repo-owned offline `.rrd`
- the current repo-owned stream logs:
  - aligned reference clouds
  - original source RGB under `world/live/source/rgb`
  - live tracking and model transforms plus keyed historical transforms
  - trajectory polylines plus optional per-pose SE3 axes
  - `rr.Pinhole` camera models
  - model-raster RGB camera images
  - metric `rr.DepthImage` payloads
  - per-keyframe pointmaps as `rr.Points3D`
  - one diagnostic preview image per keyframe
- source RGB and model-raster payloads are intentionally separate surfaces and
  are not expected to share a raster
- the default 3D scene should render aligned reference geometry,
  keyed-history point clouds from `world/keyframes/points/<id>/points`, recent
  keyed camera/frusta entities, trajectory lines, and optional per-pose axes
- the default 3D scene should use a narrow allow-list and treat
  `world/live/model/points`, source-native references, and camera image/depth
  raster branches as non-default debug/2D surfaces
- keyed-history persistence in the viewer should come from stable entity paths rather than requiring a dedicated keyframe timeline
- the streaming repo-owned sink should keep only the newest configured window of keyed camera/frusta entities visible
- the current repo-owned stream does not yet log a world-space fused dense cloud separate from per-keyframe pointmaps
- the current ViSTA preview payload is a colorized pointmap preview, not raw RGB and not metric depth
- the repo-owned transform export now uses parent-from-child semantics for repo `T_world_camera` poses
- the ViSTA live pointmap path returns scaled camera-local geometry, while
  exported `pointcloud.ply` is a separate world-space fused artifact
- missing or empty keyframe pointmaps should surface a backend warning instead of silently disappearing


## Responsibilities

- own viewer policy and typed visualization artifacts
- own the thin repo-owned Rerun wrapper
- preserve upstream-native `.rrd` files when requested
- export repo-owned `.rrd` files from repo-owned contracts when enabled
- stay separate from Streamlit widgets, runner orchestration, and method math
- keep the repo-owned live sink on a fixed minimal output surface rather than a growing per-modality configuration API
- accept visualization policy knobs for streaming frusta windowing, trajectory
  visibility, and trajectory pose axis length

## Required Frame Conventions

- repo camera poses use world <- camera (`T_world_camera`)
- frame-labelled transforms crossing into visualization must keep explicit source
  and target frame names
- the live ViSTA-aligned viewer path must preserve upstream ViSTA world orientation instead of applying a viewer-only basis remap
- the ViSTA-aligned sink should declare `world` with a neutral identity `rr.Transform3D(axis_length=1.0)` plus a static root `rr.ViewCoordinates.RDF` so the viewer grid/axes match ViSTA-native RDF semantics without rotating the data
- `rr.Pinhole.image_from_camera` uses row-major intrinsics with `X = Right`, `Y = Down`, `Z = Forward`
- camera entities should use `camera_xyz = rr.ViewCoordinates.RDF` unless a different camera basis is explicitly documented
- method-native live exports should keep their native world semantics unless a dedicated normalization layer is introduced
- `rr.Pinhole.resolution` is `[width, height]`
- metric depth rasters use `rr.DepthImage`; if the array is in meters, `meter = 1.0`
- camera-local pointmaps remain camera-local until composed through the posed parent entity for the active layout, such as `world/live/model` or `world/keyframes/points/<id>`
- the repo-owned ViSTA path preserves ViSTA-native RDF-like world semantics in
  the viewer path; it does not normalize the world into an operator/world-up
  basis

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

- visualization must not own Streamlit widgets, session state, or runner orchestration
- repo-owned `.rrd` export must be generated from repo-owned contracts, not by transcoding upstream-native viewer state
- preserved upstream `.rrd` files must remain separate artifacts
- pseudo-colored pointmap previews must never be labeled as depth
- a repo `T_world_camera` transform logged to Rerun must use parent-from-child semantics or an explicitly inverted matrix; `ChildFromParent` is invalid unless the matrix is inverted first
- if the layout uses dedicated pointmap transform branches, those transform entities should suppress visible frame axes, for example by logging `axis_length=0`
- ViSTA-specific viewer hooks must not add an extra world-basis conversion on top of the upstream pose stream
- intrinsics, images, depth, and pointmaps logged for one camera must refer to the same raster resolution and crop
- `world/live/source/rgb` is intentionally the source-frame raster and must not
  be relabeled as the ViSTA model raster
- camera-local pointmaps must not be mislabeled as world coordinates
- frusta eviction must never clear `world/keyframes/points/<id>` or the tracking trajectory branch
- per-pose trajectory axis entities are omitted by default; set a positive
  `trajectory_pose_axis_length` only when visible SE3 axes are explicitly needed
- missing keyed pointmaps are non-fatal observability events and must emit explicit warnings with `source_seq` and `keyframe_index`
- exported world-space dense clouds such as native `pointcloud.ply` must not be
  treated as interchangeable with live camera-local pointmap payloads

## Validation

- one synthetic camera-plus-depth case round-trips correctly through the Rerun
  scene tree
- per-keyframe points align with the corresponding camera frustum and image
  plane
- the trajectory polyline grows across pose updates without truncating keyed
  point history; optional per-pose axes are emitted only when explicitly enabled
- after `N + 1` keyed camera logs, only the oldest keyed camera subtree is cleared while all keyed point subtrees remain
- prepared references are logged under type-first paths:
  `world/reference/trajectory/<source>/<status>` and
  `world/reference/points/<source>/<status>/...`
- docs and code stay aligned with the pinned `rerun-sdk==0.24.1`
