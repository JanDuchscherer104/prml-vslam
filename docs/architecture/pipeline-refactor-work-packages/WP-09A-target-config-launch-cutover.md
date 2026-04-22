# WP-09A Target Config Launch Cutover

Status: Draft

Owner: Unassigned

Dependencies:
- WP-00A Baseline Acceptance
- WP-02 Config Planning
- WP-02B Target Config Completion
- WP-04 Source Runtime
- WP-05 Bounded Runtimes
- WP-06 SLAM Runtime Live Updates

Decision:
- No backward compatibility is required for old `RunRequest` TOML, old stage
  keys, or old run inspection once this package starts. Preserve behavior only
  where it belongs to the target `RunConfig` launch path.

Owned paths:
- `src/prml_vslam/pipeline/config.py`
- `src/prml_vslam/pipeline/contracts/request.py`
- `src/prml_vslam/pipeline/contracts/plan.py`
- `src/prml_vslam/pipeline/contracts/stages.py`
- `src/prml_vslam/pipeline/stage_registry.py`
- `src/prml_vslam/pipeline/demo.py`
- `src/prml_vslam/main.py`
- `src/prml_vslam/app/pipeline_controls.py`
- `src/prml_vslam/app/pages/pipeline_request_editor.py`
- `.configs/pipelines/`
- config and launch tests under `tests/`

Read-only context paths:
- `docs/architecture/pipeline-stage-refactor-target.md`
- `docs/architecture/pipeline-dto-migration-ledger.md`
- `src/prml_vslam/pipeline/stages/*/config.py`
- `src/prml_vslam/pipeline/runtime_manager.py`
- `src/prml_vslam/methods/configs.py`
- `src/prml_vslam/datasets/`
- `src/prml_vslam/io/`

Target architecture sections:
- `RunConfig Stage Bundle And Plan Compilation`
- `Target Config Shape`
- `Stage Matrix`
- `DTO Simplification Targets`

Goal:
- Make `RunConfig` with `[stages.*]` sections the only launch and planning
  contract for app, CLI, and backend submission.
- Remove old request/config compatibility objects after all callers construct
  or load `RunConfig` directly.

Out of scope:
- Rewriting runtime execution away from `RuntimeStageProgram`.
- Removing live telemetry events or old snapshot fields.
- New source, SLAM, evaluation, or reconstruction features.

Implementation notes:
- Replace `load_run_request_toml()` with a `RunConfig` loader that fails on
  legacy top-level `[source]` / `[slam]` request shapes.
- Replace `RunService.start_run(request=...)` and `PipelineBackend.submit_run(request=...)`
  with `RunConfig` or `RunPlan` oriented APIs. Do not keep adapter overloads
  that accept `RunRequest`.
- Complete `StageBundle` with stage-specific configs:
  `SourceStageConfig`, target SLAM stage config, bounded stage configs,
  reconstruction config, and summary config.
- Compile `RunConfig -> RunPlan` directly. Do not delegate through
  `RunRequest.build()`.
- Replace current executable stage keys with target public keys:
  `source`, `align.ground`, `evaluate.trajectory`, `reconstruction`,
  `evaluate.cloud`, and `evaluate.efficiency`.
- Remove alias maps such as `CURRENT_TO_TARGET_STAGE_KEYS` only after every
  stage registry, plan, runtime, app, CLI, manifest, and test call site uses the
  target stage vocabulary.
- Migrate committed pipeline TOML files into the target shape in this package.
  Do not leave mixed legacy/target examples.
- Delete `RunRequest`, `SourceSpec`, `VideoSourceSpec`, `DatasetSourceSpec`,
  `Record3DLiveSourceSpec`, `SlamStageConfig` under `contracts.request`,
  `StagePlacement`, `PlacementPolicy`, `RayRuntimeConfig`,
  `RunRuntimeConfig`, `StageDefinition`, and `StageAvailability` only after
  stale-symbol greps are clean outside historical docs.

DTO migration scope:
- Own final deletion or rehome for `RunRequest`, `SourceSpec`,
  request source variants, current request `SlamStageConfig`,
  `StagePlacement`, `PlacementPolicy`, `RayRuntimeConfig`,
  `RunRuntimeConfig`, `StageDefinition`, `StageAvailability`, and current
  stage-key aliases.
- Keep method backend configs, dataset serving configs, benchmark configs,
  visualization configs, and reconstruction backend configs with their domain
  owners.

Termination criteria:
- `RunConfig.from_toml()` parses all committed pipeline configs.
- App and CLI launch only through `RunConfig`.
- `RunPlan` contains only target stage keys.
- `RunRequest` and request source variants have no production imports.
- Stage-key alias greps are clean outside historical docs and this package's
  completion notes.
- Old config compatibility paths are deleted, not shimmed.

Required checks:
- `uv run prml-vslam plan-run-config .configs/pipelines/vista-full.toml`
- `uv run pytest tests/test_pipeline_config.py tests/test_main.py tests/test_app.py`
- stale-symbol greps for `RunRequest`, `SourceSpec`, `StagePlacement`,
  `PlacementPolicy`, `StageDefinition`, `StageAvailability`, `ingest`,
  `ground.align`, `trajectory.evaluate`, and `reference.reconstruct`
- `make lint`
- `git diff --check`

Known risks:
- Leaving `RunRequest` adapters in place will keep the old source/backend
  contract alive and block WP-10.
- Changing stage keys without migrating summaries, manifests, and app display
  logic will make new runs inconsistent.
