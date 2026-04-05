# Streamlit App Simplification Ranking By Estimated LOC Reduction

This note re-ranks the current Streamlit app cleanup findings by expected **net LOC reduction** while preserving the current behavior described in:

- `src/prml_vslam/app/REQUIREMENTS.md`
- `src/prml_vslam/app/AGENTS.md`

The estimates below are directional. They assume a pragmatic refactor that consolidates repeated patterns without adding new features.

## Ranking

### 1. Extract one shared live-session rendering shell

- Estimated net reduction: **180-280 LOC**
- Primary targets:
  - `src/prml_vslam/app/pages/record3d.py`
  - `src/prml_vslam/app/pages/advio.py`
  - `src/prml_vslam/app/pages/pipeline.py`
- Why it ranks first:
  - The three live pages all repeat the same Streamlit architecture pattern:
    - explicit controls
    - fragment-scoped rerun
    - status banner
    - metric row
    - trajectory tab
    - camera intrinsics panel
    - JSON details panel
  - Streamlit reruns work best when the page body is mostly declarative and the repeated fragment logic lives in one helper.
- Likely shape:
  - add a reusable `render_live_session_panel(...)`
  - add small page-specific adapters for status text, metrics, tabs, and details payloads

### 2. Split and normalize `app/services.py`

- Estimated net reduction: **100-180 LOC**
- Primary targets:
  - `src/prml_vslam/app/services.py`
  - new small private modules under `src/prml_vslam/app/`
- Why it ranks second:
  - `services.py` currently combines:
    - generic worker lifecycle
    - rolling metrics
    - ADVIO preview snapshot/runtime
    - Record3D runtime
  - The generic worker code already removes duplication, but the file still carries too many responsibilities and duplicate runtime-specific worker loops.
- Likely shape:
  - move `WorkerRuntime` and rolling metrics into a private runtime helper module
  - keep ADVIO and Record3D runtime modules separate
  - optionally introduce a narrower generic stream-runner helper for the shared connect/wait/update/finalize loop

### 3. Simplify the metrics page into one controller/view-model pass

- Estimated net reduction: **70-130 LOC**
- Primary targets:
  - `src/prml_vslam/app/pages/metrics.py`
- Why it ranks high:
  - The page resolves selection multiple times and interleaves:
    - selector rendering
    - state persistence
    - persisted result loading
    - compute gating
    - result rendering
  - That creates extra branching that is not buying functionality.
- Likely shape:
  - create one `resolve_metrics_view(...)` helper returning a typed view model
  - keep `Compute metrics` as an explicit action
  - reduce repeated `_save_state(...)` and `_resolve_selection(...)` calls

### 4. Move page sections out of the large page modules

- Estimated net reduction: **40-100 LOC**
- Primary targets:
  - `src/prml_vslam/app/pages/advio.py`
  - `src/prml_vslam/app/pages/pipeline.py`
- Why it ranks here:
  - This mostly improves readability, but if done carefully it also removes repeated layout boilerplate and repeated local selection logic.
  - `ADVIO` currently mixes download, overview, explorer, and live preview in one file.
  - `Pipeline` mixes request building, controls, live monitoring, and artifact rendering in one file.
- Likely shape:
  - `advio_sections.py` for download / explorer / preview
  - `pipeline_sections.py` for controls / live snapshot / artifacts

### 5. Deduplicate runtime loading in `SessionStateStore`

- Estimated net reduction: **30-70 LOC**
- Primary targets:
  - `src/prml_vslam/app/state.py`
- Why it ranks here:
  - `load_record3d_runtime`, `load_advio_runtime`, and `load_pipeline_runtime` all implement the same load-or-create-or-replace pattern.
  - This is straightforward duplication with low behavioral risk.
- Likely shape:
  - add one generic private loader:
    - session key
    - runtime factory
    - compatibility predicate

### 6. Consolidate page action/state persistence helpers

- Estimated net reduction: **30-60 LOC**
- Primary targets:
  - `src/prml_vslam/app/advio_controller.py`
  - `src/prml_vslam/app/record3d_controller.py`
  - `src/prml_vslam/app/pages/pipeline.py`
- Why it ranks here:
  - Each page has a slightly different version of:
    - apply selector updates
    - stop/restart runtime when selectors change
    - persist only when values changed
    - sync runtime state back into app state
  - A small shared controller helper would trim code and make page actions more uniform.

### 7. Make page registration and leave-page shutdown data-driven

- Estimated net reduction: **20-50 LOC**
- Primary targets:
  - `src/prml_vslam/app/bootstrap.py`
- Why it ranks here:
  - `_build_pages(...)` and the four page entry wrappers are repetitive.
  - `_enter_page(...)` is also hard-coded against page ids and runtime stop rules.
- Likely shape:
  - define a small `PageSpec`
  - generate `st.Page(...)` entries from data
  - register optional `stop_on_leave` callbacks

### 8. Remove dead or nearly-dead scaffolding

- Estimated net reduction: **10-30 LOC**
- Primary targets:
  - `src/prml_vslam/app/ui.py`
  - `src/prml_vslam/app/bootstrap.py`
  - `src/prml_vslam/app/README.qmd`
- Why it ranks here:
  - `inject_styles()` is currently a no-op but still called.
  - The app architecture note still describes the app as more Record3D-centric than the current codebase.
  - This is small, but it tightens the surface.

### 9. Centralize tiny display helpers

- Estimated net reduction: **10-25 LOC**
- Primary targets:
  - `src/prml_vslam/app/pages/advio.py`
  - `src/prml_vslam/app/pages/pipeline.py`
  - `src/prml_vslam/app/record3d_view_utils.py`
  - `src/prml_vslam/app/camera_display.py`
- Why it ranks low:
  - There are a few duplicated label and details-formatting helpers, especially around pose-source labels and frame detail payloads.
  - This is worth doing only after the larger structural simplifications.

## Recommended Order

If the goal is to reduce app LOC with the least functional risk, the order should be:

1. shared live-session rendering shell
2. `services.py` split and normalization
3. metrics page controller/view-model simplification
4. page-section extraction
5. `SessionStateStore` deduplication

That sequence should remove the most code while preserving the current Streamlit execution model:

- explicit form submits for expensive actions
- one `st.session_state` adapter
- fragment-scoped reruns for live surfaces
- typed app-facing state

## Not Recommended As Early LOC Work

These may improve clarity, but they are not the first places to chase LOC reduction:

- redesigning the page UX
- changing page count or navigation structure
- moving plotting code again
- replacing the current fragment-based live refresh model

Those changes risk functional churn without comparable LOC payoff.
