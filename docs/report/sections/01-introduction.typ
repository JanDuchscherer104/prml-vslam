= Introduction

Smartphone video is an attractive input modality for remote assistance because it is widely
available and can be captured by non-expert users. It is also a difficult input modality for
scientific benchmarking. A raw phone video does not necessarily provide a fixed calibration model,
metric scale, synchronized inertial state, or a stable world frame. In an emergency-call scenario,
the capture device should remain simple, while the computationally expensive trajectory estimation,
dense reconstruction, alignment, and visualization stages can run off-device on a workstation.

Recent dense monocular visual simultaneous localization and mapping (VSLAM) methods make this
setting increasingly plausible. ViSTA-SLAM avoids known intrinsics by estimating symmetric two-view
constraints and optimizing a Sim(3) pose graph @zhang2026vistaslam. MASt3R-SLAM uses learned
two-view pointmaps as geometric priors for real-time tracking and global optimization
@murai2025mast3rslam. LingBot-Map, based on the Geometric Context Transformer (GCT), instead treats
streaming reconstruction as causal long-range attention with anchor, local-window, and trajectory
memory contexts @chen2026gct. These methods differ in coordinate representation, memory model,
backend optimization, and dense-output semantics. A benchmark that treats their native outputs as
directly comparable risks measuring wrapper conventions rather than geometric quality.

This work therefore contributes a benchmark framework rather than a new SLAM algorithm. Its central
scientific role is to reduce the effort required to run, inspect, and later compare learned
uncalibrated monocular VSLAM methods on smartphone-like data. The framework normalizes public and
self-recorded sources into a shared observation representation, invokes method backends through a
common adapter boundary, records method-native and framework-normalized artifacts, and makes every
coordinate transformation part of the experimental record. This is the same kind of infrastructure
contribution made by framework papers such as Nerfstudio, which organizes data import, model
components, visualization, and export around extensible research interfaces @tancik2023nerfstudio,
and SLAMBench2, which defines comparable algorithm, dataset, and metric interfaces for SLAM
evaluation @bodin2018slambench2.

The paper makes three concrete contributions. First, it defines a source-normalization protocol for
ADVIO, TUM RGB-D, and Record3D data that preserves timestamps, intrinsics, reference trajectories,
depth-derived geometry, and provenance. Second, it specifies method and artifact contracts for
uncalibrated dense monocular reconstruction methods, separating method-native world frames from
benchmark reference frames. Third, it describes an alignment and evaluation protocol in which
Sim(3), gravity-aware alignment, and iterative closest point (ICP) registration are explicit
experimental choices rather than implicit post-processing. Quantitative method rankings require a
frozen experiment matrix and complete artifact-backed metric tables.

The corresponding research question is methodological: what information must be normalized,
persisted, and rejected so that future trajectory and dense-geometry numbers measure VSLAM behavior
rather than dataset layout, viewer transforms, or oracle post-processing? The paper answers this by
describing the coordinate-frame contract, admissible trajectory references, dense-cloud
preprocessing, and artifact completeness criteria. It does not claim statistical superiority of one
method over another.
