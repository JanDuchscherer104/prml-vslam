// RESPONSIBLIY: JAN (full-section)
#import "@preview/booktabs:0.0.4": bottomrule, cmidrule, midrule, toprule

= Datasets and Source Normalization

The benchmark deliberately uses three dataset families to separate three different sources of
evidence rather than treating all videos as interchangeable source streams. ADVIO is the
deployment-realistic smartphone visual-inertial odometry (VIO) stress test: it asks whether
monocular methods and provider baselines survive pedestrian phone trajectories in real public
spaces. TUM RGB-D is the controlled indoor RGB-D and motion-capture anchor: it asks whether the
geometry and trajectory-evaluation pipeline behaves correctly when synchronized color, registered
depth, and laboratory trajectory references are available. Custom Record3D captures are the
target-domain ingestion check: they ask whether the repository-owned smartphone capture path can
materialize RGB-D observations, ARKit poses, and depth-derived reference geometry end to end on
data recorded with the same class of device targeted by the project.

Source normalization exists to make those comparisons about methods and source families, not about
incidental file layout or viewer conventions. The adapters materialize a common observation
contract with RGB payloads, timestamps, intrinsics, optional metric depth, optional camera poses,
and provenance. Byte-affecting choices such as RGB resizing, intrinsics scaling, frame selection,
pose-frame mode, and reference-cloud sampling are encoded in the source profile, while run-local
sampling is recorded separately. Prepared references are stored outside method observations so that
ground-truth trajectories or depth maps cannot be consumed silently as ordinary inputs.

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


ADVIO contributes 23 pedestrian smartphone recordings spanning about 4.47 km and 1 h 8 min, with
19 indoor and 4 outdoor sequences @cortes2018advio. The original capture rig included an iPhone 6s,
a Google Pixel, and a Google Tango device; this repository uses the iPhone RGB video, frame
timestamps, calibration metadata, manual fixpoints, the ADVIO ground-truth trajectory, and optional
ARKit and ARCore provider pose streams @cortes2018advio @aaltovisionAdvioRepo. The sequences include
realistic public-space motion in offices, malls, metro stations, stairs, elevators, escalators,
multi-floor paths, and outdoor areas. ADVIO therefore contributes deployment realism, long
pedestrian trajectories, and provider VIO baselines, but it is trajectory-only in this repository:
no source-prepared dense reference cloud is published for ADVIO here, so dense-cloud metrics require
a separately documented reference reconstruction.

ADVIO trajectories are transformed before entering the normalized datastore because the ground
truth, ARCore, and ARKit streams do not start in a common provider world. Direct provider-world
overlays would therefore not be valid trajectory comparisons. The source data and fixpoint
convention follow the ADVIO paper and repository; the persisted trajectories use this repository's
right-down-forward (RDF) basis and the `advio_fixedpoints.py` fixedpoint-registration policy
@cortes2018advio @aaltovisionAdvioRepo. Raw ADVIO pose coordinates are converted by

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
motion-capture trajectories @sturm2012benchmark. The #link("https://cvg.cit.tum.de/data/datasets/rgbd-dataset")[official
  benchmark page] describes Kinect color and depth images with ground-truth trajectories for visual
odometry and SLAM; the official capture setup records Kinect RGB-D at 30 Hz and 640x480 resolution,
with motion-capture ground truth at 100 Hz. Its file-format notes define RGB/depth images as
pre-registered one-to-one, 16-bit depth PNG values as scaled by 5000, and the TUM trajectory rows as
timestamped $t_x, t_y, t_z, q_x, q_y, q_z, q_w$ poses. The official tools further standardize
timestamp association and absolute and relative trajectory-error evaluation. TUM RGB-D is therefore
the controlled, research-standard indoor benchmark anchor, and the normalized adapter can create
deterministic metric reference clouds from the same selected RGB-D frames used as method input. The
final evidence pass uses 19 ViSTA-oriented Freiburg sequences covering handheld SLAM,
testing/debugging, and 3D object-reconstruction categories.

Record3D supplies the custom smartphone-data path, not a public gold-standard benchmark. The
current catalog contains eight archived `.r3d` recordings. The archive metadata provides RGB and
depth raster sizes, camera intrinsics, frame timestamps, and ARKit poses; each frame stores RGB,
metric depth, and confidence payloads. The normalized archive path prepares RGB-D observations, an
ARKit provider trajectory, and a depth-derived reference cloud in `record3d_world` @record3d2026.
Those references are useful target-domain checks for the repository ingestion and evaluation path,
but they remain mobile-device provider references rather than laboratory motion-capture ground
truth.

TUM RGB-D and Record3D use a different normalization from ADVIO because their replay and reference
geometry are already tied to one selected observation stream. In `tum_rgbd_sequence.py` and
`record3d_sequence.py`, RGB and depth payloads are resized together, intrinsics are scaled into the
stored raster, depth units are normalized to meters, and deterministic point-level reference-cloud
sampling is applied after every selected observation can contribute. Their stored camera poses are
first-pose-relative,

$
  bold(T)'_k = (bold(T)_0)^(-1) bold(T)_k,
$

so the first observation becomes the local world-frame anchor. This matches the TUM RGB-D loading
convention used by the upstream ViSTA-SLAM dataset adapter, while keeping the raw motion-capture or
provider world only as provenance @zhang2026vistaslamRepo. The distinction matters: ADVIO needs
cross-provider fixedpoint registration before comparison, whereas TUM RGB-D and Record3D need a
local SLAM-compatible origin for one reference stream.

The normalized datastore used for the final evidence pass covers all three source families. The
coverage summaries in @tab:dataset-duration-coverage and @tab:dataset-trajectory-coverage are
derived from the checked-in
`docs/figures/evidence/dataset-summary.csv` artifact and from the current normalized
`stats_long.csv` entries. ADVIO dominates total duration because it contains longer pedestrian
phone trajectories. TUM RGB-D supplies short controlled RGB-D scenes with full depth coverage.
Record3D supplies a smaller custom smartphone set with depth and ARKit provider poses; its full
normalized-store trajectory range includes a long provider-path outlier and should not be conflated
with the matched-scene ranges reported later for method comparisons.

#figure(
  [
    #set text(size: 6.6pt)
    #table(
      columns: (auto, auto, auto, auto, auto, auto),
      align: center,
      inset: (x: 0.12em, y: 0.2em),
      column-gutter: 2em,
      row-gutter: 0.2em,
      toprule(),
      [#align(center)[*Dataset*]],
      [#align(center)[*Seq.*]],
      table.cell(colspan: 4)[#align(center)[*Duration*]],
      cmidrule(start: 2, end: 6),
      [],
      [],
      [#align(center)[*Total* (min)]],
      table.cell(colspan: 3)[#align(center)[*Observation* (s)]],
      cmidrule(start: 3, end: 6),
      [],
      [],
      [],
      [#align(center)[*Min*]],
      [#align(center)[*Median*]],
      [#align(center)[*Max*]],
      midrule(),
      [*ADVIO*], [23], [67.8], [51.7], [151.6], [385.6],
      [*TUM RGB-D*], [19], [19.6], [20.4], [46.3], [172.7],
      [*Record3D*], [8], [13.8], [33.9], [103.2], [173.9],
      bottomrule(),
    )
  ],
  placement: auto,
  caption: [Sequence count and duration coverage for the final evidence pass. Durations summarize manifest timestamps.],
) <tab:dataset-duration-coverage>

#figure(
  [
    #set text(size: 6.6pt)
    #table(
      columns: (auto, auto, auto, auto),
      align: center,
      inset: (x: 0.12em, y: 0.2em),
      column-gutter: 2em,
      row-gutter: 0.2em,
      toprule(),
      [#align(center)[*Dataset*]],
      table.cell(colspan: 3)[#align(center)[*Trajectory Path* (m)]],
      cmidrule(start: 1, end: 4),
      [],
      [#align(center)[*Min*]],
      [#align(center)[*Median*]],
      [#align(center)[*Max*]],
      midrule(),
      [*ADVIO*], [19.5], [140.3], [486.8],
      [*TUM RGB-D*], [2.6], [14.1], [22.2],
      [*Record3D*], [43.5], [129.2], [1028.2],
      bottomrule(),
    )
  ],
  placement: auto,
  caption: [Prepared-reference trajectory path-length coverage for the final evidence pass.],
) <tab:dataset-trajectory-coverage>

The normalized datastore separates persistent source materialization from run-local sampling.
Full-frame payloads are prepared once for a dataset, sequence, and source profile; later runs select
frame stride or target frame rate without rebuilding the source entry. The source profile encodes
byte-affecting choices such as stored frame selection, RGB resizing, intrinsics scaling, pose-frame
mode, and reference-cloud sampling. Runtime sampling records selected indices and timestamps against
the immutable normalized entry, and the metric record must trace every sampled run to that source
evidence.

The dataset disclosure for this report is therefore an evaluation-corpus disclosure rather than a
training split description. The final evidence pass is configured by
`.configs/datasets/benchmark-vslam-datastore.toml`: it includes all 23 supported ADVIO sequences,
the eight archived Record3D captures in the local catalog, and the 19 selected Freiburg TUM RGB-D
sequences used for the ViSTA-oriented benchmark pass. The report should therefore expose the same
items that machine-learning reproducibility checklists and datasheet-style dataset documentation
ask for: dataset access path, license or usage terms, asset version or retrieval date where
applicable, inclusion/exclusion rationale, explicit evaluation-only split status, preprocessing and
normalization policy, frame-selection policy, source of summary statistics, reference limitations,
and failure behavior for missing or corrupt local data. For newly recorded Record3D data, the
disclosure also needs capture provenance and any privacy or consent constraints that follow from
self-recorded smartphone video.

The figures and tables in this section should make both coverage and qualitative difference visible.
@fig:dataset-qualitative-coverage shows the qualitative axis that motivates the three-dataset
design: trajectory-only ADVIO, controlled TUM RGB-D reference geometry, and Record3D target-domain
RGB-D capture. @tab:dataset-duration-coverage gives the compact corpus-size view, while
@tab:dataset-trajectory-coverage separates the prepared-reference trajectory statistics. The most
useful supplementary statistics for a fuller dataset appendix would be sequence duration and
path-length distributions, depth-coverage distributions, indoor/outdoor or scene-category
breakdowns, example RGB/depth frames, and reference trajectory or cloud overlays for representative
sequences. Appendix figures and tables provide the selected ADVIO catalog distributions,
normalized-store coverage, statistic surfaces, and reference caveats in
@fig:appendix-advio-catalog-disclosure, @fig:appendix-dataset-summary-bars,
@tab:appendix-normalized-stat-surface, and @tab:appendix-reference-caveats.
