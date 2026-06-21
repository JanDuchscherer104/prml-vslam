#import "@preview/booktabs:0.0.4": toprule, midrule, bottomrule

= Benchmark Framework

The benchmark problem is to estimate camera motion and dense scene geometry from smartphone video
when intrinsics, metric scale, and the reference coordinate system cannot be assumed to be uniformly
available. This creates a framework problem before it becomes a leaderboard problem. A method output
cannot be interpreted from a rendered overlay alone: the source coordinate frame, pose convention,
sampling policy, depth units, trajectory alignment, and point-cloud registration all affect the
measured result.

The framework is organized around an artifact-first contract. A declarative run request is compiled
into a deterministic execution plan with ordered source, SLAM, alignment, evaluation,
reconstruction, and summary stages. The source stage produces a normalized sequence manifest and
optional benchmark references. The method stage consumes normalized observations and produces a
trajectory, dense geometry when available, and method-specific metadata. Downstream stages consume
those artifacts rather than rediscovering file layout or viewer state. Live runtime updates and
visualization records are useful for diagnosis, but terminal scientific evidence is the set of
persisted manifests, trajectories, clouds, alignment files, and metric tables.

#figure(
  table(
    columns: (0.9fr, 1.25fr, 1.7fr),
    align: (left, left, left),
    inset: (x: 0.26em, y: 0.23em),
    column-gutter: 0.38em,
    toprule(),
    table.header([Framework layer], [Contract], [Scientific role]),
    midrule(),
    [Source ingestion],
    [Normalized observations and prepared references],
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
    [Supports debugging while keeping rendered views separate from scientific truth.],
    bottomrule(),
  ),
  caption: [Main framework contracts used to make uncalibrated monocular VSLAM runs reproducible and comparable.],
) <fig:framework-contracts>

The framework currently supports offline replay for reproducible experiments and streaming execution
for the target use case. It includes dataset-backed sources for ADVIO and TUM RGB-D, live Record3D
ingestion, offline Record3D archive preparation, ViSTA-SLAM integration, optional MASt3R-SLAM
integration in CUDA environments, a LingBot-Map adapter, Rerun-based visualization, explicit
trajectory alignment and evaluation for prepared references, and ICP-based point-cloud placement.
Dense-cloud metric computation and efficiency evaluation are treated as validation gates rather than
as completed benchmark results. This boundary is important: the framework can document how a method
output is placed into a reference frame, but final method ranking requires the same frozen run matrix
for all selected datasets and methods.
