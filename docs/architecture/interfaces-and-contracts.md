# Interfaces And Contracts

This note is the human-facing architecture guide for the repository’s current
contract split after the offline/streaming refactor.

## Canonical Ownership

- `prml_vslam.interfaces`
  - repo-wide shared semantic DTOs such as `CameraIntrinsics`,
    `FramePacket`, and `FrameTransform`
- `prml_vslam.protocols`
  - repo-wide behavior seams such as `OfflineSequenceSource`,
    `StreamingSequenceSource`, and `FramePacketStream`
- `prml_vslam.pipeline`
  - run requests, plans, normalized sequence manifests, stage artifacts,
    provenance, runtime events, projected snapshots, and execution orchestration
- `prml_vslam.methods`
  - method ids, backend-private config, output policy, runtime updates, and
    thin wrapper integration around external SLAM systems
- `prml_vslam.alignment`
  - derived alignment contracts and services such as dominant-ground detection
    and viewer-scoped world alignment metadata
- `prml_vslam.benchmark`
  - benchmark-policy composition such as reference reconstruction and
    evaluation-stage enablement/baseline selection
  - prepared reference trajectories, prepared static reference clouds, and
    step-wise reference point-cloud sequence refs used by replay-style adapters
- `prml_vslam.visualization`
  - viewer/export policy plus the repo-owned Rerun integration layer
  - owns visualization config such as the optional viewer blueprint path, while
    the CLI remains responsible for auto-launching and supervising external
    viewer subprocesses

## Pipeline Center

The architectural center is an artifact-first pipeline with one public
orchestration model and two stage-execution strategies:

- batch/offline stage execution over a materialized `SequenceManifest`
- streaming stage execution over incremental `FramePacket` updates

The runtime truth is event-first:

- `RunEvent`
  - append-only semantic runtime record
- `RunSnapshot`
  - projection of those events
- `PipelineBackend`
  - execution substrate boundary consumed by CLI and Streamlit

The default execution substrate is Ray, but Ray does not own the public
contracts.

The shared offline boundary stays `SequenceManifest`. Canonical scientific
artifacts remain TUM trajectories, PLY clouds, manifests, and stage summaries.
Normalized `.rrd` recordings are viewer/export artifacts, not the scientific
source of truth. Bulk arrays stay out of persisted/public contracts and move
through repo-owned opaque handles instead.

Streaming method startup is intentionally symmetric with offline execution: a
backend session can receive the normalized `SequenceManifest`, optional
prepared benchmark inputs, and the selected reference baseline before the first
`FramePacket` arrives. That keeps dataset-backed replay logic, such as mock
reference-trajectory and Tango point-cloud forwarding, inside the method layer
instead of leaking dataset-specific hooks into the transport path.

Derived viewer/world-up alignment remains a separate repo-owned boundary. It
must produce explicit metadata and derived artifacts without mutating the native
SLAM artifact bundle in place.

## Pose And Transform Ownership

- `FrameTransform`
  - is the canonical rigid-transform DTO for runtime poses, dataset
    calibration, frame-graph edges, and visualization/export logic
  - defaults to the repo pose convention `camera -> world` for runtime pose use

This keeps rigid-transform math in one place while preserving explicit frame
labels at package boundaries.

## Wrapper Implications

- ViSTA-SLAM offline integration consumes a normalized `SequenceManifest`
    containing canonical `rgb_dir` and sidecar metadata.
  - Method-specific preparation such as resizing, workspace layout, or native
    output import stays in `methods/vista`, not in shared ingest.
  - The repository ships repo-owned observer sinks for JSONL events and Rerun
    output. Native upstream `.rrd` recordings may still be preserved as
    additional visualization-owned artifacts.
