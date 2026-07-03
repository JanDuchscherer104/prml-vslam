// RESPONSIBLIY: JAN (full-section)
#import "@preview/booktabs:0.0.4": bottomrule, cmidrule, midrule, toprule

= Datasets and Source Normalization

We employ three datasets with distinct evidential roles. ADVIO supplies
deployment-realistic smartphone visual-inertial odometry (VIO) trajectories in common public spaces but lacks dense reference geometry; TUM RGB-D supplies high-quality indoor RGB-D observations with motion-capture trajectory references; and our custom Record3D dataset allows end-to-end verification of both tracking and dense reconstruction capabilities against ARKit trajectories and LiDAR-derived point-maps.


#figure(
  grid(
    columns: (1fr, 1fr, 1fr),
    gutter: 0.45em,
    [
      #image("../../figures/evidence/dataset-gt-advio.png", width: 100%)
      #par(justify: false)[#text(size: 7.2pt)[ADVIO-01: registered GT, ARKit and ARCore trajectories.]]
    ],
    [
      #image("../../figures/evidence/dataset-gt-tum-rgbd.png", width: 100%)
      #par(justify: false)[#text(size: 7.2pt)[TUM RGB-D `fr3/cabinet`: sub-sampled GT cloud and mocap trajectory.]]
    ],
    [
      #image("../../figures/evidence/dataset-gt-record3d.png", width: 100%)
      #par(justify: false)[#text(size: 7.2pt)[Record3D `29-08`: iPhone LiDAR cloud and ARKit trajectory.]]
    ],
  ),
  caption: [Qualitative dataset coverage: trajectory-only ADVIO, controlled RGB-D TUM reference geometry, and target-domain Record3D iPhone RGB-D capture.],
) <fig:dataset-qualitative-coverage>

The normalized datastore is the source-stage artifact boundary for the artifact-first pipeline in
@fig:framework-contracts. ADVIO frames arrive as `frames.mov`, Record3D
scenes as compressed `.r3d` archives, and TUM RGB-D as image and association files. Reading these
native layouts inside every method run would make the run directory depend on decoder behavior, timestamp matching, resizing, intrinsics scaling, depth units, pose-frame
conventions, and reference-cloud sampling; for Record3D it also makes sweeps and replay pay the slow
archive decode cost repeatedly. The datastore therefore decodes and normalizes each selected source
profile once into replay-ready artifacts: RGB payloads, timestamps, calibrated intrinsics, optional
metric depth, optional poses, prepared references, frame labels, alignment metadata, and provenance.
Each run then materializes only the source artifacts it needs, such as `input/sequence_manifest.json`
and `benchmark/inputs.json`, into its run directory. This keeps sweeps and real-time replay from
reopening slow native containers, while keeping ground-truth poses, provider trajectories, depth
maps, and reference clouds outside the method observation stream.

ADVIO contributes 23 pedestrian smartphone recordings spanning about 4.47 km and 1 h 8 min, with
19 indoor and 4 outdoor sequences @cortes2018advio. The supported ADVIO assets used here are the
iPhone RGB video at 60 fps with exact timestamps and calibrated
1280x720 intrinsics, a 100 Hz ground-truth pose trajectory constrained by manual fixpoint positions, raw iPhone inertial streams, 60 Hz ARKit poses, and 30 Hz Pixel ARCore
poses @cortes2018advio @aaltovisionAdvioRepo.

ADVIO ground-truth, ARCore, and ARKit trajectories do not start in a common provider world, so direct
provider-world overlays would not be valid trajectory comparisons. The source data and fixpoint
convention follow the ADVIO paper and repository, while persisted trajectories use this
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

ADVIO fixpoints are manual time-position constraints, consistent with the official fixpoint
visualization @cortes2018advio @aaltovisionAdvioRepo. For each source
$s in {"GT", "ARCore", "ARKit"}$, the normalized store keeps only fixpoints within the GT
trajectory interval, linearly interpolates RDF trajectory positions at those timestamps, and derives
one unit-scale rigid registration into the GT frame, whose first pose is the local world-frame anchor.

Registered trajectories are cropped to the common
provider interval and rebased once by the ground-truth pose at the common start time,

$
  t_0 = max_s min cal(T)_s,
  quad
  t_1 = min_s max cal(T)_s.
$

For $t in [t_0, t_1]$, the published pose is

$
  bold(T)^"local"_"c,s" (t) =
  (bold(T)^"fix"_"c,GT" (t_0))^(-1) bold(T)^"fix"_"c,s" (t),
$

for any of the three sources $s$, such that all poses are first-pose-relative and in the same local world frame.

ARCore and ARKit are benchmark
candidates only in this registered frame, while post-hoc GT-aligned ARCore/ARKit files are provided as diagnostics.

TUM RGB-D provides synchronized Kinect color and registered depth at 30 Hz and 640x480 resolution,
camera intrinsics, and 100 Hz motion-capture trajectories @sturm2012benchmark. Its file format
defines pre-registered RGB/depth images, 16-bit depth PNG values scaled by 5000, and timestamped trajectory rows. TUM RGB-D represents a controlled
benchmark reference, and the normalized adapter can create deterministic metric reference clouds from
the same selected RGB-D frames used as method input to allow for dense-geometry evaluation.

Record3D supplies custom iPhone captures, with RGB and LiDAR depth at 30 Hz, ARKit poses, as well as intrinsics. The eight recorded scenes are short outdoor pedestrian trajectories, of which a few contain dynamic objects and loop closures, while all are captured in planar public spaces.

TUM RGB-D and Record3D employ the same first-pose-relative normalization as ADVIO to normalize the poses of their single observation stream to ensure that the first pose of the first frame is the local world-frame anchor:

$
  bold(T)'_k = (bold(T)_0)^(-1) bold(T)_k,
$

This matches the TUM RGB-D loading
convention used by the upstream ViSTA-SLAM dataset adapter, ensuring that the anchor pose of each sequence becomes:

$
  bold(T)'_0 = (bold(T)_0)^(-1) bold(T)_0 = I_4.
$

RGB and depth payloads are resized together,
intrinsics are scaled into the stored raster, depth units are normalized to meters, and reference-clouds are created by back-projecting the depth maps of the selected frames into the local world frame, applying a configured pixel-stride, filtering out-of-range and low-confidence points, followed by a randomized sub-sampling to a maximum point count.

The normalized datastore used for the final evidence pass covers all three source families. The
coverage summary in @tab:dataset-duration-coverage is derived from the checked-in
`docs/figures/evidence/dataset-summary.csv` artifact and current normalized `stats_long.csv`
entries. ADVIO dominates total duration because it contains longer pedestrian phone trajectories;
TUM RGB-D supplies short controlled RGB-D scenes with full depth coverage; and Record3D supplies a
smaller custom smartphone set with depth and ARKit provider poses.

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

This disclosure describes the evaluation corpus, not a training split. The final evidence pass is
configured by `.configs/datasets/benchmark-vslam-datastore.toml`: it includes
all 23 supported ADVIO sequences, eight archived Record3D captures, and 19 selected Freiburg TUM
RGB-D sequences. Appendix material reports the ADVIO catalog distribution, normalized-store
coverage, available statistic surfaces, and reference caveats in
@fig:appendix-advio-catalog-disclosure, @fig:appendix-dataset-summary-bars,
@tab:appendix-normalized-stat-surface, and @tab:appendix-reference-caveats.
