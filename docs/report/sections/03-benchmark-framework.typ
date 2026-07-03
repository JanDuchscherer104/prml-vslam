// RESPONSIBILITY: JAN (full-section)
#import "@preview/booktabs:0.0.4": bottomrule, midrule, toprule

= Benchmark Framework
The benchmark framework addresses camera-motion and dense-scene-geometry estimation from
smartphone video when intrinsics, metric scale, and the reference coordinate system are not
uniformly available. A rendered overlay is insufficient evidence: the source frame, pose
convention, sampling policy, depth units, trajectory alignment, and point-cloud registration
determine the measured quantity. The runtime boundary is therefore methodological, not cosmetic:
concurrent stages exchange typed results, artifacts, and transient payload references so large
frame and depth payloads do not dominate measured SLAM behavior, while live Rerun visualization
remains an observer path for demos and debugging.

A declarative run request is compiled into ordered source and SLAM stages followed by configured
gravity, trajectory, or cloud alignment, trajectory evaluation, reconstruction, image diagnostics,
and summary stages; dense-cloud evaluation is diagnostic unless explicit metric artifacts exist.
The source stage emits a normalized sequence manifest and prepared references, while the method
stage emits benchmark-facing trajectories, dense geometry when available, and metadata.
Downstream stages consume canonical artifacts such as `input/sequence_manifest.json`,
`benchmark/inputs.json`, `slam/trajectory.tum`, `evaluation/trajectory/metrics_long.csv`,
`summary/run-events.jsonl`, and `summary/stage_manifests.json`, rather than viewer state or
rediscovered paths. The contracts in @fig:framework-contracts define the reproducibility boundary:
metrics remain tied to their reference, alignment policy, and stage provenance.

#figure(
  table(
    columns: (0.9fr, 1.25fr, 1.7fr),
    align: (left, left, left),
    inset: (x: 0.26em, y: 0.23em),
    column-gutter: 0.38em,
    toprule(),
    table.header([Framework layer], [Contract], [Scientific role]),
    midrule(), [Source ingestion], [Normalized observations and prepared references],
    [Binds each frame to timestamps, intrinsics, optional depth, poses, and provenance.],
    [Method adapter],
    [Standard trajectory and dense-geometry outputs],

    [Separates method-native outputs from benchmark-facing artifacts.],
    [Transform record],
    [Frame-labelled alignment artifacts],

    [Makes scale, gravity, yaw, and cloud-placement choices reproducible.],
    [Evaluation record],
    [Metric manifests and long-form rows],

    [Prevents metric values from being detached from their reference and alignment policy.],
    [Visualization],
    [Viewer recordings and neutral visualization items],

    [Supports debugging while keeping rendered views separate from metric records.], bottomrule(),
  ),
  caption: [Main framework contracts used to make uncalibrated monocular VSLAM runs reproducible and comparable.],
) <fig:framework-contracts>

The implemented surface covers offline replay, live Record3D capture, ADVIO and TUM RGB-D
sources, Record3D archive preparation, ViSTA-SLAM, optional CUDA-backed MASt3R-SLAM, LingBot-Map,
Rerun visualization, trajectory evaluation, reconstruction, and ICP-based cloud placement.
Streaming can replay datasets in real time or as fast as possible and can ingest live Record3D
frames over USB or Wi-Fi preview. Live status reports processed frames, accepted keyframes, rolling
frame rate, keyframes-per-second throughput, and latency; durable SLAM outcomes preserve frame,
keyframe, point-count, and artifact records. Runtime rates and rendered views are therefore
run-scoped diagnostics unless archived, and broad method claims still require a frozen
method--dataset matrix, sampling policy, and metric artifact set.
