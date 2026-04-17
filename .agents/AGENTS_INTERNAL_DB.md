# AGENTS Internal Database

Purpose: a compact, repository-local alignment database for stable project facts, ownership boundaries, configuration policy, and current technical context. Add highly important facts here that are not discoverable or easily inferred from the current repo state, and that should be included in the canonical agent guidance as per [AGENTS.md](../AGENTS.md) and nested `AGENTS.md` files. This file is for operational memory, not for new policy or detailed implementation notes that should live in package `README.md` or `REQUIREMENTS.md` files.

This file is operational memory, not a replacement for the full repo-wide policy in [../AGENTS.md](../AGENTS.md) or the maintenance workflow in [skills/agents-db-and-simplification/SKILL.md](skills/agents-db-and-simplification/SKILL.md).

## Mission Snapshot

- Build the repository-owned scaffold for an off-device monocular VSLAM benchmark on smartphone video or streams with unknown intrinsics.
- Keep artifact boundaries typed and explicit.
- Treat the Streamlit workbench as an inspection and bounded-demo surface, not the owner of core pipeline semantics.

## Configuration Policy

- `BaseConfig` is the repo-owned config-as-factory base.
- TOML is the preferred persisted configuration surface for repo-owned `BaseConfig` derivatives.
- Use:
  - `BaseConfig.from_toml()` to hydrate persisted configs
  - `BaseConfig.to_toml()` and `save_toml()` to emit repo-owned configs
  - `PathConfig.resolve_toml_path()` for repo-relative TOML files
- Inline construction of `BaseConfig` graphs is acceptable for focused tests, tiny examples, and short-lived local helpers, but durable CLI, app, and benchmark workflows should converge on TOML inputs.

## Stable Ownership Snapshot

- `prml_vslam.interfaces.*` owns canonical shared datamodels.
- `prml_vslam.protocols.*` owns shared protocol seams such as `FramePacketStream`.
- `app` owns Streamlit-only state and rendering concerns.
- `io` owns transport and packet ingestion, not app session snapshots.
- `pipeline` owns planning, normalized run contracts, event-projected snapshots, and Ray-backed run coordination.

## Current Stable Facts

- `BaseConfig` already supports TOML IO in `src/prml_vslam/utils/base_config.py`.
- `PathConfig.resolve_toml_path()` already exists and should anchor repo relative config resolution.
- The active pipeline runtime surface is `prml_vslam.pipeline.run_service.RunService` over the repo-owned `PipelineBackend` and current `RayPipelineBackend`, not app-owned orchestration.
- `prml_vslam.app` still uses `prml_vslam.utils.packet_session` for Record3D preview/runtime helpers, but the pipeline orchestration path is no longer built on that packet-session utility.
- The current repo-owned live Rerun path after the pipeline refactor is `src/prml_vslam/pipeline/sinks/rerun.py` fed by `prml_vslam.methods.events.translate_slam_update(...)`; the older direct viewer path in `pipeline/streaming_coordinator.py` is useful historical context but is no longer the primary sink surface.
- Upstream ViSTA's own Rerun integration in `external/vista-slam/run.py` and `run_live.py` logs raw `Transform3D(translation=pose[:3,3], mat3x3=pose[:3,:3])`, uses `Pinhole(..., camera_xyz=rr.ViewCoordinates.RDF)`, and logs camera-local `Points3D` under the posed camera entity. It does not apply a viewer-only basis flip or a root Y-up world declaration in the Rerun path.
- The older viewer-only remap `diag([1,-1,-1])` plus a root Y-up world existed in the older `bd39b4c` streaming path, but not in the later `b5731e6` / `55afaeb` behavior that was treated as the "working" post-fix state. Do not confuse those two historical states when debugging Rerun regressions.
- The stable lessons from the Rerun regression work are:
  - preserve upstream-style ViSTA frame preprocessing via `SLAM_image_only.process_image()` semantics before sending frames into `OnlineSLAM`
  - log poses with parent-from-child semantics for repo `T_world_camera`
  - keep the live Rerun root world declared as `ViewCoordinates.RDF`
  - do not enable the live `DepthImage` cloud by default when debugging geometry, because it adds a second auto-backprojected 3D cloud that obscures whether the explicit pointmap branch is correct
- The current sink semantics intentionally separate `world/live/camera` from `world/live/pointmap` and `world/est/cameras/*` from `world/est/pointmaps/*` so camera frusta can be hidden without hiding points. This is a repo-owned viewer usability choice and is not identical to upstream ViSTA's single-branch Rerun layout.
