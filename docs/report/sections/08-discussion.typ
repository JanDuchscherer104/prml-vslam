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

The LingBot-Map adapter is not yet an upstream-parity streaming implementation. It buffers
repository streaming frames and emits no incremental updates until terminal inference; local runs use
memory-constrained settings such as a smaller model raster, fewer scale frames, interpolated
positional embeddings, and an unresolved profile mismatch between the documented windowed run and
the checked-in full configuration; fixed keyframe and window controls omit upstream's optional
flow-based keyframing; durable artifacts keep normalized poses, intrinsics, metadata, and a
downsampled depth-derived PLY, but not the upstream depth, confidence, point-map, sky-mask, viewer,
or attention/cache state needed for full auditability; and the point-head path remains disabled.
Consequently, LingBot dense-cloud diagnostics in this report measure the repository's
depth-backprojection contract rather than the full native LingBot output surface.

The limitation is that the final evidence matrix is local and artifact-scoped rather than a broad
statistical benchmark. It now includes matched trajectory medians, registered ADVIO provider
baselines, dense-cloud medians for TUM RGB-D and Record3D, render-based image diagnostics, and local
runtime telemetry. It still does not provide confidence intervals, hypothesis tests, a complete
LingBot cross-dataset trajectory table, ADVIO dense-cloud scores, or a hardware-normalized
efficiency study. The method-comparison language is therefore descriptive and local to this evidence
pass. Because preprocessing, sampling, and alignment choices can dominate monocular benchmark
results, the statistical unit for future claims remains the completed method--dataset--sequence run
under a fixed protocol.

The results support a cautious comparison rather than a single winner. MASt3R-SLAM gives the best
accuracy on short controlled RGB-D sequences and the best dense-cloud overlap where the reference
surface is clean. ViSTA-SLAM is less accurate in those medians but completed more long runs, which
matters for phone trajectories where a fixed keyframe buffer can turn accuracy into brittle
failure. ADVIO remains the hardest setting for both vision-only methods: the registered ARCore and
ARKit baselines show how much metric scale and gravity from phone sensor fusion help, while the
monocular methods lose orientation and local consistency. The ADVIO rotation values are additionally
qualified by the known gravity-lock gate issue in the local evaluation path, so they should be read
as evidence of a difficult phone-video regime and pipeline sensitivity, not as method-only
orientation accuracy.

Diagnostic visualization remains valuable but secondary. Rerun recordings expose frame mistakes,
scale errors, cloud-placement failures, and missing references @rerun2026. They should be read as
interactive projections of persisted artifacts; manifests, transform records, metric tables, and
source provenance carry the scientific claim.
