# Streamlit App Responsibility Issues

This note records code currently living under `src/prml_vslam/app/` that
appears to exceed the app's intended ownership boundary.

Relevant constraints:

- the app is not responsible for pipeline orchestration, data flow, or domain
  logic
- the app may orchestrate background runtime objects, but those runtime objects
  should consume repo-owned contracts rather than become app-owned execution
  surfaces
- page modules should focus on rendering and light orchestration

## Scanned Implementations

The current findings were checked against the domain-specific implementations
already present in the repo, not just against the app-facing wrappers.

- `src/prml_vslam/io/record3d.py`
- `src/prml_vslam/io/wifi_session.py`
- `src/prml_vslam/io/cv2_producer.py`
- `src/prml_vslam/datasets/advio/advio_service.py`
- `src/prml_vslam/datasets/advio/advio_sequence.py`
- `src/prml_vslam/datasets/advio/advio_replay_adapter.py`
- `src/prml_vslam/pipeline/session.py`
- `src/prml_vslam/methods/mock_vslam.py`
- `src/prml_vslam/eval/services.py`
- `src/prml_vslam/eval/contracts.py`
- `src/prml_vslam/eval/mock_metrics.py`

## Issue 1: App-Owned Runtime And Stream Workers

Affected files:

- `src/prml_vslam/app/services.py`
- `src/prml_vslam/pipeline/session.py`

Problem:

- `WorkerRuntime` owns generic thread lifecycle, stop events, active-stream
  registration, disconnect handling, and snapshot mutation.
- `AdvioPreviewRuntimeController` owns ADVIO replay polling, frame ingestion,
  trajectory extraction, and failure handling.
- `Record3DStreamRuntimeController` owns Record3D stream construction,
  connection, timeout filtering, packet polling, and runtime metrics.
- The same category of runtime metrics helper already exists in
  `src/prml_vslam/pipeline/session.py`, so the app currently owns duplicated
  execution/runtime infrastructure.

Why this is outside app responsibility:

- This is execution and data-flow ownership, not UI composition.
- The app should consume runtime/session services, not define generic worker
  runtimes and stream-processing loops.

Suggested direction:

- Move generic worker/session primitives out of `app/services.py`.
- Move Record3D live runtime ownership into `prml_vslam.io` or a dedicated
  runtime/session package.
- Move ADVIO preview runtime ownership into `datasets` or a dedicated
  runtime/session package.
- Deduplicate rolling-metrics helpers with the pipeline session implementation
  instead of maintaining two app/runtime variants.

Present redundancies and simplifications:

- `app/services.py` and `pipeline/session.py` both define:
  - empty trajectory-array helpers
  - rolling runtime metrics helpers
  - pose-to-position extraction helpers
- `app/services.py` owns a generic `WorkerRuntime`, while
  `pipeline/session.py` owns a separate packet-loop runtime with very similar
  lifecycle structure.
- `app/services.py` rebuilds Record3D USB and Wi-Fi stream factories even
  though transport setup is already owned by `io/record3d.py` and
  `io/wifi_session.py`.
- `app/services.py` owns `Record3DAppService`, which is just a thin wrapper
  over USB device listing already available from the IO layer.
- `datasets/advio/advio_service.py` already owns both:
  - `build_sequence_manifest(...)`
  - `open_preview_stream(...)`
  - `build_streaming_source(...)`
  so the app-side ADVIO preview runtime is layered on top of a dataset-owned
  replay abstraction that already exists.
- `datasets/advio/advio_sequence.py` and
  `datasets/advio/advio_replay_adapter.py` repeatedly resolve the same ADVIO
  paths and metadata when building manifests and replay streams.

Recommended action items:

1. Extract one repo-owned packet-session runner for `FramePacketStream`
   consumers and reuse it for:
   - Record3D preview
   - ADVIO preview
   - pipeline replay sessions
2. Move `WorkerRuntime`, rolling metrics helpers, and position-extraction
   helpers out of `app/services.py`.
3. Move Record3D runtime ownership down into `io` and keep the app limited to
   invoking that service and rendering its snapshot.
4. Move ADVIO preview runtime ownership down into `datasets` or the shared
   runtime/session layer, reusing the dataset-owned replay abstractions that
   already exist.
5. Remove `Record3DAppService` if device listing stays directly available from
   the IO layer.
6. Deduplicate snapshot field definitions across app preview runtimes and the
   pipeline session by extracting a shared live-runtime stats contract or base
   model.
7. Introduce a resolved ADVIO sequence handle or similar helper so manifest
   creation and replay setup stop reloading the same path/calibration/timing
   data independently.

## Issue 2: Page-Owned Pipeline Request Policy

Affected file:

- `src/prml_vslam/app/pages/pipeline.py`

Problem:

- `_build_demo_request()` hard-codes experiment naming, source normalization,
  and stage-toggle policy for the pipeline demo.
- The page currently decides that the demo run should always use:
  - `DatasetSourceSpec(dataset_id=DatasetId.ADVIO, ...)`
  - `DenseConfig(enabled=True)`
  - `ReferenceConfig(enabled=False)`
  - all evaluation toggles disabled

Why this is outside app responsibility:

- This is pipeline policy and request-shaping logic, not rendering.
- The page should collect user intent and hand it to a pipeline-owned builder
  or demo-request factory.

Suggested direction:

- Move demo-request construction into `prml_vslam.pipeline` as an explicit
  builder/helper for the bounded demo slice.
- Keep the page responsible only for selectors, button handling, and rendering
  the resulting plan/session state.

Present redundancies and simplifications:

- `app/pages/pipeline.py` hard-codes the bounded demo run shape, while
  `pipeline/session.py` separately hard-codes which stage ids are actually
  supported by the current streaming slice.
- `pipeline/services.py` already owns generic `RunRequest -> RunPlan`
  planning, but the app still owns the policy for how the demo request should
  be shaped.
- `pipeline/session.py` manually rebuilds stage-status and summary-manifest
  policy for the same bounded stage subset, so stage knowledge is currently
  split across page code, session code, and planner code.
- `methods/mock_vslam.py` and `pipeline/session.py` are already the true
  runtime endpoints for the demo, so the app page adds little value by owning
  request-shaping logic itself.

Recommended action items:

1. Add a pipeline-owned demo request builder or demo config surface that
   accepts only the bounded user choices:
   - sequence id or slug
   - mode
   - method
   - pose source / replay options when needed
2. Remove `_build_demo_request()` from `app/pages/pipeline.py`.
3. Keep the page limited to collecting selectors and invoking the pipeline
   helper, then rendering `RunPlan` and session snapshots.
4. Centralize the supported-stage policy for the bounded demo slice in
   `prml_vslam.pipeline` instead of splitting it between page code and session
   code.
5. Extract stage-status and summary-manifest construction from
   `pipeline/session.py` into a smaller pipeline-owned helper once the demo
   request policy is centralized.

## Issue 3: Page-Owned Evaluation Readiness Rules

Affected file:

- `src/prml_vslam/app/pages/metrics.py`

Problem:

- The page decides whether evaluation can run based on benchmark-specific rules
  such as `selection.reference_path is not None` and
  `selection.run.estimate_path.exists()`.
- The page also owns the user-facing policy message that evaluation is only
  allowed when a TUM reference trajectory already exists.

Why this is outside app responsibility:

- Readiness and failure policy for evaluation belongs to `eval`, not to the
  Streamlit page.
- The page should render a typed status from the evaluation service instead of
  re-encoding service preconditions inline.

Suggested direction:

- Move readiness checks and explanatory status into
  `TrajectoryEvaluationService` or a small eval-facing view model/helper.
- Let the page consume a typed "can compute / why not" result instead of
  duplicating evaluation policy.

Present redundancies and simplifications:

- `app/pages/metrics.py` re-resolves selection state multiple times during one
  render even though `eval/services.py` already owns selection resolution.
- `app/pages/metrics.py` computes readiness using direct path checks, while
  `eval/services.py` already owns the same inputs and can decide readiness
  centrally.
- `MetricsPageState` persists `EvaluationControls`, but
  `eval/contracts.py` defines `EvaluationControls` as an empty placeholder and
  `eval/services.py.result_path(...)` currently ignores it.
- `MetricsPageState` also persists `result_path`, but the page recomputes or
  reloads the result from the selection on each render anyway.
- `methods/mock_vslam.py` and `eval/mock_metrics.py` both parse TUM trajectory
  files directly, so basic trajectory artifact reading is duplicated across
  packages.

Recommended action items:

1. Add an eval-owned selection/readiness view model that returns:
   - dataset and sequence choices
   - run choices
   - current resolved selection
   - whether metrics can be computed
   - why computation is blocked when it is blocked
   - any currently persisted evaluation artifact
2. Update the metrics page to render that eval-owned status instead of
   duplicating readiness policy inline.
3. Remove `EvaluationControls` from app state until real controls exist, or
   add real controls and make `result_path(...)` depend on them.
4. Remove `result_path` from app state unless the app truly needs to persist a
   path independent of the current resolved selection.
5. Consolidate TUM trajectory parsing into one shared artifact reader used by
   both `methods/mock_vslam.py` and `eval/mock_metrics.py`.

## Non-Issues

The following code looked acceptable for current app ownership and does not
need to move just because of this review:

- `src/prml_vslam/app/bootstrap.py`
  - page-entry lifecycle handling such as stopping page-scoped runtimes when
    navigating away
- `src/prml_vslam/app/live_session.py`
  - shared Streamlit rendering helpers
- most of `src/prml_vslam/app/pages/record3d.py`
  - UI rendering plus light action orchestration
- most of `src/prml_vslam/app/pages/advio.py`
  - UI rendering, download form wiring, and preview composition

## Follow-Up Work

1. Extract a repo-owned runtime/session layer for non-pipeline live preview
   flows.
2. Move bounded pipeline-demo request construction into `prml_vslam.pipeline`.
3. Move evaluation readiness/status logic into `prml_vslam.eval`.
4. Remove placeholder or duplicated app state once the eval/pipeline helpers
   exist.
5. Consolidate shared artifact helpers such as TUM readers and stable
   live-runtime metrics helpers.
6. Re-run the app-responsibility review after those moves to ensure `app/`
   becomes a thin rendering and orchestration layer.
