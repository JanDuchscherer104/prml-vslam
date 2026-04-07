# PRML VSLAM Pipeline Guide

This README is the long-form implementation guide for `src/prml_vslam/pipeline/`.

Use [REQUIREMENTS.md](./REQUIREMENTS.md) for the concise pipeline contract and [../REQUIREMENTS.md](../REQUIREMENTS.md) for top-level package ownership. Shared source-provider protocols live in [`prml_vslam.protocols.source`](../protocols/source.py), shared runtime seams live in [`prml_vslam.protocols.runtime`](../protocols/runtime.py), and shared SLAM behavior seams live in [`prml_vslam.methods.protocols`](../methods/protocols.py).

## Current Implementation

Today `prml_vslam.pipeline` is a typed planning package plus a bounded runtime slice.

The current module split is:

- [`contracts.py`](./contracts.py)
  - owns `RunRequest`, `RunPlan`, `SequenceManifest`, `ArtifactRef`, `SlamArtifacts`, `StageManifest`, `RunSummary`, and `SlamUpdate`
- [`services.py`](./services.py)
  - owns planning through `RunPlannerService`
- [`workspace.py`](./workspace.py)
  - owns capture-manifest helpers such as `CaptureManifest`
- [`demo.py`](./demo.py)
  - owns persisted request helpers and request templates, not the runtime
- [`run_service.py`](./run_service.py)
  - owns the current runtime entry surface
- [`session.py`](./session.py)
  - owns the bounded session lifetime, incremental updates, and finalization

The current launch surfaces are:

- the Streamlit [`Pipeline` page](../app/pages/pipeline.py)
- the CLI [`plan-run-config`](../main.py) and [`pipeline-demo`](../main.py) commands

The current executable stage subset is limited to `ingest`, `slam`, and `summary`. The planner can already describe reference and evaluation stages, but the bounded runtime rejects them until explicit runtime support exists.

The current offline demo path also still flows through the streaming execution seam. Single-pass replay is real today, but it is still implemented through the bounded session service rather than through a separate `OfflineRunner`.

## Ownership Model

The pipeline package owns its own DTOs, manifests, and payload bundles. In practice that means the pipeline owns:

- `RunRequest`
- `RunPlan`
- `SequenceManifest`
- `ArtifactRef`
- `SlamArtifacts`
- `StageManifest`
- `RunSummary`
- `SlamUpdate`

The pipeline does not own every symbol it consumes.

- Shared runtime data such as [`FramePacket`](../interfaces/runtime.py) belongs to [`prml_vslam.interfaces`](../interfaces/runtime.py).
- Shared runtime behavior seams such as [`FramePacketStream`](../protocols/runtime.py) and [`StreamingSequenceSource`](../protocols/source.py) belong to [`prml_vslam.protocols`](../protocols/source.py).
- SLAM behavior seams such as [`SlamBackend`](../methods/protocols.py) and [`SlamSession`](../methods/protocols.py) belong to [`prml_vslam.methods.protocols`](../methods/protocols.py).
- Streamlit-only UI state such as [`PipelinePageState`](../app/models.py) belongs to [`prml_vslam.app.models`](../app/models.py).

That split keeps one semantic concept attached to one owning module instead of letting app state, transport payloads, and benchmark contracts drift into parallel shapes.

## Manifests And Artifacts

The package is manifest-driven and artifact-first. Those terms are related, but they are not interchangeable.

A **manifest** is a typed description of normalized input data or executed work. It tells later stages what exists, where it lives, and how it should be interpreted.

An **artifact** is the durable payload a stage produces or reuses, such as a trajectory file, point cloud, or preview log.

The current key manifest contracts are:

- [`SequenceManifest`](./contracts.py)
  - the normalized input boundary between source adaptation and the main benchmark stages
  - currently requires only `sequence_id`, with optional paths for `video_path`, `rgb_dir`, `timestamps_path`, `intrinsics_path`, `reference_tum_path`, and `arcore_tum_path`
- [`StageManifest`](./contracts.py)
  - one stage-level provenance record with execution status and output paths
- [`RunSummary`](./contracts.py)
  - the terminal run-level summary and stage-status view

The current key artifact contracts are:

- [`ArtifactRef`](./contracts.py)
  - a typed handle to one materialized artifact with `path`, `kind`, and `fingerprint`
- [`SlamArtifacts`](./contracts.py)
  - the current concrete SLAM payload bundle
  - `trajectory_tum` is mandatory
  - `sparse_points_ply`, `dense_points_ply`, and `preview_log_jsonl` remain optional

This is the reason the package talks about explicit artifact paths and run summaries instead of moving heavy stage outputs around as large in-memory payloads.

## Request And Runtime Lifecycle

The current runtime flow is:

1. A caller constructs or loads a [`RunRequest`](./contracts.py).
2. [`RunPlannerService`](./services.py) validates the request, chooses enabled stages, assigns stable `RunPlanStageId` values, and resolves canonical artifact paths through [`PathConfig.plan_run_paths(...)`](../utils/path_config.py).
3. [`RunService`](./run_service.py) accepts the typed request and source, checks that every planned stage is within the currently executable slice, and hands the run into [`PipelineSessionService`](./session.py).
4. [`PipelineSessionService`](./session.py) persists the normalized sequence manifest, opens the packet stream, starts the SLAM session, and updates the live snapshot with incremental [`SlamUpdate`](./contracts.py) values.
5. When the session stops, completes, or fails, the service finalizes [`SlamArtifacts`](./contracts.py), stage manifests, and the [`RunSummary`](./contracts.py).

The current runtime keeps the hot path lightweight, but the durable boundaries stay at the manifest, artifact bundle, and final summary layers.

## Example Requests

The smallest offline pipeline is a [`RunRequest`](./contracts.py) with an offline source and a [`SlamConfig`](./contracts.py):

```python
from pathlib import Path

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts import (
    BenchmarkEvaluationConfig,
    ReferenceConfig,
    SlamConfig,
    VideoSourceSpec,
)
from prml_vslam.utils import PathConfig

request = RunRequest(
    experiment_name="office-offline-vista",
    mode=PipelineMode.OFFLINE,
    output_dir=Path(".artifacts"),
    source=VideoSourceSpec(video_path=Path("captures/office.mp4"), frame_stride=2),
    slam=SlamConfig(method=MethodId.VISTA, emit_dense_points=False),
    reference=ReferenceConfig(enabled=False),
    evaluation=BenchmarkEvaluationConfig(
        compare_to_arcore=False,
        evaluate_cloud=False,
        evaluate_efficiency=True,
    ),
)

plan = request.build(PathConfig())
```

A streaming Record3D request uses the transport-aware live source contract:

```python
from pathlib import Path

from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts import Record3DLiveSourceSpec, SlamConfig

request = RunRequest(
    experiment_name="record3d-live-vista",
    mode=PipelineMode.STREAMING,
    output_dir=Path(".artifacts"),
    source=Record3DLiveSourceSpec(
        transport=Record3DTransportId.WIFI,
        device_address="myiphone.local",
        persist_capture=True,
    ),
    slam=SlamConfig(method=MethodId.VISTA),
)
```

## Current Record3D Live Support

Record3D live support is already present in both the app and the bounded pipeline runtime.

The planning-facing source contract is [`Record3DLiveSourceSpec`](./contracts.py). The runtime-facing live-source adapter is [`Record3DStreamingSourceConfig`](../io/record3d_source.py).

Both transports are currently implemented:

- `USB`
  - richer transport
  - current shared packet surface includes RGB, depth, confidence, intrinsics, and pose
  - canonical programmatic ingress
- `Wi-Fi Preview`
  - Python-side WebRTC preview receiver
  - current shared packet surface includes RGB and depth plus intrinsics when metadata is available
  - does not currently expose pose or confidence parity with USB

One important current limitation remains: the live [`prepare_sequence_manifest(...)`](../io/record3d_source.py) path still only materializes `SequenceManifest(sequence_id=...)`. That means the intended architectural convergence at the `SequenceManifest` boundary is only partially true today for live Record3D sessions, even though both transports can already be planned and launched.

## TOML Planning Semantics

The repo-owned way to persist a durable request is through [`RunRequest`](./contracts.py) plus the helpers in [`demo.py`](./demo.py).

The current TOML structure mirrors the nested config models directly:

```toml
experiment_name = "advio-office-offline-vista"
mode = "offline"
output_dir = ".artifacts"

[source]
dataset_id = "advio"
sequence_id = "advio-15"

[slam]
method = "vista"
config_path = ".configs/methods/vista/demo.toml"
max_frames = 300
emit_dense_points = true
emit_sparse_points = true

[reference]
enabled = false

[evaluation]
compare_to_arcore = true
evaluate_cloud = false
evaluate_efficiency = true
```

The current `[source]` shapes are:

- video source
  - `video_path` and optional `frame_stride`
- dataset source
  - `dataset_id` and `sequence_id`
- Record3D live source
  - `source_id = "record3d"`
  - `transport = "usb"` or `transport = "wifi"`
  - `persist_capture = true | false`
  - optional `device_index` for USB or `device_address` for Wi-Fi Preview

`plan-run-config` resolves the config file itself through [`PathConfig`](../utils/path_config.py), but nested TOML paths such as `source.video_path`, `slam.config_path`, or `output_dir` are hydrated exactly as written and should be normalized explicitly when repo-relative behavior is required at runtime.

`BenchmarkEvaluationConfig.compare_to_arcore` is documented here in its current code shape. Today it is the planner flag that reserves the trajectory evaluation stage for ARCore comparison. The name is overloaded, but until the code is refactored the pipeline docs describe that current behavior as-is.

## Diagram Pointers

The richer request-lifecycle and runtime-state diagrams still live in:

- [`docs/figures/mermaid_pipeline_planning_phase.mmd`](../../../docs/figures/mermaid_pipeline_planning_phase.mmd)
- [`docs/figures/mermaid_pipeline_boundaries.mmd`](../../../docs/figures/mermaid_pipeline_boundaries.mmd)
- [`docs/figures/mermaid_pipeline_request_flow.mmd`](../../../docs/figures/mermaid_pipeline_request_flow.mmd)
- [`docs/figures/mermaid_pipeline_request_sequence.mmd`](../../../docs/figures/mermaid_pipeline_request_sequence.mmd)
- [`docs/figures/mermaid_pipeline_session_state.mmd`](../../../docs/figures/mermaid_pipeline_session_state.mmd)
