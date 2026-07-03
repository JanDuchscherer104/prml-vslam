// RESPONSIBLIY: JAN (full-section)
#import "@preview/booktabs:0.0.4": bottomrule, midrule, toprule

= Benchmark Framework
The benchmark framework addresses camera-motion and dense-scene-geometry estimation from
smartphone video when intrinsics, metric scale, and the reference coordinate system are not
uniformly available. A rendered overlay is insufficient evidence: the source frame, pose
convention, sampling policy, depth units, trajectory alignment, and point-cloud registration
determine the measured quantity.

A declarative run request is compiled into ordered source, SLAM, alignment, evaluation,
reconstruction, and summary stages. The source stage emits a normalized sequence manifest and
optional references. The method stage consumes normalized observations and emits a trajectory,
dense geometry when available, and method metadata. Downstream stages consume these artifacts
instead of rediscovering paths or viewer state. Scientific evidence is the persisted set of
manifests, trajectories, clouds, alignment files, and metric tables; live visualization remains
diagnostic.

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

The implemented surface covers offline replay, streaming Record3D capture, ADVIO and TUM RGB-D
sources, Record3D archive preparation, ViSTA-SLAM, optional CUDA-backed MASt3R-SLAM,
LingBot-Map, Rerun visualization, trajectory evaluation, and ICP-based cloud placement. The final
report includes selected local trajectory, dense-cloud, render-diagnostic, and runtime evidence
from available artifacts. Those numbers remain artifact-scoped diagnostics; broad cross-method
claims still require a frozen method--dataset matrix, sampling policy, and metric artifact set for
all compared methods.
