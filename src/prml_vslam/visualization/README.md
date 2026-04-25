# Visualization

This package owns viewer/export policy plus the repo-owned Rerun integration
layer for PRML VSLAM.

It does not own Streamlit widgets, pipeline planning, or SLAM math. Rerun
recordings are viewer artifacts only. TUM trajectories, PLY clouds, manifests,
and stage summaries remain the scientific and provenance source of truth.

## Package Surface

- [`contracts.py`](./contracts.py): per-run viewer policy and visualization
  artifact contracts.
- [`rerun.py`](./rerun.py): thin helpers around the pinned
  `rerun-sdk==0.24.1` API plus native visualization-artifact collection.
- [`rerun_follow.py`](./rerun_follow.py): additive offline post-processor that
  merges a follow-enabled Rerun 0.27 blueprint into an existing `.rrd`.
- [`../pipeline/sinks/rerun.py`](../pipeline/sinks/rerun.py): event-driven
  live sink and Ray sidecar that own repo-managed recording streams.
- [`validation.py`](./validation.py): deterministic `.rrd` validation helpers
  for non-interactive inspection.
- [`REQUIREMENTS.md`](./REQUIREMENTS.md): concise package source of truth and
  invariants.
- [`RERUN_SEMANTICS.md`](./RERUN_SEMANTICS.md): frame conventions, entity
  layout, and current logging model.
- [`VISTA_NOTES.md`](./VISTA_NOTES.md): upstream ViSTA comparison notes and
  method-specific viewer behavior.
- [`DEBUGGING.md`](./DEBUGGING.md): validation flow, `.rrd` inspection, and
  package-local debugging entry points.
- [`ISSUES.md`](./ISSUES.md): active viewer-facing issue log.

## Quick Start

Install the optional Rerun dependency set:

```bash
uv sync --extra vista
```

Start the committed blueprint in a web viewer:

```bash
uv run --extra vista rerun \
  .configs/visualization/vista_blueprint.rbl \
  --serve-web
```

When using the web viewer, open:

```text
http://127.0.0.1:9090/?url=rerun%2Bhttp%3A%2F%2F127.0.0.1%3A9876%2Fproxy
```

Enable live streaming and/or repo-owned `.rrd` export in a run request:

```toml
[visualization]
connect_live_viewer = true
export_viewer_rrd = true
frusta_history_window_streaming = 20
show_tracking_trajectory = true
trajectory_pose_axis_length = 0.0
```

Set `trajectory_pose_axis_length` to a positive value only when pose axes are
needed. The default keeps dense reference trajectories as compact line strips
instead of emitting one `Transform3D` entity per TUM pose.

Inspect a persisted repo-owned recording:

```bash
uv run --extra vista rerun \
  .artifacts/<run_id>/visualization/viewer_recording.rrd \
  .configs/visualization/vista_blueprint.rbl
```

Create a follow-enabled offline artifact without changing the source `.rrd`:

```bash
uv run python -m prml_vslam.visualization.rerun_follow \
  .artifacts/<run_id>/visualization/viewer_recording.rrd
```

Generate a deterministic validation bundle:

```bash
uv run python -m prml_vslam.visualization.validation \
  .artifacts/<run_id>/visualization/viewer_recording.rrd \
  --output-dir .artifacts/<run_id>/visualization/validation
```

This writes:

- `summary.json`
- `summary.md`
- `map_xy.png`
- `map_xz.png`

## Current Logging Model

The current repo-owned live sink logs a fixed surface rather than a
per-modality toggle matrix.

- `world`: static root world convention for the viewer.
- `world/live/source/rgb`: original source-frame RGB packets.
- `world/live/tracking/camera`: live tracking pose.
- `world/live/model/diag/rgb`: dedicated 2D-only model-raster RGB surface.
- `world/live/model/camera/image`: 3D camera entity with `Pinhole`, image, and
  depth when the camera bundle is coherent.
- `world/live/model/diag/preview`: diagnostic preview surface.
- `world/live/model/points`: latest/debug camera-local pointmap surface.
- `world/keyframes/cameras/<id>` and `world/keyframes/points/<id>`: stable
  keyed-history branches.
- `world/slam/vista_slam_world/trajectory/raw`: tracking polyline.
- `world/slam/vista_slam_world/trajectory/raw/poses/<id>`: optional per-pose
  SE3 trajectory transforms when `trajectory_pose_axis_length > 0`.

Current operational constraints:

- offline runs still preserve upstream-native visualization artifacts rather
  than synthesizing a repo-owned offline `.rrd`;
- the default 3D scene is keyed-history first and treats
  `world/live/model/points` as mutable latest/debug geometry;
- live pointmaps and exported `pointcloud.ply` are different geometry products.

## Where To Read Next

- Read [`REQUIREMENTS.md`](./REQUIREMENTS.md) for the concise authoritative
  package contract.
- Read [`RERUN_SEMANTICS.md`](./RERUN_SEMANTICS.md) when changing entity paths,
  transforms, pinholes, depth, or pointmap placement.
- Read [`VISTA_NOTES.md`](./VISTA_NOTES.md) when comparing repo behavior with
  upstream ViSTA or reasoning about ViSTA-native payload semantics.
- Read [`DEBUGGING.md`](./DEBUGGING.md) when inspecting `.rrd` files or
  generating validation bundles.

## Primary External References

- Rerun Python API index:
  [ref.rerun.io/docs/python/stable/common/](https://ref.rerun.io/docs/python/stable/common/)
- Rerun blueprint APIs:
  [ref.rerun.io/docs/python/stable/common/blueprint_apis/](https://ref.rerun.io/docs/python/stable/common/blueprint_apis/)
- Repo pin:
  [`../../../pyproject.toml`](../../../pyproject.toml)

This package assumes the repo pin `rerun-sdk==0.24.1`, not an arbitrary future
Rerun release.
