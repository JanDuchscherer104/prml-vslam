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

= Appendix: Supplementary Materials

== Persisted Datastore Layouts

The normalized datastore is materialized as a dataset, sequence, and profile hierarchy. The
representative entries in @fig:appendix-vslam-datastore-layouts show the persisted files that define the benchmark input contract for
each dataset family; profile identifiers are shortened because they identify materialization
profiles.

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
