#import "@preview/booktabs:0.0.4": bottomrule, midrule, toprule

= Datasets and Source Normalization

The benchmark deliberately combines three dataset families rather than treating source data as
interchangeable video streams. ADVIO stresses deployment-realistic pedestrian smartphone video and
provider visual-inertial odometry (VIO) baselines. TUM RGB-D provides a controlled indoor RGB-D
benchmark with motion-capture trajectory references and registered depth. Custom Record3D captures
exercise the target smartphone ingestion path with iPhone RGB-D archives, ARKit poses, and
depth-derived clouds. This combination separates three questions: whether monocular methods survive
phone-video trajectories, whether the geometry pipeline behaves under a controlled RGB-D reference,
and whether the repository-owned capture path is end-to-end reproducible on target-domain data.

Source normalization prevents file layout, viewer settings, image geometry, intrinsics, depth
units, timestamp association, coordinate-frame conventions, and reference leakage from becoming
uncontrolled variables. Each adapter materializes images, timestamps, available intrinsics,
optional depth, optional camera poses, and provenance. Prepared references are stored separately
from method inputs so that ground-truth trajectories or depth maps cannot be consumed silently as
ordinary observations.

ADVIO contributes 23 pedestrian smartphone recordings spanning about 4.47 km and 1 h 8 min, with
19 indoor and 4 outdoor sequences @cortes2018advio. In this repository it provides iPhone RGB
video, timestamps, calibration metadata, manual fixpoints, the ADVIO ground-truth trajectory, and
optional ARKit and ARCore provider pose streams. The ADVIO reference is an inertial-navigation
estimate constrained by manual position fixes, while ARKit and ARCore are mobile-provider baselines
rather than hidden method inputs. Because no source-prepared dense reference cloud is published for
ADVIO here, dense-cloud metrics require a separately documented reference reconstruction.

ADVIO trajectories are transformed before entering the normalized datastore because the ground
truth, ARCore, and ARKit streams do not start in a common provider world. Direct provider-world
overlays would therefore not be valid trajectory comparisons. The source data and fixpoint
convention follow the ADVIO paper and repository; the persisted trajectories use this repository's
right-down-forward (RDF) basis @cortes2018advio @aaltovisionAdvioRepo. Raw ADVIO pose coordinates
are converted by

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
not method candidates. The yaw-restricted fit also anticipates the trajectory-evaluation constraint
for near-planar phone paths: allowing arbitrary roll or pitch can make a flat path align
geometrically while violating the source up direction.

TUM RGB-D provides synchronized color, registered depth, camera intrinsics, and high-accuracy
motion-capture trajectories @sturm2012benchmark. The official capture setup records Kinect RGB-D at
30 Hz and 640x480 resolution, with motion-capture ground truth at 100 Hz. Its RGB and depth images
are pre-registered one-to-one, and 16-bit depth PNG values use a scale factor of 5000, so the
normalized adapter can create deterministic metric reference clouds from the same selected RGB-D
frames used as method input. The final evidence pass uses 19 ViSTA-oriented Freiburg sequences
covering handheld SLAM, testing/debugging, and 3D object-reconstruction categories.

Record3D supplies the custom smartphone-data path. The current catalog contains eight archived
`.r3d` recordings. The archive metadata provides RGB and depth raster sizes, camera intrinsics,
frame timestamps, and ARKit poses; each frame stores RGB, metric depth, and confidence payloads. The
normalized archive path prepares RGB-D observations, an ARKit provider trajectory, and a
depth-derived reference cloud @record3d2026. These references are mobile-device provider
references, not laboratory ground truth.

TUM RGB-D and Record3D use a different normalization from ADVIO because their replay and reference
geometry are already tied to one selected observation stream. Their stored camera poses are
first-pose-relative,

$
  bold(T)'_k = (bold(T)_0)^(-1) bold(T)_k,
$

so the first observation becomes the local world-frame anchor. This matches the TUM RGB-D loading
convention used by the upstream ViSTA-SLAM dataset adapter, while keeping the raw motion-capture or
provider world only as provenance @zhang2026vistaslamRepo. The distinction matters: ADVIO needs
cross-provider fixedpoint registration before comparison, whereas TUM RGB-D and Record3D need a
local SLAM-compatible origin for one reference stream.

#figure(
  [
    #set text(size: 7.6pt)
    #table(
      columns: (0.56fr, 1.34fr, 1.6fr),
      align: (left, left, left),
      inset: (x: 0.22em, y: 0.2em),
      column-gutter: 0.32em,
      toprule(),
      table.header([Dataset], [Role and source modalities], [Reference, frame, and caveat]),
      midrule(),
      [ADVIO],
      [Deployment-realistic smartphone trajectory stress test with iPhone RGB video, timestamps,
        calibration, fixpoints, and optional ARKit/ARCore provider poses.],
      [INS plus manual-fixpoint ground-truth trajectory; ARKit/ARCore baselines in
        `advio_fixedpoint_common_start_local` after RDF conversion and fixedpoint registration. No
        source-prepared dense cloud.],
      [TUM RGB-D],
      [Controlled indoor RGB-D and mocap benchmark anchor with Kinect RGB-D at 30 Hz / 640x480,
        registered depth, timestamps, and intrinsics.],
      [Motion-capture trajectory and registered-depth cloud in the first-camera RDF frame, relative
        to the first ground-truth pose. Controlled indoor scenes, not phone video.],
      [Record3D],
      [Target-domain custom smartphone capture validation with archived iPhone `.r3d` RGB, depth,
        confidence, intrinsics, timestamps, and ARKit poses.],
      [ARKit provider trajectory and depth-derived cloud in first-pose-relative `record3d_world`.
        Depth is available, but references are provider estimates rather than lab ground truth.],
      bottomrule(),
    )
  ],
  placement: auto,
  scope: "parent",
  caption: [Dataset roles, modalities, references, frame contracts, and caveats preserved by source normalization before methods are executed.],
) <tab:dataset-structures>

#figure(
  grid(
    columns: (1fr, 1fr, 1fr),
    gutter: 0.45em,
    [
      #image("../../figures/evidence/dataset-gt-advio.png", width: 100%)
      #par(justify: false)[#text(size: 7.2pt)[ADVIO: fixedpoint-registered pedestrian phone trajectories.]]
    ],
    [
      #image("../../figures/evidence/dataset-gt-tum-rgbd.png", width: 100%)
      #par(justify: false)[#text(size: 7.2pt)[TUM RGB-D: registered-depth reference cloud and mocap trajectory.]]
    ],
    [
      #image("../../figures/evidence/dataset-gt-record3d.png", width: 100%)
      #par(justify: false)[#text(size: 7.2pt)[Record3D: iPhone depth-derived cloud and ARKit provider trajectory.]]
    ],
  ),
  caption: [Qualitative dataset coverage: trajectory-only ADVIO, controlled RGB-D TUM reference geometry, and target-domain Record3D smartphone RGB-D capture.],
) <fig:dataset-qualitative-coverage>

The normalized datastore used for the final evidence pass covers all three source families. The
coverage summary in @tab:dataset-coverage is derived from the checked-in
`docs/figures/evidence/dataset-summary.csv` artifact and from the current normalized
`stats_long.csv` entries. ADVIO dominates total duration because it contains longer pedestrian
phone trajectories. TUM RGB-D supplies short controlled RGB-D scenes with full depth coverage.
Record3D supplies a smaller custom smartphone set with depth and ARKit provider poses; its full
normalized-store trajectory range includes a long provider-path outlier and should not be conflated
with the matched-scene ranges reported later for method comparisons.

#figure(
  [
    #set text(size: 7.8pt)
    #table(
      columns: (0.68fr, 0.46fr, 0.76fr, 1.16fr, 1.16fr),
      align: (left, right, right, right, right),
      inset: (x: 0.22em, y: 0.2em),
      column-gutter: 0.3em,
      toprule(),
      table.header(
        [Dataset],
        [Seq.],
        [Total (min)],
        [Duration: mean; median/range (s)],
        [Path median/range (m); depth cov.],
      ),
      midrule(),
      [ADVIO], [23], [67.8], [177.0; 151.6 / 51.7-385.6], [140.3 / 19.5-486.8; 0.0],
      [TUM RGB-D], [19], [19.6], [61.9; 46.3 / 20.4-172.7], [14.1 / 2.6-22.2; 1.0],
      [Record3D], [8], [13.8], [103.8; 103.2 / 33.9-173.9], [129.2 / 43.5-1028.2; 1.0],
      bottomrule(),
    )
  ],
  placement: auto,
  scope: "parent",
  caption: [Normalized datastore coverage for the final evidence pass. Durations summarize manifest timestamps; path lengths summarize prepared reference trajectories; depth coverage is the ratio of selected observation frames with depth payloads.],
) <tab:dataset-coverage>

The normalized datastore separates persistent source materialization from run-local sampling.
Full-frame payloads are prepared once for a dataset, sequence, and source profile; later runs select
frame stride or target frame rate without rebuilding the source entry. The source profile encodes
byte-affecting choices such as stored frame selection, RGB resizing, intrinsics scaling, pose-frame
mode, and reference-cloud sampling. Runtime sampling records selected indices and timestamps against
the immutable normalized entry, and the metric record must trace every sampled run to that source
evidence.

The dataset disclosure for this report is therefore an evaluation-corpus disclosure rather than a
training split description. Each source family is reported with its provenance, access path,
capture hardware, modalities, sampling rate or resolution where applicable, sequence count,
duration, scene category, reference source, reference limitations, and normalization frame. Missing
or corrupt local data are handled at source preparation time by explicit failures rather than
silent fallback, and reference trajectories or clouds remain physically separated from method
observations throughout the artifact contract.
