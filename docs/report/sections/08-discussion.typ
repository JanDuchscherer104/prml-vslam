= Discussion

The main contribution of the framework is to make comparability explicit. Learned monocular
reconstruction methods increasingly hide calibration, scale, correspondence, and mapping decisions
inside neural priors or learned state representations. This is useful for robustness, but it also
makes benchmark interpretation harder. A method-local world frame, a provider pose stream, a
motion-capture reference, and a viewer frame are different objects even when a 3D viewer can overlay
them convincingly. The framework's artifact contracts make those distinctions part of the
experimental record.

The three method families illustrate why a single wrapper convention is not enough. ViSTA-SLAM keeps
two-view predictions symmetric and local before pose-graph optimization, which is relevant for a
benchmark that does not want a model to choose an arbitrary first-view coordinate system at the
pairwise stage. MASt3R-SLAM uses a learned two-view geometric prior inside a classical SLAM
structure, so its accuracy depends on both pointmap prediction quality and the global optimization
that reconciles keyframes and loop closures. LingBot-Map moves the long-range structure into
attention: anchors, local context, and trajectory memory become the learned analogue of coordinate
grounding, local tracking, and global history. This supports streaming inference, but it also means
that coordinate commitment and memory compression are part of the method's failure surface.

The main limitation is the absence of a complete frozen benchmark matrix. The framework can
normalize sources, run method adapters, persist trajectories and clouds, compute trajectory
alignment for prepared references, and record diagnostic visualization. It does not provide a
validated cross-method leaderboard, dense-cloud metric tables, efficiency measurements, confidence
intervals, or hypothesis tests in this paper. This limitation should remain visible because
preprocessing, sampling, and alignment choices can dominate reported results in monocular benchmarks.
The correct statistical unit for future claims is the completed method-dataset-sequence run under a
fixed protocol; until that matrix exists, the paper should be read as a reproducibility and
measurement-protocol contribution.

Diagnostic visualization remains valuable, but it is not the primary source of scientific truth.
Rerun recordings make frame mistakes, scale errors, point-cloud placement, and missing references
easier to detect @rerun2026. They should be interpreted as interactive projections of persisted
artifacts. The report should therefore prioritize manifests, transform records, metric tables, and
source provenance over screenshots or subjective visual quality.
