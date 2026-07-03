#import "@preview/booktabs:0.0.4": bottomrule, midrule, toprule
#import "@preview/tdtr:0.5.5": *

#let ragged(body) = {
  set par(justify: false)
  body
}

#let datastore_data_color = rgb("F5F5F5")
#let datastore_group_color = rgb("E8F3FF")
#let datastore_leaf_color = rgb("F4F6FB")
#let datastore_array_color = rgb("EAF7EA")
#let datastore_derived_color = rgb("FCE8E8")

#let datastore_group = metadata("group")
#let datastore_leaf = metadata("leaf")
#let datastore_array = metadata("array")
#let datastore_derived = metadata("derived")

#let ds-code(name) = raw(name, lang: none)
#let ds-code-strong(name) = text(weight: "bold")[#ds-code(name)]

#let datastore-left-right-draw-edge = (from-node, to-node, edge-label) => {
  let from-anchor = (name: from-node.name, anchor: "east")
  let to-anchor = (name: to-node.name, anchor: "west")
  let middle-anchor = (from-anchor, 50%, to-anchor)
  if from-node.pos.x == to-node.pos.x {
    (
      vertices: (from-anchor, to-anchor),
      marks: "-|>",
      label: edge-label,
    )
  } else {
    (
      vertices: (
        from-anchor,
        ((), "-|", middle-anchor),
        ((), "|-", to-anchor),
        to-anchor,
      ),
      marks: "-|>",
      label: edge-label,
    )
  }
}

#let datastore-tree-style(
  compact: true,
  text-size: 5.9pt,
  node-width: 12.2em,
  spacing: (5pt, 8pt),
) = tidy-tree-graph.with(
  compact: compact,
  text-size: text-size,
  node-width: node-width,
  node-inset: 2pt,
  spacing: spacing,
  draw-edge: datastore-left-right-draw-edge,
  draw-node: (
    tidy-tree-draws.metadata-match-draw-node.with(
      matches: (
        group: (fill: datastore_group_color, stroke: 0.65pt + datastore_group_color.darken(28%)),
        leaf: (fill: datastore_leaf_color, stroke: 0.5pt + datastore_leaf_color.darken(18%)),
        array: (fill: datastore_array_color, stroke: 0.55pt + datastore_array_color.darken(24%)),
        derived: (fill: datastore_derived_color, stroke: 0.65pt + datastore_derived_color.darken(28%)),
      ),
      default: (fill: datastore_data_color, stroke: 0.5pt + datastore_data_color.darken(18%)),
    ),
    tidy-tree-draws.horizontal-draw-node,
  ),
)

#let vslam-datastore-tree() = {
  let tree = datastore-tree-style()
  tree[
    - #ds-code-strong("vslam-datastore/") \ --  norm. \ data samples #datastore_group
      - #ds-code-strong("advio/<seq>/<profile>/") #datastore_group
        - meta-data, statistics \ & manifest  #datastore_leaf
        - #ds-code-strong("observations/") \ --  RGB frames #datastore_group
          - #ds-code("rgb/*.png") #datastore_array
          - #ds-code("observations.json") \ --  per frame payload & metadata #datastore_leaf
        - #ds-code-strong("trajectories/") \  #datastore_group
          - #ds-code("ground_truth.tum") \ --  GT traj. #datastore_array
          - #ds-code("arcore.tum, arkit.tum") \ --  baseline \ trajs. #datastore_array
          - #ds-code("*_aligned_to_gt.tum") \ --  Sim(3) aligned trajs. #datastore_derived

      - #ds-code-strong("tum_rgbd/<seq>/<profile>/") #datastore_group
        - meta-data, statistics \ & manifest  #datastore_leaf
        - #ds-code-strong("observations/") \ -- RGB-D frames #datastore_group
          - #ds-code("rgb/*.png") \ #ds-code("depth/*.png") #datastore_array
          - #ds-code("observations.json") \ --  per frame payload & metadata #datastore_leaf
        - #ds-code-strong("benchmark/") \ \ --  GT data #datastore_group
          - #ds-code("ground_truth.tum") \ --  GT traj. #datastore_array
          - #ds-code("tum_rgbd.ply") \ --  GT cloud #datastore_array

      - #ds-code-strong("record3d/<seq>/<profile>/") #datastore_group
        - meta-data, statistics \ & manifest  #datastore_leaf
        - #ds-code-strong("observations/") \ -- RGB-D frames #datastore_group
          - #ds-code("rgb/*.png") \ #ds-code("depth/*.png") #datastore_array
          - #ds-code("observations.json") \ --  per frame payload & metadata #datastore_leaf
        - #ds-code-strong("benchmark/")  #datastore_group
          - #ds-code("arkit.tum") \ --  ref. traj. #datastore_array
          - #ds-code("record3d_lidar.ply") \ --  ref. cloud #datastore_array
  ]
}

#pagebreak()

= Appendix: Supplementary Architecture and Artifact Map

== Pipeline Architecture Diagrams

The following diagrams document reproducibility-relevant implementation structure that is too
detailed for the main paper: deterministic planning, standardized stage handoff, and separation
between live diagnostics and durable artifacts.

#figure(
  image("../../figures/mermaid/pipeline/03-run-config-stage-plan.png", width: 100%),
  caption: [Supplementary architecture: deterministic compilation from experiment configuration to an ordered execution plan.],
) <fig:appendix-run-config-stage-plan>

#figure(
  image("../../figures/mermaid/pipeline/06-stage-result.png", width: 100%),
  caption: [Supplementary architecture: terminal stage handoff and durable artifact persistence.],
) <fig:appendix-stage-result-handoff>

#figure(
  image("../../figures/mermaid/pipeline/07-runtime-updates-visualization.png", width: 100%),
  caption: [Supplementary architecture: live diagnostic updates are separated from durable scientific artifacts.],
) <fig:appendix-runtime-updates-visualization>

== Persisted Datastore Layouts

The normalized datastore is materialized as a dataset, sequence, and profile hierarchy. The
representative entries below show the persisted files that define the benchmark input contract for
each dataset family; profile identifiers are shortened because they identify materialization
profiles rather than scientific variables.

#place(
  top + center,
  float: true,
  scope: "parent",
  [
    #figure(
      vslam-datastore-tree(),
      caption: [Representative persisted datastore layouts for the three normalized dataset families.],
    ) <fig:appendix-vslam-datastore-layouts>
  ],
)

#figure(
  table(
    columns: (0.58fr, 2.42fr),
    align: (left, left),
    inset: (x: 0.24em, y: 0.21em),
    column-gutter: 0.36em,
    toprule(),
    table.header([Dataset], [Persisted modality and frame contract]),
    midrule(), [ADVIO],
    ragged(
      [RGB-only observations; `ground_truth.tum` reference; registered `arcore.tum` and `arkit.tum` as candidates and baseline references; aligned AR files as diagnostic references only. All registered trajectories target `advio_fixedpoint_common_start_local`; no reference cloud is persisted.],
    ),
    [TUM RGB-D],

    ragged(
      [RGB and registered depth observations; `ground_truth.tum` maps from `tum_rgbd_mocap_world` to `tum_rgbd_world` after first-pose-relative normalization. `tum_rgbd.ply` is a reference cloud in the same target frame.],
    ),
    [Record3D],

    ragged(
      [RGB and depth observations; `arkit.tum` and `record3d_lidar.ply` use `record3d_world` as native and target frame after the metadata `p_yz_flip` pose-frame conversion and first-pose-relative normalization.],
    ),
    bottomrule(),
  ),
  caption: [Supplementary datastore modality and frame contracts for representative normalized entries.],
) <tab:appendix-vslam-datastore-contracts>

== Dataset Coverage and ADVIO Catalog Disclosure

The supplementary dataset disclosure below keeps catalog composition and normalized-store coverage
outside the main three-page dataset narrative. The ADVIO catalog charts in
@fig:appendix-advio-catalog-disclosure document scene metadata over the public smartphone VIO
corpus, @fig:appendix-dataset-summary-bars summarizes the normalized evidence-pass coverage, and
@tab:appendix-normalized-stat-surface and @tab:appendix-reference-caveats state which statistics and
reference semantics are carried by the persisted datastore.

#figure(
  grid(
    columns: (1fr, 1fr),
    gutter: 0.65em,
    [
      #image("../../figures/advio/advio-crowd-density.png", width: 100%)
      #par(justify: false)[#text(size: 7.0pt)[Crowd-density labels from the ADVIO scene catalog.]]
    ],
    [
      #image("../../figures/advio/advio-scene-theaters.png", width: 100%)
      #par(justify: false)[#text(size: 7.0pt)[Venue and indoor/outdoor labels from the same catalog.]]
    ],
  ),
  caption: [ADVIO catalog metadata over 23 scenes: crowd density None 5, Low 8, Moderate 5, and High 5; venues Mall 10, Office 7, Metro 2, Outdoor 2, and Outdoor urban 2; 19 indoor and 4 outdoor scenes.],
) <fig:appendix-advio-catalog-disclosure>

#figure(
  image("../../figures/evidence/dataset-summary-bars.svg", width: 100%),
  caption: [Normalized datastore coverage generated from `docs/figures/evidence/dataset-summary.csv`, using one preferred normalized profile per sequence.],
) <fig:appendix-dataset-summary-bars>

#figure(
  {
    set text(size: 7.2pt)
    table(
      columns: (0.86fr, 2.34fr),
      align: (left, left),
      inset: (x: 0.18em, y: 0.18em),
      column-gutter: 0.32em,
      toprule(),
      table.header([Scope], [Persisted normalized statistics]),
      midrule(),
      [#text(size: 6.4pt)[#ds-code("sequence")]],
      ragged([Manifest frame count, manifest duration, and manifest mean FPS.]),
      [#text(size: 6.4pt)[#ds-code("observation_") \ #ds-code("sequence")]],
      ragged([Observation frame count, RGB and depth frame counts, depth coverage, observation duration, and observation mean FPS.]),
      [#text(size: 6.4pt)[#ds-code("reference_") \ #ds-code("trajectory")]],
      ragged([Reference pose count, duration, path length, speed, angular rate, curvature, and tangent-angle statistics.]),
      [#text(size: 6.4pt)[#ds-code("candidate_") \ #ds-code("trajectory")]],
      ragged([Provider or method-candidate pose count, duration, path length, speed, angular rate, curvature, and tangent-angle statistics when present.]),
      bottomrule(),
    )
  },
  caption: [Compact normalized-statistic surface persisted for materialized dataset entries.],
) <tab:appendix-normalized-stat-surface>

#figure(
  {
    set text(size: 7.2pt)
    table(
      columns: (0.72fr, 1.08fr, 1.5fr),
      align: (left, left, left),
      inset: (x: 0.16em, y: 0.16em),
      column-gutter: 0.28em,
      toprule(),
      table.header([Dataset], [Reference source], [Limitation for interpretation]),
      midrule(),
      [ADVIO],
      ragged([INS trajectory constrained by manual fixpoints; ARKit and ARCore provider trajectories are baselines.]),
      ragged([Trajectory-only in this repository; no dense cloud is source-prepared, and provider paths require explicit fixedpoint/common-start registration.]),
      [TUM RGB-D],
      ragged([Motion-capture trajectory with registered depth and a source-prepared RGB-D reference cloud.]),
      ragged([Controlled indoor benchmark; valuable as a research-standard anchor, but not deployment smartphone video.]),
      [Record3D],
      ragged([ARKit provider trajectory and depth-derived iPhone RGB-D reference cloud.]),
      ragged([Provider-quality mobile reference rather than laboratory ground truth, so it validates target-domain ingestion more than absolute accuracy.]),
      bottomrule(),
    )
  },
  caption: [Reference semantics and caveats that bound dataset-level interpretation.],
) <tab:appendix-reference-caveats>

== Artifact and Responsibility Map

The artifact map is supplementary context for reproducing or extending the benchmark. The sidecar
fields listed here are the minimum provenance surface needed to interpret the local result tables.

#figure(
  {
    set text(size: 7.6pt)
    table(
      columns: (0.78fr, 1.62fr, 1.4fr),
      align: (left, left, left),
      inset: (x: 0.18em, y: 0.18em),
      column-gutter: 0.32em,
      toprule(),
      table.header([Area], [Artifact or contract], [Scientific role]),
      midrule(),
      [Source data],
      ragged([Manifest, observations, timestamps, intrinsics, and prepared references.]),
      ragged([Separates method inputs from evaluation references.]),
      [Method execution],
      ragged([Configuration, trajectory, dense cloud, and native extras.]),
      ragged([Preserves comparable outputs and native diagnostics.]),
      [Trajectory alignment],
      ragged([Trajectory artifact plus sidecar metadata: `target_frame`, `native_frame`, pose/source provenance, origin or normalization, reference source, association policy, alignment mode, and scale policy.]),
      ragged([Documents the transformation used before trajectory metrics are interpreted.]),
      [Dense geometry],
      ragged([Reference-cloud artifact plus sidecar metadata: target frame, depth units, intrinsics and pose provenance, stride, confidence gate, random seed, sampled point counts, ICP threshold, and inlier statistics.]),
      ragged([Separates cloud placement from dense-quality scoring.]),
      [Visualization],
      ragged([Neutral visualization items and recordings.]),
      ragged([Debugs persisted artifacts.]),
      [Reporting],
      ragged([Experiment matrix, metric tables, limitations, and recommendations.]),
      ragged([Turns validated runs into scientific claims.]),
      bottomrule(),
    )
  },
  caption: [Supplementary artifact map for reproducing and extending the benchmark framework.],
) <tab:artifact-map>
