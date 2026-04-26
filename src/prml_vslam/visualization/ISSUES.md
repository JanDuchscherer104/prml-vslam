# Visualization Issues

This file captures active visualization/viewer-facing issues distilled from the
recent Rerun debugging discussion. It is intentionally concise and focused on
the user-visible failures rather than implementation detail.

## Conversation Provenance And Query Handles

Use these sources to recover the full discussion history behind this issue.

### Exported session artifacts

- User export:
  `codex-session-019d9b63-user-messages.md`
- Agent export:
  `codex-session-019d9b63-agent-messages.md`

### Raw Codex session metadata for the exported files

- Session id:
  `019d9b63-1bd9-7201-8373-d9555874798d`
- Thread title:
  `Fix rerun point cloud regression`
- Raw session JSONL:
  `/home/jandu/.codex/sessions/2026/04/17/rollout-2026-04-17T14-20-57-019d9b63-1bd9-7201-8373-d9555874798d.jsonl`

### Repo-local MemPalace

- Palace path:
  `.artifacts/mempalace/palace`
- Wrapper script:
  `python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py`

Useful commands:

```bash
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py refresh
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py status
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py search "rerun coordinate frame point cloud origin world camera local"
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py search "diag 1 -1 -1 rerun vista viewer pose basis flip"
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py search "world ViewCoordinates RDF pointmap transport ParentFromChild ChildFromParent"
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py search "sticky keyframe timeline rerun live keyframe pointmap"
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py search "run_live sliding window frusta cam_0 cam_1 world/est"
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py search "world live camera cam world est pointmaps camera local geometry"
```

### File-level anchors for this issue

- Current repo-owned sink policy:
  `src/prml_vslam/pipeline/sinks/rerun_policy.py`
- Current repo-owned Rerun helper / blueprint:
  `src/prml_vslam/visualization/rerun.py`
- Current visualization requirements:
  `src/prml_vslam/visualization/REQUIREMENTS.md`
- Current visualization issue log:
  `src/prml_vslam/visualization/ISSUES.md`
- Upstream live reference:
  `external/vista-slam/run_live.py`

## User-Reported Issues

This section contains only the issues explicitly pointed out by the user.

1. Point clouds are not being projected into the correct world coordinates and
  instead appear clustered near the global origin.
2. Point clouds are being displayed as if they were still in camera/local
  coordinates instead of as a stable world-space map.
3. New point clouds overwrite previously visible point clouds instead of
  accumulating persistently.
4. The viewer can end up no longer showing any persistent point cloud at all.
5. No entities are being persisted under `/world/keyframes/points`.
6. In some runs, only keyframe frusta are visible.
7. A ViSTA-style sliding-window approach is desired for frusta visibility, so
  only a bounded recent set of frusta remains visible.
8. The points under the keyed history path can be empty.

## Current Point-Cloud Issue

The repo-owned Rerun viewer still does not present a stable accumulated map in
the same way that ViSTA-SLAM live does.

Observed failure modes:

- Point clouds have appeared camera-local or clustered near the global origin
  instead of reading as a stable world-space map.
- New visible point clouds have overwritten previous visible geometry instead
  of accumulating.
- After hiding the mutable live/model cloud, the default 3D scene has shown no
  persistent point cloud at all, sometimes leaving only keyframe frusta.

## Distilled Recent Findings

## Current Discrepancy Matrix

| Area | Status | Classification | Notes |
| --- | --- | --- | --- |
| Upstream crop/resize preprocessing parity | Confirmed | intentional difference | No basis drift originates in preprocessing; the wrapper preserves upstream ingest semantics. |
| Source RGB vs ViSTA model raster | Different surfaces | documentation gap | `world/live/source/rgb` is source-frame only, while model RGB/depth/pointmap/intrinsics live on the ViSTA raster. |
| Live pointmap vs exported `pointcloud.ply` | Different products | documentation gap | Live path is scaled camera-local; export path is fused world-space geometry. |
| Repo entity layout vs upstream `world/est/cam_n` layout | Different layout | intentional difference | Path/layout parity is not required if composed world placement is equivalent. |
| ViSTA-native RDF-like world semantics in repo viewer | Confirmed | documentation gap | Current screenshots are consistent with preserved ViSTA-native semantics, not a repo world-up convention. |
| Root-world basis remap in repo-owned Rerun path | Not present | confirmed equivalence | Repo path keeps a neutral root and no root `ViewCoordinates`, matching upstream intent. |
| Keyed point persistence vs frusta eviction | Guarded | confirmed equivalence | Current sink keeps points and clears only stale keyed camera branches. |
| Offline preserved native visualization vs repo-owned live `.rrd` | Different product surface | intentional difference | Offline repo-owned `.rrd` synthesis remains out of scope in the current design. |

### 1. The problem is not only transform math

The failure is a combination of:

- how point clouds are attached in the entity tree
- how persistence is represented
- what the default 3D blueprint actually renders

Even when synthetic recording-level parity tests pass, the user-visible scene
can still be wrong if the blueprint selects the wrong branches.

### 2. ViSTA live uses a different persistence model

`external/vista-slam/run_live.py` keeps recent views visible by logging each
camera and point cloud under a stable per-view topic such as `world/est/cam_0`,
`world/est/cam_1`, etc. It relies on:

- unique entity paths
- a bounded recent-view window
- no separate keyed-history timeline for persistent visibility

This differs from the repo-owned split layout of:

- `world/live/source`
- `world/live/tracking`
- `world/live/model`
- `world/keyframes/...`

### 3. Persistent map geometry and frusta need different policies

The desired viewer behavior is:

- point clouds persist and accumulate into a world map
- frusta do not persist forever
- frusta use a sliding window like ViSTA live

That means map history and frusta history must not share the same persistence
policy.

### 4. Sliding-window frusta are an explicit requirement

The viewer should adopt ViSTA live’s sliding-window idea for visible frusta.
Older frusta should disappear from the default scene, while historical point
cloud geometry remains available as the persistent map surface.

## Current Confirmed Runtime Observation

From the actual viewer/debug state, the important distinction is:

- `world/live/model/points` has arrived in some runs.
- `/world/keyframes/points/...` has also failed to appear in some runs.

That means the remaining issue is not only blueprint selection. The real
runtime can still fail to emit the persistent keyed-history point-cloud branch
at all, leaving the viewer with either:

- only the mutable live/model cloud,
- only keyed frusta,
- or no persistent point cloud surface.

For the screenshot axis complaint specifically, the current agreed reading is:

- the scene behaves like a ViSTA-native RDF-like world
- that is consistent with the chosen repo-owned viewer policy
- therefore the remaining work is to keep repo logging semantically aligned
  with upstream ViSTA and make that policy explicit, not to normalize the
  viewer into a world-up convention in this pass

## Historical / Recurrent Visualization Issues

These are the previously identified point-cloud and coordinate-frame issues that
have recurred across iterations of the Rerun work:

1. Wrong transform relation for repo poses.
   - Repo `T_world_camera` poses were previously logged with
     `ChildFromParent` instead of `ParentFromChild`, which can invert world
     placement.

2. Viewer-only basis flip in the ViSTA path.
   - Earlier versions coupled visualization to a `diag([1, -1, -1])`-style
     viewer remap / viewer-pose hook instead of preserving ViSTA-native world
     semantics.

3. Root-world convention mismatch.
   - Different iterations alternated between:
     - forcing `world` to `ViewCoordinates.RDF`
     - using a neutral identity root transform
     - leaving the root entirely implicit
   - This repeatedly obscured whether the real bug was world-basis policy or
     scene-graph composition.

4. Dropped pointmap transport.
   - During the Ray/event-first refactor, the explicit dense pointmap payload
     was at one point dropped or ignored, so the sink lost the actual geometry
     path that older working versions had.

5. Loss of the posed pointmap composition path.
   - Older working versions composed camera-local pointmaps through explicit
     posed entities like `world/live/pointmap` and `world/est/pointmaps/...`.
   - Later refactors changed the layout and made it harder to verify that
     point-cloud world placement still matched the intended parent transform.

6. Sticky keyframe timeline contamination.
   - At one stage, `set_time("keyframe", ...)` leaked into later live logs and
     mixed current/live geometry semantics with historical keyed semantics.

7. Persistence model mismatch with ViSTA live.
   - ViSTA live keeps recent history visible via stable per-view entity paths.
   - The repo has repeatedly mixed:
     - mutable live geometry,
     - keyed history,
     - and timeline-scoped history
     without matching ViSTA’s user-visible persistence model.

8. Camera-path misunderstanding.
   - The real requirement is not that points must be logged under the image
     plane (`.../cam`), but that they must be logged under the correct posed
     parent/view entity so camera-local geometry is composed correctly.

9. Raster/intrinsics consistency drift.
   - `Pinhole`, RGB, depth, and pointmap payloads must all refer to the same
     ViSTA-sized raster assumptions. Mixing capture-resolution intrinsics with
     ViSTA-resolution geometry is invalid.

10. Diagnostic preview semantics drift.
   - The pseudo-colored pointmap preview must remain a diagnostic image only,
     not a substitute for RGB or metric depth.

## What We Tried And The Effects

### A. Restored pointmap transport through the Ray/event path

Effect:

- point clouds re-entered the repo-owned Rerun path
- but the visible scene was still wrong

### B. Fixed sticky timeline handling

Effect:

- live/keyed logging contamination was reduced
- but the main map/frusta behavior still did not match ViSTA live

### C. Preserved ViSTA/native world semantics

Effect:

- removed viewer-only root-world remap
- added a neutral root `world` transform
- made semantics cleaner
- but this alone did not solve persistent map visibility

### D. Added recording-level parity tests against a minimal ViSTA-style reference

Effect:

- synthetic recordings can be made internally consistent
- but this did not guarantee the default 3D scene showed the correct branches

### E. Switched the default 3D scene away from `world/live/model/points`

Effect:

- stopped the obvious visible overwrite behavior from the mutable live cloud
- but the scene then risked showing no persistent point cloud

### F. Split keyed history into separate camera and point subtrees

Effect:

- the blueprint can now target historical point clouds without also pulling in
  keyed frusta
- this is closer to the intended ViSTA-like user-visible behavior
- sliding-window frusta are still a separate follow-up requirement

### G. Switched keyed history from one mixed subtree to separate
`keyframes/cameras` and `keyframes/points`

Effect:

- keyed frusta and keyed point clouds are no longer forced to share the same
  blueprint query branch
- the default 3D scene can now ask for historical points without also
  explicitly including keyed camera branches
- this does not by itself guarantee that the real runtime is actually
  persisting `/world/keyframes/points/...`

## Functional Comparison Matrix

| Capability                         | ViSTA `run_live.py`                               | Repo-owned viewer path                                           | Functional equivalence |
| ---------------------------------- | ------------------------------------------------- | ---------------------------------------------------------------- | ---------------------- |
| Root world declaration             | Neutral `/world` identity `Transform3D()`         | Neutral `world` identity `Transform3D()`                         | Equivalent intent      |
| Root `ViewCoordinates` basis       | None                                              | Static root `world=RDF` declaration                              | Intentional difference |
| Camera basis on `Pinhole`          | `camera_xyz=RDF`                                  | `camera_xyz=RDF`                                                 | Equivalent             |
| Pose relation semantics            | Raw `Transform3D(...)` defaults on posed parent   | Explicit `ParentFromChild` for repo `T_world_camera`             | Intended equivalent    |
| Point cloud frame                  | Camera-local                                      | Camera-local                                                     | Equivalent             |
| Point cloud placement              | Inherits posed parent transform                   | Inherits posed parent transform                                  | Intended equivalent    |
| Persistent visibility model        | Stable per-view topics (`cam_0`, `cam_1`, …)      | Split live/model + keyed-history layout                          | Not equivalent         |
| History timeline dependence        | No separate history timeline in live path         | Iterated between keyed-history timeline and stable untimed paths | Not equivalent         |
| Sliding-window frusta              | Yes                                               | Not implemented yet                                              | Not equivalent         |
| Persistent point-cloud history     | Yes, via stable view topics                       | Still unstable / still being debugged                            | Not equivalent         |
| Preview semantics                  | Can overwrite visible image with pointmap preview | Preview kept separate from RGB                                   | Different by design    |
| Explicit `DepthImage` in live path | No                                                | Yes                                                              | Different by design    |

## Design / Interaction Matrix

This matrix compares concrete Rerun interactions and viewer-design decisions
between the current repo-owned implementation and ViSTA live.

| Area                              | ViSTA `run_live.py` behavior                                                         | Repo-owned behavior                                                                                   | Equivalent?               | Why it matters                                                                                           |
| --------------------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- | ------------------------- | -------------------------------------------------------------------------------------------------------- |
| Recording init                    | `rr.init(...)`, optional save/connect, then `rr.log("/world", rr.Transform3D())`     | Explicit `RecordingStream`, sinks, blueprint, then neutral `world` identity transform                 | Mostly yes                | Both declare a neutral root scene without a viewer-only world-basis remap.                               |
| Root `ViewCoordinates`            | Not logged                                                                           | Not logged on the ViSTA-aligned path                                                                  | Yes                       | Avoids introducing a viewer-only basis conversion at the root.                                           |
| World basis normalization         | None in the live Rerun path                                                          | None in the live ViSTA-aligned path; root RDF only informs viewer interpretation                     | Yes                       | Keeps the viewer from silently changing upstream world semantics while aligning the viewer grid to the scene. |
| Pose logging path                 | `world/est/{topic}`                                                                  | `world/live/tracking/camera`, `world/live/model`, `world/keyframes/...`                               | No                        | Repo uses a split semantic tree instead of one per-view path.                                            |
| Camera model path                 | `world/est/{topic}/cam`                                                              | `.../camera/image` or keyed camera subtree `.../image`                                                | No                        | Same concept, different path structure.                                                                  |
| Point cloud path                  | `world/est/{topic}/points`                                                           | `world/live/model/points` and `world/keyframes/points/<id>/points`                                    | No                        | Repo separates live/debug and keyed-history geometry.                                                    |
| Image path                        | RGB/image logged on the camera entity                                                | RGB logged on `.../camera/image` or keyed `.../image`                                                 | Conceptually yes          | The image stays on the same entity as the pinhole.                                                       |
| Preview image handling            | Can replace the camera image with pointmap preview                                   | Separate preview branch `.../diag/preview`                                                            | No                        | Repo keeps preview semantically separate, which is cleaner.                                              |
| Metric depth logging              | Not logged in live path                                                              | Logged as `DepthImage`                                                                                | No                        | Repo exposes more modalities, but also adds more moving parts.                                           |
| Camera basis declaration          | `camera_xyz=RDF`                                                                     | `camera_xyz=RDF`                                                                                      | Yes                       | This should stay aligned.                                                                                |
| Point cloud coordinate frame      | Camera-local                                                                         | Camera-local                                                                                          | Yes                       | In both systems, world placement should come from the parent transform, not pre-transforming the points. |
| Point cloud filtering             | Filters valid points with `z > 0` through the mask/path that builds `pts`            | Helper filters points with `z > 0` and finite depth before logging                                    | Yes                       | Empty point clouds can still happen if all points fail this filter.                                      |
| Point size / radii                | `radii=0.002`                                                                        | repo helper default `POINT_CLOUD_RADII`                                                               | Intentionally aligned now | Important for visibility; too-large radii can visually smear geometry.                                   |
| History persistence               | Stable per-view topics in a bounded recent window                                    | Stable keyed-history entities plus separate live/model branch                                         | Partially                 | Repo is now trying to separate persistent map history from latest/debug geometry.                        |
| Sliding-window frusta             | Yes, via reused topics like `cam_0`, `cam_1`, ...                                    | Not yet implemented                                                                                   | No                        | This is still a missing feature explicitly requested by the user.                                        |
| Timeline use in live path         | No meaningful active history timeline (`rr.set_time("index", ...)` is commented out) | Explicit `frame` timeline for live/source/tracking/model; keyed history moved to stable untimed paths | No                        | Repo has more explicit time semantics, but that diverges from ViSTA’s visible-history model.             |
| Persistent point-cloud visibility | Comes from stable visible topic paths                                                | Depends on keyed-history subtree emission plus blueprint selection                                    | No                        | This is the current failure surface.                                                                     |
| Live/current point cloud          | Visible as part of the recent-view window                                            | Logged under `world/live/model/points`, intended as latest/debug-only                                 | No                        | Repo separates current debug geometry from persistent history.                                           |
| Keyed camera visibility           | Visible in the recent-view window                                                    | Intended hidden by default in the main 3D scene                                                       | No                        | Repo wants historical clouds without cluttering the scene with all frusta.                               |
| Entity reuse                      | Reuses `cam_0`, `cam_1`, ... slots                                                   | Uses permanent keyed IDs plus one live/model branch                                                   | No                        | This is the clearest architectural divergence from ViSTA live.                                           |
| Viewer policy owner               | Script-local in `run_live.py`                                                        | Repo-owned helper + sink policy + blueprint                                                           | No                        | More structured, but easier to drift away from ViSTA behavior.                                           |

## Still Required

- Make the default 3D scene show persistent historical point clouds reliably.
- Add a ViSTA-style sliding-window policy for visible frusta.
- Keep `world/live/model/points` as latest/debug-only geometry, not the main
  visible map.
- Verify the real runtime event stream, not just synthetic recordings, emits the
  point-cloud branches needed for the default scene.
