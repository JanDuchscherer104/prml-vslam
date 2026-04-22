# WP-09D App CLI Target Snapshot Cutover

Status: Draft

Owner: Unassigned

Dependencies:
- WP-00A Baseline Acceptance
- WP-08 Snapshot Events Payloads
- WP-09A Target Config Launch Cutover
- WP-09C Live Events Handles Cutover

Decision:
- No backward compatibility is required for `StreamingRunSnapshot`,
  top-level stage payload fields, old live handle fields, or old app/CLI
  request flows. App and CLI may move directly to target keyed snapshot data.

Owned paths:
- `src/prml_vslam/pipeline/contracts/runtime.py`
- `src/prml_vslam/pipeline/snapshot_projector.py`
- `src/prml_vslam/pipeline/demo.py`
- `src/prml_vslam/pipeline/run_service.py`
- `src/prml_vslam/pipeline/backend.py`
- `src/prml_vslam/pipeline/backend_ray.py`
- `src/prml_vslam/app/`
- `src/prml_vslam/main.py`
- app, CLI, snapshot, and backend tests under `tests/`

Read-only context paths:
- `src/prml_vslam/pipeline/contracts/events.py`
- `src/prml_vslam/pipeline/stages/base/contracts.py`
- `src/prml_vslam/pipeline/stages/base/handles.py`
- `src/prml_vslam/pipeline/artifact_inspection.py`
- `docs/architecture/pipeline-stage-refactor-target.md`
- `docs/architecture/pipeline-dto-migration-ledger.md`

Target architecture sections:
- `Target Snapshot Shape`
- `Durable Run Events And Live Updates`
- `Transient Payload Handles`
- `App And CLI Contract`

Goal:
- Collapse app and CLI monitoring onto target `RunSnapshot` keyed fields:
  `stage_outcomes`, `stage_runtime_status`, `live_refs`, and artifact refs.
- Delete streaming-specific and stage-specific top-level snapshot fields.

Out of scope:
- New app layout or visual redesign.
- New pipeline runtime behavior.
- Old-run inspection compatibility.

Implementation notes:
- Delete `StreamingRunSnapshot`. Use one `RunSnapshot` type for offline and
  streaming runs.
- Delete `RunSnapshot.stage_status` and `RunSnapshot.stage_progress`. Display
  status is derived at read time from `stage_outcomes`,
  `stage_runtime_status`, current stage, and plan rows.
- Delete top-level stage payload fields from `RunSnapshot`: `sequence_manifest`,
  `benchmark_inputs`, `slam`, `ground_alignment`, `visualization`, `summary`,
  and `stage_manifests`. App and CLI should inspect durable artifacts or keyed
  outcomes through explicit helper functions.
- Delete old live convenience fields: `latest_packet`, `latest_frame`,
  `latest_preview`, `received_frames`, `measured_fps`, `accepted_keyframes`,
  `backend_fps`, `num_sparse_points`, `num_dense_points`,
  `trajectory_positions_xyz`, and `trajectory_timestamps_s`.
- Add app/CLI projection helpers that derive operator-facing cards from
  `StageRuntimeStatus`, `StageRuntimeUpdate` semantic events projected into
  keyed snapshot state, and `live_refs`.
- Replace `read_array(...)` callers with `read_payload(...)` and
  `TransientPayloadRef`.
- Artifact inspection must not backfill deleted top-level snapshot fields. It
  should return explicit inspection DTOs or keyed artifact views.
- CLI terminal printing should not branch on `StreamingRunSnapshot`; it should
  render the same target snapshot shape for every mode.

DTO migration scope:
- Own final deletion of `StreamingRunSnapshot`, `RunSnapshot.stage_status`,
  `RunSnapshot.stage_progress`, top-level stage payload fields, and old live
  snapshot fields.
- Keep `RunState` and `RunSnapshot` as pipeline-owned target projection DTOs.

Termination criteria:
- App and CLI import only `RunSnapshot`, not `StreamingRunSnapshot`.
- Snapshot contract has no stage-specific top-level payload fields.
- App rendering uses target keyed fields and payload refs only.
- Artifact inspection returns explicit inspection models instead of mutating
  `RunSnapshot` compatibility fields.
- Stale-symbol grep for deleted snapshot fields is clean outside historical
  docs.

Required checks:
- `uv run pytest tests/test_app.py tests/test_main.py`
- `uv run pytest tests/test_pipeline.py tests/test_app_services.py`
- app smoke path for pipeline run page
- CLI smoke path for `plan-run-config` and mocked `run-config`
- stale-symbol greps for `StreamingRunSnapshot`, `stage_status`,
  `stage_progress`, `latest_packet`, `latest_frame`, `latest_preview`,
  `received_frames`, `accepted_keyframes`, and top-level stage payload fields
- `make lint`
- `git diff --check`

Known risks:
- App code can accidentally become the new source of stage semantics if status
  derivation is copied into many page helpers. Put shared derivation in one app
  or pipeline helper.
- Removing top-level payload fields before artifact inspection gets explicit
  DTOs can make old artifact pages silently empty.
