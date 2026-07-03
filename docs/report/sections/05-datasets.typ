#import "@preview/booktabs:0.0.4": bottomrule, cmidrule, midrule, toprule

= Datasets and Source Normalization

The benchmark uses three source families because no single dataset covers the required failure modes.
ADVIO tests deployment-realistic pedestrian smartphone VIO with independent mobile-provider
trajectories but no dense geometry. TUM RGB-D supplies controlled indoor RGB-D with motion-capture
poses and source-derived reference clouds. Record3D supplies the target-domain iPhone RGB-D path with
ARKit poses and LiDAR-derived point maps. The datasets are therefore not merged as raw files; each is
adapted into the same source-stage contract before reconstruction or evaluation starts.

#figure(
  grid(
    columns: (1fr, 1fr, 1fr),
    gutter: 0.45em,
    [
      #image("../../figures/evidence/dataset-gt-advio.png", width: 100%)
      #par(justify: false)[#text(size: 7.2pt)[ADVIO-01: fixedpoint/common-start GT, ARKit, and ARCore trajectories.]]
    ],
    [
      #image("../../figures/evidence/dataset-gt-tum-rgbd.png", width: 100%)
      #par(justify: false)[#text(size: 7.2pt)[TUM RGB-D `fr3/cabinet`: sub-sampled RGB-D reference cloud and mocap trajectory.]]
    ],
    [
      #image("../../figures/evidence/dataset-gt-record3d.png", width: 100%)
      #par(justify: false)[#text(size: 7.2pt)[Record3D `29-08`: iPhone LiDAR reference cloud and ARKit trajectory.]]
    ],
  ),
  caption: [Dataset roles in the benchmark corpus: trajectory-only ADVIO, controlled RGB-D TUM reference geometry, and target-domain Record3D smartphone RGB-D capture.],
) <fig:dataset-qualitative-coverage>

== Normalized source contract

Source normalization is a methodology step, not a convenience cache. Native inputs have incompatible
containers and gauges: ADVIO stores iPhone video and provider CSVs, TUM RGB-D stores timestamped RGB,
depth, and trajectory text files, and Record3D stores compressed `.r3d` archives. Reading those
formats inside every run would make reconstruction depend on decoder state, archive random access,
timestamp association, resize policy, depth units, pose conventions, and reference-cloud sampling.
The normalized datastore materializes each byte-affecting source profile once under
`.data/vslam-datastore/<dataset>/<sequence>/<profile-key>/`, where the profile key captures the
source id, sequence id, frame-selection policy, raster policy, reference-cloud policy, and dataset
materialization options. Replay mode and later run-local frame selection are not allowed to rewrite
that stored evidence.

Each normalized entry publishes two downstream DTOs. `SequenceManifest` is the method-facing source
contract: it identifies the sequence, RGB directory or video source, timestamps, optional observation
index, intrinsics, and dataset-specific metadata such as ADVIO calibration. `PreparedBenchmarkInputs`
is the evaluation-side contract: it contains reference trajectories, candidate provider trajectories,
reference clouds, and replayable RGB-D observation sequences. This separation prevents benchmark
references from becoming implicit solver inputs; optional poses attached to observation rows are
provenance/replay geometry unless a downstream stage explicitly consumes them.

In offline mode, a runtime source reads an existing normalized entry and writes run-local selected
manifests and benchmark sidecars. Runtime frame selection is index selection over already persisted
observations; it can downsample but cannot demand frames or reference clouds that were not normalized.
In replay mode, the same entry opens an `ImageSequenceObservationSource` over `observations.json` and
emits timestamped observations with RGB, optional depth, intrinsics, optional
$T_"world,camera"$, source-frame indices, and provenance. Live Record3D is the only non-archive
streaming path: USB or Wi-Fi capture returns observations directly from the device and is not a
benchmark reference until archived and normalized.

Across all normalized dataset-backed sources, RGB frames are stored as PNGs in a method-neutral cache
raster. The current evidence profile uses maximum width 392 px with dimensions rounded to multiples
of 14, and intrinsics are scaled to the stored raster. Depth maps, when present, are resized by
nearest-neighbor to the same raster and retain an explicit `depth_scale_to_m`. The final evidence
build configuration fixes 30 Hz target cadence, the same raster policy for all three source
families, and deterministic reference-cloud sampling for TUM RGB-D and Record3D.

#figure(
  [
    #set text(size: 7.0pt)
    #table(
      columns: (0.62fr, 1.28fr, 1.50fr, 1.48fr),
      align: (left, left, left, left),
      inset: (x: 0.18em, y: 0.22em),
      column-gutter: 0.38em,
      toprule(),
      table.header([Dataset], [Native evidence], [Normalized observations], [Benchmark sidecars]),
      midrule(),
      [*ADVIO*],
      [iPhone `frames.mov`, frame timestamps, calibration, GT/fixpoints, ARCore, optional ARKit.],
      [Downscaled RGB PNGs, timestamps, scaled intrinsics, selected provider pose provenance in `advio_fixedpoint_common_start_local`; no depth.],
      [Fixedpoint/common-start GT trajectory plus ARCore/ARKit candidate trajectories; GT-aligned provider files are diagnostics only; no source dense cloud.],
      [*TUM RGB-D*],
      [`rgb.txt`, `depth.txt`, registered RGB/depth images, Freiburg intrinsics, mocap `groundtruth.txt`/`pose.txt`.],
      [Associated RGB/depth/pose frames, RGB-cache raster, depth PNG with scale $1/5000$, scaled intrinsics, first-pose-relative mocap pose.],
      [First-pose-relative GT trajectory and deterministic depth-unprojected reference cloud from the same selected observation rows.],
      [*Record3D archive*],
      [`.r3d` archive metadata, JPG RGB, LZFSE depth, confidence frames, intrinsics, ARKit pose rows.],
      [Decoded RGB-D observations, depth PNG with millimeter scale, confidence-filtered provenance, scaled intrinsics, first-pose-relative ARKit pose.],
      [ARKit provider trajectory and LiDAR-depth reference cloud; provider reference, not laboratory ground truth.],
      [*Record3D live*],
      [USB or Wi-Fi device stream.],
      [Direct observations with RGB, depth, intrinsics, confidence, and live ARKit pose; optional runtime sampling.],
      [No durable benchmark sidecar until the capture is archived and normalized.],
      bottomrule(),
    )
  ],
  caption: [Dataset-specific conversion from native source evidence to the common offline and replay contracts.],
) <tab:dataset-normalization-outputs>

== ADVIO trajectory normalization

ADVIO contributes 23 pedestrian smartphone recordings spanning about 4.47 km and 1 h 8 min, with 19
indoor and 4 outdoor sequences @cortes2018advio. The assets used here are iPhone RGB video, frame
timestamps, calibration metadata, ground-truth poses, manual fixpoints, and ARKit/ARCore provider
pose streams @cortes2018advio @aaltovisionAdvioRepo. ADVIO is trajectory-only in this benchmark: the
source repository does not publish a dense reference cloud, so dense-cloud metrics on ADVIO require a
separately documented reconstruction target.

ADVIO provider trajectories are not directly comparable in their raw worlds. The repository first
converts all ADVIO pose streams into its right--down--forward (RDF) camera convention. With raw
ADVIO coordinates interpreted in the Apple/Y-up basis, the basis conversion is

$
  bold(B)_"advio" =
  mat(0, 0, 1; 0, -1, 0; 1, 0, 0),
$

and positions and rotations are transformed by

$
  bold(p)^"rdf" = bold(B)_"advio" bold(p)^"raw",
  quad
  bold(R)^"rdf" =
  bold(B)_"advio" bold(R)^"raw" bold(B)_"advio"^(-1).
$

`ground-truth/fixpoints.csv` is then used as timestamped physical control-point evidence, not as a
precomputed transformation matrix. For each source
$s in {"GT", "ARCore", "ARKit"}$, fixpoints outside the provider trajectory interval are discarded,
RDF trajectory positions are linearly interpolated at the remaining fixpoint timestamps, and one
unit-scale rigid registration is estimated:

$
  (bold(R)_s^*, bold(t)_s^*) =
  op("arg min", limits: #true)_(bold(R) in "SO"(3), bold(t))
  sum_i norm(bold(f)_i - (bold(R) bold(x)_s(t_i) + bold(t)))^2 .
$

This is the no-scale, no-reflection absolute-orientation problem; scale is fixed to 1 because GT,
ARKit, and ARCore are metric pose providers @umeyama1991least. At least six matched fixpoints are
required. The full $"SO"(3)$ solution is accepted only if it tilts RDF gravity by at most 15 degrees;
otherwise the same least-squares objective is solved with $bold(R)$ restricted to yaw about RDF
gravity. Registrations with excessive residual RMS or max error are rejected. These gates are
repository stability guards for near-planar pedestrian trajectories, not an official ADVIO metric.

After fixedpoint registration, accepted providers are cropped to their common time interval and
rebased once by the ground-truth pose at the common start time,

$
  t_0 = max_s min cal(T)_s,
  quad
  t_1 = min_s max cal(T)_s,
$

with the normalized camera pose

$
  bold(T)^"local"_"c,s"(t) =
  (bold(T)^"fix"_"c,GT"(t_0))^(-1) bold(T)^"fix"_"c,s"(t),
  quad t in [t_0, t_1].
$

The resulting frame is `advio_fixedpoint_common_start_local`. Registered ARCore and ARKit are
candidate baselines in this frame. Additional `*_aligned_to_gt.tum` files use post-hoc Sim(3) or
yaw-similarity alignment after fixedpoint normalization and are diagnostics only. The fixedpoint
registration is gauge normalization, not trajectory repair: it changes one global frame per source
without altering relative motion, local drift, or trajectory shape.

== TUM RGB-D normalization

TUM RGB-D provides synchronized Kinect color, registered depth, calibrated intrinsics, and
motion-capture trajectories @sturm2012benchmark. The adapter parses RGB/depth lists, associates RGB,
depth, and mocap samples by nearest timestamp with a bounded tolerance, uses sequence-specific
Freiburg intrinsics, and converts the raw mocap trajectory into the camera-RDF convention. Depth PNG
values are interpreted with scale $1/5000$ meters, and depth is treated as already registered to RGB.

For each selected frame, the normalized observation sequence stores downscaled RGB, nearest-neighbor
resized depth, scaled intrinsics, source-frame index, timestamp, and first-pose-relative
$T_"world,camera"$. The GT trajectory is written in the same first-pose-relative world. Reference
clouds are generated only from the selected observation rows: metric depth is unprojected through the
scaled intrinsics and GT camera pose, color is carried from the RGB image, points are sampled by the
configured pixel stride, and the final cloud is deterministically capped by `max_points` and
`random_seed`. TUM RGB-D is therefore the controlled geometry anchor for both trajectory and dense
cloud diagnostics.

== Record3D archive and live normalization

Record3D archives supply the custom smartphone RGB-D path @record3d2026. The archive adapter validates
that every frame has a JPG RGB image, LZFSE-compressed depth map, confidence map, timestamp, and ARKit
pose. RGB intrinsics are parsed from the archive metadata; depth intrinsics are obtained by scaling
those intrinsics to the depth raster. Pose rows are decoded as ARKit camera poses with the configured
Record3D pose-frame policy, whose default applies the repository's Y/Z flip before converting to the
camera-RDF transform.

For offline archives, selected frames are decoded once into RGB-D observations. RGB is resized to the
cache raster, depth is resized to that raster for method input and stored as 16-bit PNG with
`depth_scale_to_m = 0.001`, and intrinsics are scaled accordingly. ARKit poses and the trajectory are
rebased to the first selected pose, so `record3d_world` is a provider-local world rather than a
laboratory reference frame. The reference cloud is generated from LiDAR depth in the depth raster,
optionally filters pixels by confidence, unprojects with depth intrinsics and the first-pose-relative
ARKit pose, colors from RGB resized to depth resolution, and applies deterministic random
subsampling. These clouds are target-domain provider references.

The live Record3D source is deliberately separate from archive normalization. In streaming mode, USB
or Wi-Fi capture emits observations directly from the device with arrival timestamps, RGB, metric
depth, confidence, intrinsics, and ARKit pose. A frame-stride or target-FPS wrapper may downsample the
stream, but live sessions do not produce reference clouds or durable benchmark trajectories unless
the capture is saved as an archive and normalized through the offline path.

== Evidence corpus and traceability

The final evidence pass is configured by `.configs/datasets/benchmark-vslam-datastore.toml`. It
normalizes all 23 supported ADVIO sequences, eight archived Record3D captures, and 19 selected TUM
RGB-D Freiburg sequences. TUM RGB-D and Record3D use deterministic reference-cloud parameters
(`depth_stride_px = 3`, `max_points = 500000`, `random_seed = 17`; Record3D additionally requires
`min_confidence = 1`). The coverage summary in @tab:dataset-duration-coverage is derived from the
checked-in `docs/figures/evidence/dataset-summary.csv` artifact and the normalized `stats_long.csv`
entries.

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
  caption: [Sequence count and duration coverage for the final evidence pass. Durations summarize normalized manifest timestamps.],
) <tab:dataset-duration-coverage>

Every normalized entry also writes `stats_long.csv` and `metadata_long.csv`. These tables record
frame counts, durations, effective FPS, path-length and motion statistics for trajectories, source
profile settings, timestamp sampling metadata, and payload paths. Metric records can therefore trace
back to an immutable dataset id, sequence id, profile key, source-frame index set, timestamp set, and
reference artifact. This disclosure describes the evaluation corpus, not a training split; all
source-prepared references remain benchmark sidecars and must be reported with their stated reference
strength: ADVIO fixedpoint-registered trajectories, TUM RGB-D mocap/depth geometry, or Record3D
ARKit/LiDAR provider references.
