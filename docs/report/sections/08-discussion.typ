= Discussion

The central contribution is explicit comparability. Learned monocular reconstruction methods often
hide calibration, scale, correspondence, and mapping decisions inside neural priors or learned state
representations. That can improve robustness, but it complicates interpretation: a method-local
world frame, provider pose stream, motion-capture reference, and viewer frame are different objects
even when a 3D viewer overlays them convincingly.

The three method families illustrate why a single wrapper convention is not enough. ViSTA-SLAM keeps
two-view predictions symmetric and local before pose-graph optimization, which is relevant for a
benchmark that does not want a model to choose an arbitrary first-view coordinate system at the
pairwise stage. MASt3R-SLAM uses a learned two-view geometric prior inside a classical SLAM
structure, so its accuracy depends on both pointmap prediction quality and the global optimization
that reconciles keyframes and loop closures. LingBot-Map moves the long-range structure into
attention: anchors, local context, and trajectory memory become the learned analogue of coordinate
grounding, local tracking, and global history. This supports streaming inference, but it also means
that coordinate commitment and memory compression are part of the method's failure surface.

The limitation is the absence of a complete frozen benchmark matrix. The implementation can
normalize sources, run method adapters, persist trajectories and clouds, align prepared references,
and record diagnostic visualization. It does not yet provide a validated cross-method leaderboard,
dense-cloud metric tables, efficiency measurements, confidence intervals, or hypothesis tests.
Because preprocessing, sampling, and alignment choices can dominate monocular benchmark results, the
statistical unit for future claims must be the completed method--dataset--sequence run under a fixed
protocol.

Diagnostic visualization remains valuable but secondary. Rerun recordings expose frame mistakes,
scale errors, cloud-placement failures, and missing references @rerun2026. They should be read as
interactive projections of persisted artifacts; manifests, transform records, metric tables, and
source provenance carry the scientific claim.
