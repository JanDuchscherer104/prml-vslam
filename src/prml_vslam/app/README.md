# Streamlit App Architecture

This package contains the packaged Streamlit workbench for PRML VSLAM.

The app is intentionally small and typed. It is not the owner of capture, benchmark execution, or artifact formats. Instead, it is a thin interactive surface over repo-owned services in `prml_vslam.sources.replay`, `prml_vslam.sources.datasets`, `prml_vslam.eval`, `prml_vslam.pipeline`, `prml_vslam.sources`, `prml_vslam.visualization`, and `prml_vslam.utils`.

Use this document together with the other app-specific and repo-wide guidance:

- [REQUIREMENTS.md](REQUIREMENTS.md)
- [AGENTS.md](AGENTS.md)

## Design Goals

- Keep Streamlit-specific orchestration in this package, but keep domain logic outside it.
- Model app-facing state with typed Pydantic models.
- Let exactly one adapter touch raw `st.session_state`.
- Use idiomatic Streamlit primitives such as forms, tabs, metrics, and fragment-scoped reruns instead of custom browser components.
- Make expensive actions explicit. In particular, the metrics page must not run `evo` implicitly on selector changes.

## Mental Model

The app follows a small layered pattern:

1. `bootstrap.py` constructs typed context for one rerun.
2. `state.py` restores persisted app state and the opaque live Record3D runtime from `st.session_state`.
3. `bootstrap.py` registers native Streamlit pages through `st.navigation()` and enters the selected page.
4. Page modules in `pages/` render the current view and translate user actions into service calls.
5. `services.py` owns Record3D-specific app glue and long-lived preview side effects.
6. `plotting/` builds Plotly figures, keeping page modules focused on layout.

This maps well onto Streamlit's rerun model:

- local variables are rebuilt on every rerun
- persisted app state lives in `SessionStateStore`
- long-lived live-stream behavior is handled by `Record3DStreamRuntimeController`
- live preview refresh uses `@st.fragment` so the Record3D page can update without forcing full app rebuild semantics for every frame
- forms batch widget changes for explicit submit-driven actions

## Sequence Diagram

The following sequence chart shows the main architecture flow for one browser session, including both ordinary Streamlit reruns and the live Record3D path.

```{mermaid}
sequenceDiagram
    autonumber
    actor User
    participant Browser as Streamlit Frontend
    participant Bootstrap as app/bootstrap.py
    participant Store as SessionStateStore
    participant Page as pages/*.py
    participant Service as prml_vslam.eval/services.py
    participant Runtime as Record3DStreamRuntimeController
    participant Source as prml_vslam.sources

    User->>Browser: Open app or interact with a widget
    Browser->>Bootstrap: Trigger script rerun
    Bootstrap->>Store: Load AppState
    Store-->>Bootstrap: Typed persisted state
    Bootstrap->>Store: Load Record3D runtime handle
    Store-->>Bootstrap: Session-local runtime controller
    Bootstrap->>Browser: Register pages with st.navigation()
    Browser-->>Bootstrap: Resolve selected page
    Bootstrap->>Page: Render selected page with AppContext

    alt Record3D page
        Page->>Store: Persist selector updates
        Page->>Browser: Render sidebar controls
        User->>Page: Submit Start/Restart form
        Page->>Runtime: start_usb(...) or start_wifi_preview(...)
        Runtime->>Source: Create Record3D observation stream
        Source-->>Runtime: Blocking observation stream
        loop Background worker thread
            Runtime->>Source: wait_for_observation(...)
            Source-->>Runtime: Observation
            Runtime->>Runtime: Update Record3DStreamSnapshot
        end
        loop Fragment rerun
            Browser->>Page: Rerun live fragment
            Page->>Runtime: snapshot()
            Runtime-->>Page: Latest snapshot
            Page-->>Browser: Render metrics, images, Plotly trajectory
        end
    else Metrics page
        Page->>Service: discover_runs(...) / resolve_selection(...)
        Service->>Service: Resolve dataset and run artifacts
        alt User presses Compute
            Page->>Service: compute_evaluation(...)
            Service->>Service: Run explicit evo evaluation
            Service-->>Page: EvaluationArtifact
        else Persisted result exists
            Page->>Service: load_evaluation(...)
            Service-->>Page: EvaluationArtifact
        end
        Page-->>Browser: Render metrics, figures, provenance
    else Datasets page
        Page->>Service: summarize() / scene_rows()
        Service->>Service: Read committed dataset catalogs and local dataset roots
        Page-->>Browser: Render dataset summary metrics and scene table
        User->>Page: Submit explicit download form
        Page->>Service: download(...)
        Service->>Service: Fetch selected archives and calibrations
        Service-->>Page: Download result summary
        Page-->>Browser: Render refreshed local coverage
    end
```

## Package Responsibilities

### File-by-file

- [__init__.py](__init__.py)
  - Public package entrypoint.
  - Re-exports `run_app()` so `streamlit_app.py` stays thin.

- [bootstrap.py](bootstrap.py)
  - Builds one typed `AppContext` per rerun.
  - Wires shared services and persisted state together.
  - Registers Streamlit-native top-level navigation and enters the active page.
  - Stops the live Record3D runtime when the user leaves the `Record3D` page.

- [models.py](models.py)
  - Defines app-owned page and session-state models only.
  - Keeps persisted page state JSON-friendly so session persistence survives reruns.

- [state.py](state.py)
  - The only app module allowed to access raw `st.session_state`.
  - Persists and restores `AppState`.
  - Owns the opaque session-local `Record3DStreamRuntimeController`.
  - Handles hot-reload compatibility for stored runtime objects.

- [services.py](services.py)
  - Record3D-only app glue.
  - `Record3DStreamRuntimeController` owns the live stream worker thread and maintains the latest `Record3DStreamSnapshot`.

- [pipeline_controls.py](pipeline_controls.py)
  - Pipeline-page request editing, template syncing, validation, and run-launch helpers.
  - Keeps request construction and action handling out of the render-only page module.

- [pipeline_controller.py](pipeline_controller.py)
  - Pipeline snapshot presentation and app-facing render-model shaping.
  - Re-exports the Pipeline page control helpers for a stable app-local import surface.

- [ui.py](ui.py)
  - Shared app UI helpers only.
  - Currently provides lightweight page-header rendering and the style hook.

- [pages/metrics.py](pages/metrics.py)
  - Metrics page renderer.
  - Reads current selectors and controls from app state.
  - Uses explicit actions for `evo` execution.
  - Delegates data access to `TrajectoryEvaluationService` and figure creation to `plotting.metrics`.

- [pages/artifacts.py](pages/artifacts.py)
  - Persisted run artifact inspector.
  - Reads typed summaries, manifests, structured paths, and small raw metadata from a selected method-level run root.
  - Keeps heavier trajectory and reconstruction views behind explicit buttons.

- [pages/datasets.py](pages/datasets.py)
  - Dataset-management page renderer for ADVIO and TUM RGB-D tabs.
  - Renders committed upstream metadata, local dataset coverage, and explicit download controls.
  - Delegates dataset discovery and downloads to dataset services.

- [pages/record3d.py](pages/record3d.py)
  - Record3D page renderer.
  - Owns Streamlit layout only: sidebar controls, tabs, status panels, image rendering, LaTeX intrinsics, and Plotly trajectory display.
  - Does not decode frames or speak WebRTC directly.
  - Uses a fragment-scoped renderer for live snapshot refresh.

- [plotting/metrics.py](plotting/metrics.py)
  - Plotly builders for persisted benchmark review.
  - Keeps chart configuration out of page modules.

- [plotting/record3d.py](plotting/record3d.py)
  - Plotly builders for live Record3D visuals such as the 3D ego trajectory.

- [plotting/theme.py](plotting/theme.py)
  - Shared Plotly colors, margins, and legend layout for workbench figures.

- [REQUIREMENTS.md](REQUIREMENTS.md)
  - Normative app scope and acceptance criteria.

- [AGENTS.md](AGENTS.md)
  - Local engineering and architecture constraints for contributors and agents.

### Directory roles

- `pages/`
  - Page-level render functions only.
  - Pages compose layout and call services; they should not become miniature service layers.

- `plotting/`
  - Pure figure-building helpers.
  - This keeps Plotly configuration reusable and avoids large inline chart code inside page modules.

## Boundaries To Other Packages

- `prml_vslam.sources.replay`
  - Owns replay clocking and shared observation-stream mechanics.
  - The app consumes shared typed source contracts; it does not implement
    transport protocols itself.

- `prml_vslam.sources.record3d`
  - Owns Record3D capture, frame decoding, and the official USB plus Wi-Fi
    Preview transport integrations.

- `prml_vslam.sources.datasets`
  - Owns ADVIO metadata, local dataset normalization, and selective download semantics.
  - The app renders dataset summaries and forwards explicit user actions into dataset-owned services.

- `prml_vslam.utils`
  - Owns shared utilities such as `PathConfig`, `BaseConfig`, and `Console`.
  - `PathConfig` is the source of truth for repo paths and discovery roots.

- `prml_vslam.pipeline`
  - Owns run planning, execution orchestration, manifests, and runtime state.
  - The Streamlit app may expose pipeline-facing controls, but it should not define pipeline semantics itself.

- `prml_vslam.sources`
  - Owns source-stage preparation and reference identifiers consumed by prepared benchmark-side inputs.

- `prml_vslam.visualization`
  - Owns viewer policy and preserved native Rerun artifacts.

- `prml_vslam.eval`
  - Owns evaluation logic, artifact semantics, and benchmark-run discovery for the metrics surface.
  - The app presents persisted evaluation outputs rather than inventing app-only evaluation formats.

## State Pattern

The app uses two kinds of state:

- Persisted UI state
  - Stored as `AppState` in `st.session_state`
  - Includes current selectors and current controls
  - Must remain JSON-friendly

- Opaque runtime state
  - Stored as `Record3DStreamRuntimeController` in `st.session_state`
  - Represents the session-local live stream worker and latest snapshot
  - Not serialized into the JSON app state

This separation is deliberate:

- UI state should be easy to restore on rerun
- long-lived runtime objects should not be reconstructed from ad hoc widget values every time the script reruns

## Page Pattern

Each page should follow the same structure:

1. Render a small page intro.
2. Render sidebar controls when the page has live setup inputs.
3. Read current typed state from `context.state`.
4. Save selector changes back through `context.store`.
5. Call app services for side effects or derived data.
6. Render figures and summaries through plotting helpers and typed snapshots.

Pages should not:

- touch raw `st.session_state`
- instantiate transport-specific lower-level objects directly
- inline large Plotly figure definitions
- own benchmark or transport business logic

## Record3D Runtime Pattern

The Record3D page uses an explicit runtime-controller pattern:

- the UI starts or stops a session through `Record3DStreamRuntimeController`
- the runtime owns a background worker thread
- the worker consumes `ObservationStream` objects from the source layer
- the worker continuously updates one shared `Record3DStreamSnapshot`
- the page reads that snapshot during fragment reruns and renders it

This keeps the live path compatible with Streamlit's rerun model while avoiding transport logic in the UI.

## Metrics Pattern

The metrics page is artifact-first:

- selectors resolve to a dataset slice and artifact run
- persisted `evo` results are loaded when available
- recomputation happens only when the user presses the explicit action button
- visual rendering is split into:
  - scalar metrics
  - trajectory/error figures
  - provenance

This avoids hidden expensive work during ordinary reruns.

## Why This Structure

This package layout is intentionally conservative:

- small enough to understand quickly
- strongly typed at the app boundary
- aligned with Streamlit's rerun architecture
- easy to test with `AppTest`
- easy to extend with another page or another plotting module without turning the package into a monolith

When adding features, prefer extending the existing pattern rather than adding new architectural layers:

- new page -> `pages/<name>.py`
- new chart -> `plotting/<name>.py`
- new app session-state model -> `models.py`
- new evaluation/discovery contract -> `prml_vslam.eval`
- new benchmark reference identifier -> `prml_vslam.sources.contracts`
- new prepared benchmark-input contract -> `prml_vslam.sources.contracts`
- new viewer/export artifact contract -> `prml_vslam.visualization`
- new app-facing orchestration or runtime behavior -> `services.py`
- new persisted state slot -> `state.py`
