# Interfaces And Contracts

This note is the human-facing architecture guide for the repository’s current
contract split after the offline/streaming refactor.

## Canonical Ownership

- `prml_vslam.interfaces`
  - repo-wide shared semantic DTOs such as `CameraIntrinsics`, `SE3Pose`,
    `FramePacket`, and `FrameTransform`
- `prml_vslam.protocols`
  - repo-wide behavior seams such as `OfflineSequenceSource`,
    `StreamingSequenceSource`, and `FramePacketStream`
- `prml_vslam.pipeline`
  - run requests, plans, normalized sequence manifests, stage artifacts,
    provenance, runner snapshots, and execution orchestration
- `prml_vslam.methods`
  - method ids, backend-private config, output policy, runtime updates, and
    thin wrapper integration around external SLAM systems
- `prml_vslam.benchmark`
  - benchmark-policy composition such as reference reconstruction and
    evaluation-stage enablement/baseline selection
- `prml_vslam.visualization`
  - viewer/export policy plus the repo-owned Rerun integration layer

## Pipeline Center

The architectural center is an artifact-first pipeline with two execution
strategies:

- offline: batch execution over a materialized `SequenceManifest`
- streaming: incremental execution over `FramePacket` updates

The shared offline boundary stays `SequenceManifest`. Canonical scientific
artifacts remain TUM trajectories, PLY clouds, manifests, and stage summaries.
Normalized `.rrd` recordings are viewer/export artifacts, not the scientific
source of truth.

## Pose And Transform Split

- `SE3Pose`
  - remains the canonical runtime pose DTO used by packet/session updates and
    trajectory helpers in this series
- `FrameTransform`
  - is the explicit frame-labelled transform DTO used for dataset calibration,
    frame-graph edges, and visualization/export logic

This keeps runtime pose churn low while still making static transform ownership
explicit at dataset and viewer boundaries.

## Wrapper Implications

- ViSTA-SLAM offline integration consumes a normalized `SequenceManifest`
  containing canonical `rgb_dir` and sidecar metadata.
- Method-specific preparation such as resizing, workspace layout, or native
  output import stays in `methods/vista`, not in shared ingest.
- Native upstream `.rrd` recordings may be preserved as method artifacts, but
  the repo-owned normalized Rerun schema is generated from repo-owned artifacts
  rather than by reinterpreting the upstream viewer tree.
