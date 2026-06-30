= Introduction

Smartphone video is attractive for remote assistance because it is ubiquitous and easy to capture.
It is difficult to benchmark scientifically. A phone recording may lack a stable calibration model,
metric scale, synchronized inertial state, or globally meaningful world frame. In the intended
off-device setting, the phone remains a simple sensor while trajectory estimation, dense
reconstruction, alignment, and visualization run on a workstation.

Recent dense monocular visual simultaneous localization and mapping (VSLAM) methods make this
setting increasingly plausible. ViSTA-SLAM avoids known intrinsics by estimating symmetric two-view
constraints and optimizing a Sim(3) pose graph @zhang2026vistaslam. MASt3R-SLAM uses learned
two-view pointmaps as geometric priors for real-time tracking and global optimization
@murai2025mast3rslam. LingBot-Map, based on the Geometric Context Transformer (GCT), instead treats
streaming reconstruction as causal long-range attention over anchor, local-window, and trajectory
memory contexts @chen2026gct. These systems differ in coordinate representation, memory model,
optimization structure, and dense-output semantics. Directly comparing their native outputs risks
measuring adapter conventions instead of geometric quality.

This paper therefore specifies a measurement substrate, not a new SLAM method. It normalizes public
and self-recorded sources into a shared observation representation, invokes method backends through
a common adapter boundary, records method-native and benchmark-facing artifacts, and makes each
coordinate transformation part of the experimental record.

The contributions are threefold. First, the source contract preserves timestamps, intrinsics,
reference trajectories, depth-derived geometry, and provenance for ADVIO, TUM RGB-D, and Record3D.
Second, the method contract separates method-native world frames from benchmark reference frames for
uncalibrated dense monocular reconstruction. Third, the evaluation contract makes Sim(3),
gravity-aware trajectory placement, and iterative closest point (ICP) registration explicit choices.
The methodological question is what must be normalized, persisted, and rejected so that later
trajectory and dense-geometry measurements reflect VSLAM behavior rather than dataset layout,
viewer transforms, or oracle post-processing.
