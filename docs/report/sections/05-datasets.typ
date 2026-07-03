#import "@preview/booktabs:0.0.4": bottomrule, midrule, toprule

= Datasets and Source Normalization

Source normalization prevents file layout, viewer settings, or dataset-specific axes from becoming
uncontrolled variables. Each adapter materializes images, timestamps, available intrinsics,
optional depth, optional camera poses, and provenance. Prepared references are stored separately
from method inputs so that ground-truth trajectories or depth maps cannot be consumed silently as
ordinary observations.

ADVIO contributes smartphone trajectory evidence: iPhone RGB video, visual-inertial trajectory
references, and mobile-provider pose streams @cortes2018advio. Provider poses and ground truth are
kept as explicit references or baselines; their native frames are not assumed to coincide with
method-local SLAM worlds. Because no source-prepared dense reference cloud is published for ADVIO
here, dense-cloud metrics require a separately documented reference reconstruction.

ADVIO trajectories are transformed before entering the normalized datastore. The source data and
fixpoint convention follow the ADVIO paper and repository; the persisted trajectories use this
repository's right-down-forward (RDF) basis @cortes2018advio @aaltovisionAdvioRepo. Raw ADVIO pose
coordinates are converted by

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

ADVIO fixpoints are time-position constraints, consistent with the dataset's manual position fixes
and the official fixpoint visualization @cortes2018advio @aaltovisionAdvioRepo. For each source
$s in {"GT", "ARCore", "ARKit"}$, the store interpolates the RDF trajectory at matched fixpoint
times and estimates a no-scale registration into the common fixedpoint frame:

$
  (bold(R)_s^*, bold(t)_s^*) =
  op("arg min", limits: #true)_(bold(R) in "SO"(3), bold(t)) sum_i
  norm(bold(f)_i - (bold(R) bold(x)_s (t_i) + bold(t)))^2 .
$

If that rigid fit would tilt gravity beyond the configured gate, the same least-squares objective is
solved with $bold(R)$ restricted to yaw about RDF gravity. Registered trajectories are then cropped
to the common provider interval and rebased once by the ground-truth pose at the common start time,

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

The resulting target frame is `advio_fixedpoint_common_start_local`. ARCore and ARKit are benchmark
candidates only in this registered frame. Post-hoc GT-aligned ARCore/ARKit files are diagnostics,
not method candidates.

TUM RGB-D provides synchronized color, registered depth, camera intrinsics, and motion-capture
trajectories @sturm2012benchmark. It supplies controlled RGB replay for monocular methods and
deterministic depth-derived reference geometry for alignment diagnostics. Native motion-capture
provenance is preserved while observations are converted into the common camera-frame convention.

TUM RGB-D and Record3D use a different normalization because their replay and reference geometry are
already tied to a single provider trajectory. Their stored camera poses are first-pose-relative,

$
  bold(T)'_k = (bold(T)_0)^(-1) bold(T)_k,
$

so the first observation becomes the local world-frame anchor. This matches the TUM RGB-D loading
convention used by the upstream ViSTA-SLAM dataset adapter, while keeping the raw motion-capture or
provider world only as provenance @zhang2026vistaslamRepo.

Record3D supplies the custom smartphone-data path. The live path streams iPhone RGB-D observations;
the archive path prepares self-recorded RGB frames, depth maps, ARKit poses, and depth-derived
reference clouds @record3d2026. Record3D references are provider trajectories rather than
laboratory ground truth, so they should be reported as mobile-device references unless an
independent validation path is added.

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

The normalized datastore used for the final evidence pass covers all three source families. The
coverage summary in @tab:dataset-coverage is derived from the checked-in
`docs/figures/evidence/dataset-summary.csv` artifact used by the final slide deck. ADVIO dominates
duration because it contains longer pedestrian phone trajectories, while TUM RGB-D supplies more
controlled RGB-D sequences and Record3D supplies a smaller custom smartphone set with depth and
ARKit provider poses.

#figure(
  table(
    columns: (0.7fr, 0.55fr, 0.75fr, 0.75fr),
    align: (left, right, right, right),
    inset: (x: 0.24em, y: 0.22em),
    toprule(),
    table.header([Dataset], [Sequences], [Total duration (min)], [Mean duration (s)]),
    midrule(),
    [ADVIO], [23], [67.8], [177.0],
    [TUM RGB-D], [19], [19.6], [61.9],
    [Record3D], [8], [13.8], [103.8],
    bottomrule(),
  ),
  caption: [Normalized datastore coverage used to frame the final benchmark evidence.],
) <tab:dataset-coverage>

The normalized datastore separates persistent source materialization from run-local sampling.
Full-frame payloads are prepared once for a dataset, sequence, and source profile; later runs select
frame stride or target frame rate without rebuilding the source entry. The metric record must still
trace every sampled run to the same normalized source evidence.
