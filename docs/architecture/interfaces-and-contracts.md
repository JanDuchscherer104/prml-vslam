# Interfaces And Contracts

This note is the human-facing architecture guide for the repository’s current
contract split after the offline/streaming refactor.

## Canonical Ownership

- `prml_vslam.interfaces`
  - repo-wide shared semantic DTOs such as `CameraIntrinsics`,
    `Observation`, `FrameTransform`, `PointCloud`, `PointMap`, and `DepthMap`
- `prml_vslam.protocols`
  - repo-wide behavior seams such as `OfflineSequenceSource`,
    `StreamingSequenceSource`, and `ObservationStream`
- `prml_vslam.pipeline`
  - run requests, plans, normalized sequence manifests, stage artifacts,
    provenance, runtime events, projected snapshots, and execution orchestration
- `prml_vslam.methods`
  - method ids, backend-private config, output policy, runtime updates, and
    thin wrapper integration around external SLAM systems
- `prml_vslam.alignment`
  - derived alignment contracts and services such as dominant-ground detection
    and viewer-scoped world alignment metadata
- `prml_vslam.sources`
  - source-stage config, runtime preparation, source-stage outputs, and
    prepared reference identifiers
  - prepared reference trajectories, prepared static reference clouds, and
    step-wise reference point-cloud sequence refs used by replay-style adapters
- `prml_vslam.visualization`
  - viewer/export policy plus the repo-owned Rerun integration layer
  - owns visualization config such as the optional viewer blueprint path, while
    the CLI remains responsible for auto-launching and supervising external
    viewer subprocesses

## Artifact And Raster Ownership

- `prml_vslam.interfaces.camera`
  - owns shared camera datamodels such as `CameraIntrinsics`
  - owns reusable camera-intrinsics artifact DTOs, such as a future
    `CameraIntrinsicsSeries`, when multiple packages consume the same
    per-frame or per-keyframe camera-model semantics
  - owns pure camera-model transforms such as crop/resize intrinsics updates
    when they are independent of a method's workflow policy
- `prml_vslam.methods.vista`
  - owns ViSTA-native artifact normalization, including conversion of native
    `intrinsics.npy` into typed repo artifacts
  - owns ViSTA preprocessing metadata, such as the source-raster to 224x224
    model-raster relationship needed to interpret estimated intrinsics
- `prml_vslam.eval`
  - owns typed intrinsics-comparison results if those residuals or statistics
    become persisted diagnostics or benchmark artifacts
  - no `evaluate.calibration` stage is implied until calibration metrics become
    a planned pipeline stage
- `prml_vslam.utils`
  - owns only generic low-level helpers such as color-preserving PLY IO or
    serialization primitives
  - does not own method-native semantics, artifact policy, or benchmark
    comparison results
- `prml_vslam.visualization`
  - owns Rerun validation DTOs and validation-bundle generation for `.rrd`
    viewer artifacts
- `prml_vslam.plotting`
  - owns figures only; it must not decide artifact semantics or raster-space
    policy

## Pipeline Center

The architectural center is an artifact-first pipeline with one public
orchestration model and two stage-execution strategies:

- batch/offline stage execution over a materialized `SequenceManifest`
- streaming stage execution over incremental `Observation` updates

The runtime truth is event-first:

- `RunEvent`
  - append-only semantic runtime record
- `RunSnapshot`
  - projection of those events
- `PipelineBackend`
  - execution substrate boundary consumed by CLI and Streamlit

The default execution substrate is Ray, but Ray does not own the public
contracts.

The shared offline source boundary is `SourceStageOutput`: a
`SequenceManifest` plus optional prepared benchmark inputs. Canonical
scientific artifacts remain TUM trajectories, PLY clouds, manifests, and stage
summaries. Normalized `.rrd` recordings are viewer/export artifacts, not the
scientific source of truth. Bulk arrays stay out of persisted/public contracts
and move through repo-owned opaque handles instead.

Source-stage visualization is represented by neutral `VisualizationItem`
values. The source stage may request logging of prepared reference trajectories
and reference clouds, but Rerun entity paths and SDK calls stay in the sink
policy.

Streaming method startup is intentionally symmetric with offline execution: a
backend session can receive the normalized `SequenceManifest`, optional
prepared benchmark inputs, and the selected reference baseline before the first
`Observation` arrives. That keeps dataset-backed replay logic, such as
reference-trajectory selection and Tango point-cloud forwarding, inside the
method layer instead of leaking dataset-specific hooks into the transport path.

Derived viewer/world-up alignment remains a separate repo-owned boundary. It
must produce explicit metadata and derived artifacts without mutating the native
SLAM artifact bundle in place.

## Pose And Transform Ownership

- `FrameTransform`
  - is the canonical rigid-transform DTO for runtime poses, dataset
    calibration, frame-graph edges, and visualization/export logic
  - defaults to the repo pose convention `world <- camera`
    (`T_world_camera`) for runtime pose use

- `PointCloud`, `PointMap`, and `DepthMap`
  - keep unstructured XYZ clouds, raster-aligned camera-local XYZ pointmaps,
    and metric depth rasters separate
  - carry explicit frame names, and carry `T_world_camera` or
    `T_world_frame` when the payload is world-placeable

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
