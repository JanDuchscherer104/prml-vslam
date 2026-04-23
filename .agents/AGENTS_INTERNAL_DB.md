# AGENTS Internal Database

Purpose: a compact, repository-local alignment database for stable project facts, ownership boundaries, configuration policy, and current technical context. Add highly important facts here that are not discoverable or easily inferred from the current repo state, and that should be included in the canonical agent guidance as per [AGENTS.md](../AGENTS.md) and nested `AGENTS.md` files. This file is for operational memory, not for new policy or detailed implementation notes that should live in package `README.md` or `REQUIREMENTS.md` files.

This file is operational memory, not a replacement for the full repo-wide policy in [../AGENTS.md](../AGENTS.md) or the maintenance workflows in [skills/agents-db/SKILL.md](skills/agents-db/SKILL.md) and [skills/simplification/SKILL.md](skills/simplification/SKILL.md).

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
- The documentation split is intentional: root `README.md` owns project framing and high-level status, `SETUP.md` owns environment and runbook detail, `src/prml_vslam/pipeline/README.md` owns TOML planning mechanics, and `src/prml_vslam/visualization/README.md` owns Rerun usage mechanics.
- The active pipeline runtime surface is `prml_vslam.pipeline.run_service.RunService` over the repo-owned `PipelineBackend` and current `RayPipelineBackend`, not app-owned orchestration.
- The current Ray pipeline runtime no longer uses a separate supervisor actor; `RayPipelineBackend` owns named coordinator lifecycle directly, and `RunCoordinatorActor` is the single semantic runtime owner per run.
- In the current pipeline runtime, ingest materialization, trajectory evaluation, and summary projection run directly inside the coordinator through pure helpers; only the stateful or ordered execution seams remain Ray actors.
- The current pipeline request is also the authoritative streaming execution contract for ADVIO replay controls: `DatasetSourceSpec` now carries replay pose-source and video-rotation settings, and CLI `run-config`, CLI `pipeline-demo`, and Streamlit all resolve runtime sources through `build_runtime_source_from_request(...)`.
- `prml_vslam.app` still uses `prml_vslam.utils.packet_session` for Record3D preview/runtime helpers, but the pipeline orchestration path is no longer built on that packet-session utility.
- Record3D Wi-Fi is treated in this repository as a stable supported path equivalent to USB. Do not describe it in backlog or docs as preview-only, lower-fidelity, optional fallback, or non-canonical unless a concrete upstream/runtime limitation is being discussed narrowly.
- The current repo-owned live Rerun path after the pipeline refactor is `src/prml_vslam/pipeline/sinks/rerun.py` fed by `StageRuntimeUpdate.visualizations` from `SlamStageRuntime`; the older direct viewer path in `pipeline/streaming_coordinator.py` is useful historical context but is no longer the primary sink surface.
- The intended repo-local Rerun architecture is observer-sidecar based: Rerun is a sink surface, not a stage owner and not the place where the coordinator should perform coordinate normalization or hot-path visualization payload resolution.
- Upstream ViSTA's own Rerun integration in `external/vista-slam/run.py` and `run_live.py` logs raw `Transform3D(translation=pose[:3,3], mat3x3=pose[:3,:3])`, uses `Pinhole(..., camera_xyz=rr.ViewCoordinates.RDF)`, and logs camera-local `Points3D` under the posed camera entity. It does not apply a viewer-only basis flip or a root Y-up world declaration in the Rerun path.
- The older viewer-only remap `diag([1,-1,-1])` plus a root Y-up world existed in the older `bd39b4c` streaming path, but not in the later `b5731e6` / `55afaeb` behavior that was treated as the "working" post-fix state. Do not confuse those two historical states when debugging Rerun regressions.
- The stable lessons from the Rerun regression work are:
  - preserve upstream-style ViSTA frame preprocessing via `SLAM_image_only.process_image()` semantics before sending frames into `OnlineSLAM`
  - log poses with parent-from-child semantics for repo `T_world_camera`
  - preserve upstream/native ViSTA world orientation on the repo-owned sink path; use an explicit neutral root `Transform3D()` at `world` when the scene root should be declared, but do not add a viewer-only root `ViewCoordinates` remap
  - do not enable the live `DepthImage` cloud by default when debugging geometry, because it adds a second auto-backprojected 3D cloud that obscures whether the explicit pointmap branch is correct
- The current repo-owned Rerun sink no longer exposes per-modality request toggles; when enabled, it emits a fixed minimal live surface of source RGB, camera poses, keyed intrinsics/RGB/depth, pointmaps, and diagnostic previews.
- The current sink semantics use a split viewer tree of `world/live/source`, `world/live/tracking`, `world/live/model`, and `world/keyframes/{cameras,points}/<id>`. Camera-local pointmaps live at `world/keyframes/points/<id>/points` beneath a posed point-history parent while keyed camera frusta live under `world/keyframes/cameras/<id>`, which is a repo-owned divergence from upstream ViSTA's simpler `world/est/<topic>` layout.
- The default 3D blueprint should render keyed-history `world/keyframes/points/<id>/points` as the accumulated map and hide `world/live/model/points` by default; the live/model point cloud remains a latest/debug-only surface, while keyed-history persistence comes from stable untimed entity paths rather than a separate keyframe timeline.
