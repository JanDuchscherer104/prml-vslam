#import "@preview/booktabs:0.0.4": bottomrule, midrule, toprule

= Datasets and Source Normalization

Source normalization is the main protection against accidental benchmark leakage from file layout,
viewer appearance, or dataset-specific conventions. Each source adapter materializes a normalized
sequence with image payloads, timestamps, intrinsics when available, optional depth, optional camera
poses, and provenance. Prepared benchmark inputs are stored separately from the primary observation
sequence so that a method cannot silently consume a ground-truth trajectory or depth map as input
when those data are intended only for evaluation.

ADVIO is the public smartphone-oriented trajectory dataset used by the framework. It contains iPhone
RGB video, visual-inertial trajectory references, and mobile-provider pose streams
@cortes2018advio. The benchmark uses ADVIO primarily as trajectory evidence. Provider poses and
ground-truth trajectories are kept as explicit references or baselines, and their native frames are
not assumed to coincide with method-local SLAM worlds. Since ADVIO does not provide a source-prepared
dense reference cloud in the current framework, dense-cloud metrics are not inferred from ADVIO
unless a separate reference reconstruction is prepared and documented.

The ADVIO trajectory publication path applies the dataset-specific transforms before artifacts enter
the normalized datastore. The source data and fixpoint convention follow the ADVIO dataset paper and
repository, while the final RDF publication frame is the benchmark convention used by this framework
@cortes2018advio @aaltovisionAdvioRepo. Raw ADVIO pose coordinates are first expressed in the
repository's right-down-forward (RDF) basis,

$
  bold(B)_"advio" =
  mat(0, 0, 1; 0, -1, 0; 1, 0, 0).
$

Positions and rotations are transformed by

$
  bold(p)^"rdf" = bold(B)_"advio" bold(p)^"raw",
  quad
  bold(R)^"rdf" =
  bold(B)_"advio" bold(R)^"raw" bold(B)_"advio"^(-1).
$

ADVIO fixpoints are treated as time-position constraints, consistent with the dataset description of
manual position fixes used by the ground-truth track optimizer and with the official repository's
fixpoint visualization @cortes2018advio @aaltovisionAdvioRepo. For each source
$s in {"GT", "ARCore", "ARKit"}$, the store interpolates the RDF trajectory at the matched
fixpoint times and estimates a no-scale registration into the common fixedpoint frame:

$
  (bold(R)_s^*, bold(t)_s^*) =
  arg min_(bold(R) in "SO"(3), bold(t)) sum_i
  norm(bold(f)_i - (bold(R) bold(x)_s(t_i) + bold(t)))^2 .
$

If that rigid fit would tilt the gravity axis beyond the configured gate, the repository uses the
same least-squares objective with $bold(R)$ restricted to yaw about RDF gravity. The registered
trajectories are then cropped to the common provider interval and rebased once by the ground-truth
pose at the common start time,

$
  t_0 = max_s min cal(T)_s,
  quad
  t_1 = min_s max cal(T)_s.
$

For $t in [t_0, t_1]$, the published pose is

$
  bold(T)^"local"_"c,s" (t) =
  (bold(T)^"fix"_"c,GT" (t_0))^(-1) bold(T)^"fix"_"c,s" (t).
$

This produces a single `advio_fixedpoint_common_start_local` target frame. ARCore and ARKit remain
benchmark candidates only in this registered frame; additionally aligned `*_aligned_to_gt.tum`
artifacts are retained as diagnostics and are not method candidates.

TUM RGB-D provides controlled RGB-D sequences with registered depth, camera intrinsics, and
motion-capture trajectories @sturm2012benchmark. In this framework, it is the controlled public
source used to validate trajectory and dense-reference preparation because it can generate both
monocular RGB replay for methods and deterministic depth-derived reference geometry for alignment
diagnostics. The framework preserves the native motion-capture provenance while normalizing the
camera observations into the common camera-frame convention used by downstream stages.

TUM RGB-D and Record3D use a different normalization because their replay and reference geometry are
already tied to a single provider trajectory. Their stored camera poses are first-pose-relative,

$
  bold(T)'_k = (bold(T)_0)^(-1) bold(T)_k,
$

so the first observation becomes the local world-frame anchor. This matches the TUM RGB-D loading
convention used by the upstream ViSTA-SLAM dataset adapter, while keeping the raw motion-capture or
provider world only as provenance @zhang2026vistaslamRepo.

Record3D supplies the custom smartphone-data path. The live path streams iPhone RGB-D observations,
while the offline archive path prepares self-recorded scenes with RGB frames, depth maps, ARKit
poses, and depth-derived reference clouds @record3d2026. This makes Record3D the bridge between
controlled public benchmarks and the intended capture setting. Its reference trajectories are
provider trajectories rather than laboratory ground truth, so they should be reported as mobile
device references and not as absolute ground-truth trajectories unless an independent validation path
is added.

#figure(
  table(
    columns: (0.6fr, 1.45fr, 1.45fr),
    align: (left, left, left),
    inset: (x: 0.24em, y: 0.22em),
    column-gutter: 0.38em,
    toprule(),
    table.header([Dataset], [Normalized source], [Reference role]),
    midrule(), [ADVIO], [RGB frames, timestamps, calibration metadata, fixedpoints, and provider poses.],
    [Fixedpoint-registered trajectory references and provider baselines; no source-prepared dense cloud.],
    [TUM RGB-D],
    [RGB frames, registered depth, timestamps, and intrinsics.],

    [Motion-capture trajectory and registered-depth reference cloud for controlled validation.],
    [Record3D],
    [Live or archived iPhone RGB-D with intrinsics, depth, and ARKit poses.],

    [Provider trajectory and depth-derived cloud; not laboratory ground truth.], bottomrule(),
  ),
  caption: [Dataset information preserved by source normalization before methods are executed.],
) <tab:dataset-structures>

The normalized dataset store separates persistent source materialization from run-local sampling.
Full-frame payloads can be prepared once for a dataset, sequence, and source profile; later runs then
select frame stride or target frame rate without rebuilding the underlying source entry. This
separation matters for method comparison because a slow method may require a different runtime
sampling policy, but the benchmark should still be able to trace both runs back to the same
normalized source evidence.
