# Visualization Debugging

Use this document when a recording looks wrong in Rerun and you need to decide
whether the problem is:

- in the scene graph,
- in the logged payload semantics,
- in the viewer layout, or
- in the current artifact bundle.

## Validation Bundle

Generate a deterministic validation bundle from one repo-owned recording:

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

Use it when you need a stable, non-interactive snapshot of the recording.

## `.rrd` Inspection Workflow

For ad hoc recording inspection, prefer the helper scripts described in the
Rerun skill:

- [$mempalace:rerun-slam-integration](../../../.agents/skills/rerun-slam-integration/SKILL.md)

Useful entry points:

- `rrd_entity_inventory.py`
  - fast schema-level entity/component inventory
- `rrd_component_arrivals.py`
  - first/last populated rows for selected components on one entity query
- `rrd_chunk_order.py`
  - storage-order view using `rerun rrd print`
- `run_event_timeline.py`
  - companion parser for `summary/run-events.jsonl`

Example commands:

```bash
uv run --extra vista python .agents/skills/rerun-slam-integration/scripts/rrd_entity_inventory.py \
  .artifacts/<run_id>/visualization/viewer_recording.rrd \
  --prefix /world/live
```

```bash
uv run --extra vista python .agents/skills/rerun-slam-integration/scripts/rrd_component_arrivals.py \
  .artifacts/<run_id>/visualization/viewer_recording.rrd \
  --index frame \
  --contents /world/live/model/camera/image \
  --component-substring Image \
  --component-substring Pinhole \
  --component-substring DepthImage
```

```bash
uv run --extra vista python .agents/skills/rerun-slam-integration/scripts/rrd_chunk_order.py \
  .artifacts/<run_id>/visualization/viewer_recording.rrd \
  --match /world/live/model/camera/image
```

## Companion Artifacts

The current artifact bundle usually gives you three independent views of one
run:

- `visualization/viewer_recording.rrd`
  - repo-owned viewer artifact
- `summary/run-events.jsonl`
  - run event log emitted by the pipeline
- `native/`
  - preserved backend-native outputs

Important caveat:

- `summary/run-events.jsonl` currently contains durable run/stage summary
  events. It is useful for run lifecycle correlation, but it does not currently
  guarantee observation-level source / pose-estimate / keyframe notice
  timing for every run.

## Questions To Ask First

When a viewer rendering looks wrong, answer these in order:

1. Which entity paths actually exist in the `.rrd`?
2. Which components exist on those entities?
3. On the suspicious entity, does `Pinhole` arrive before or after `Image`?
4. Are the transforms and payloads on the same frame timeline rows?
5. Is the payload camera-local geometry or world-space geometry?
6. Is the 2D view using the intended entity, or is it reusing a 3D camera
   entity?
7. Is the current artifact bundle fresh, or are you looking at a stale
   recording from a previous run?

## Viewer Hygiene

Current implementation details that matter during debugging:

- the repo-owned file sink now replaces an existing `viewer_recording.rrd`
  before writing a new run;
- the root `world` entity is the only intentionally visible axes marker;
- the 2D “Model RGB” view uses `world/live/model/diag/rgb`, not the 3D
  camera-image entity;
- the 3D camera-image entity should only receive image/depth payloads when a
  coherent `Pinhole` is also present.
