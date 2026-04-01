# Pipeline Architecture

The pipeline is split into a planning layer and a runtime layer.

- The planning layer defines what a run is, which artifact boundaries it reserves, and where outputs
  live on disk.
- The runtime layer executes the frame-processing loop in batch or streaming mode and emits typed
  per-step updates.

This keeps artifact layout repo-owned while the execution loop stays small and session-oriented.

## Requirements

The pipeline should satisfy these requirements:

- support both offline batch processing and live streaming with one shared runtime contract
- keep stage inputs and outputs typed with [Pydantic](https://docs.pydantic.dev/latest/)
- make method swapping explicit through a small backend protocol instead of method-specific pipeline code
- allow caching of stage outputs
- keep artifact layout deterministic and repo-owned so CLI, Streamlit, and evaluation all inspect the same workspace
- reserve clear boundaries between planning contracts, runtime messages, method wrappers, and evaluation logic
- stay thin around external systems such as ViSTA-SLAM, MASt3R-SLAM, ARCore, and [`evo`](https://github.com/MichaelGrupp/evo)
- remain simple enough that most pipeline behavior can be understood from the planner, the runtime builder, and the backend protocol

## Module responsibilities

- [`contracts.py`](./contracts.py)
  - Defines the stable repo-owned planning and workspace models using
    [Pydantic](https://docs.pydantic.dev/latest/).
  - `RunPlanRequest` is the input intent for one run: video path, output root, mode, method, stride,
    and capture metadata.
  - `RunPlan` is the derived ordered benchmark plan: stage list, artifact root, and expected outputs.
  - `CaptureManifest` is the persisted record of the input capture under `input/capture_manifest.json`.
    It is the normalized boundary that makes a run inspectable and replayable.
  - `MaterializedWorkspace` is the result of reserving the run directory and writing the initial
    contract files.
  - These models are about run definition and artifact layout, not frame-by-frame execution.

- [`services.py`](./services.py)
  - `PipelinePlannerService` turns a `RunPlanRequest` into a `RunPlan`.
  - `WorkspaceMaterializerService` creates the deterministic workspace on disk and writes
    `run_request.toml`, `run_plan.toml`, and `capture_manifest.json`.
  - The materializer exists so the runtime never invents output paths ad hoc. CLI and Streamlit both
    inspect the same reserved workspace before or after execution.

- [`messages.py`](./messages.py)
  - Defines the runtime packet models, again with [Pydantic](https://docs.pydantic.dev/latest/).
  - `Envelope` is the common wrapper shared by batch replay and streaming sessions.
  - `FramePayload`, `PosePayload`, and `PreviewPayload` describe what is flowing through the runtime
    right now, not what the final workspace should contain.
  - The pose helpers wrap [`pytransform3d`](https://dfki-ric.github.io/pytransform3d/) so SE(3)
    conversion and validation stay explicit and centralized.

- [`runtime/actions.py`](./runtime/actions.py)
  - Holds the small [Burr](https://burr.apache.org/docs/concepts/actions/) actions that implement the
    runtime steps: decode or ingest, SLAM, and export.
  - These actions adapt [Burr state](https://burr.apache.org/docs/concepts/state/) to repo-owned
    message models. Heavy method logic stays in the backend adapters, not here.

- [`runtime/session.py`](./runtime/session.py)
  - `SessionManager` is the main orchestration entrypoint used by the CLI and Streamlit.
  - It creates sessions, selects batch vs streaming mode, prepares replay persistence, runs the
    runtime graph, and finalizes artifacts.
  - `Session` is the in-memory handle for one active run.
  - The mode-specific graphs are built with Burr’s
    [`ApplicationBuilder`](https://burr.apache.org/docs/reference/application/), which makes the
    runtime topology explicit instead of hiding it inside nested loops and conditionals.

- [`methods/base.py`](./methods/base.py)
  - Defines the backend protocol that any method adapter must satisfy.
  - `SlamBackend` is the stable execution boundary between the repo and an external method wrapper.
  - `SlamOutput` is one backend step result: pose, sparse update, and preview state.

- [`methods/vista.py`](./vista.py) and [`methods/mast3r.py`](./mast3r.py)
  - Thin method adapters behind the common `SlamBackend` protocol.
  - They are currently deterministic mocks, but this is the extension point for real external wrappers.

- [`../cli_support.py`](../cli_support.py) and [`../main.py`](../main.py)
  - The [Typer](https://typer.tiangolo.com/) CLI layer on top of the planner, materializer, and runtime.
  - These modules should remain thin operator-facing adapters, not a second orchestration layer.

- [`../app.py`](../app.py)
  - The [Streamlit](https://docs.streamlit.io/) workbench on top of the same contracts and session
    runtime.
  - It should consume repo-owned artifacts, not define new pipeline semantics.

## How to add a stage

There are two distinct additions:

1. Add a planned benchmark stage in [`services.py`](./services.py) by appending a `RunPlanStage`.
   Do this when the repo should reserve a new artifact boundary.
2. Add a runtime step in [`runtime/actions.py`](./runtime/actions.py) and wire it into the Burr graph in
   [`runtime/session.py`](./runtime/session.py).
   Do this when execution needs a new transition in the runtime state machine.

Typical follow-up work:

- add a new runtime payload in [`messages.py`](./messages.py) if the step emits or consumes a new packet type
- extend [`methods/base.py`](./methods/base.py) if the backend protocol needs a new capability
- add or update targeted tests under `tests/`

## Running the pipeline

Offline batch run:

```bash
uv run prml-vslam run-offline "Debug Run" /absolute/path/to/video.mp4 \
  --output-dir artifacts \
  --method vista_slam \
  --max-frames 5
```

Streaming demo:

```bash
uv run prml-vslam run-streaming-demo \
  --output-dir artifacts \
  --method vista_slam \
  --num-frames 5
```

## Why Burr here

We use [Burr](https://burr.apache.org/concepts/) for the runtime layer only.

Relevant advantages for this repo:

- one explicit runtime graph for both batch replay and streaming sessions
- first-class [actions](https://burr.apache.org/docs/concepts/actions/) and
  [state](https://burr.apache.org/docs/concepts/state/) instead of hidden control flow
- step-wise execution that is easier to inspect and debug
- native support for session-oriented execution without adopting a larger workflow platform

Relevant docs:

- [Applications / state machine](https://burr.apache.org/docs/concepts/state-machine/)
- [Streaming actions](https://burr.apache.org/docs/concepts/streaming-actions/)
- [State persistence](https://burr.apache.org/docs/concepts/state-persistence/)
- [Application API](https://burr.apache.org/docs/reference/application/)
