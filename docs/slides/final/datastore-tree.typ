#import "@preview/tdtr:0.5.5": *

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

#let ds-symbol(body) = text(size: 1.12em, weight: "bold")[#body]

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

#let datastore-tree-style = tidy-tree-graph.with(
  compact: true,
  text-size: 11pt,
  node-width: 12.2em,
  node-inset: 4.4pt,
  spacing: (11pt, 16pt),
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
  datastore-tree-style[
    - #ds-code-strong("vslam-datastore/<dataset>/<seq>/") \ -- normalized sequence #datastore_group
      - input \ -- camera and time contract #datastore_group
        - #ds-symbol[$bold(K), bold(tau)$] \ -- intrinsics, timestamps #datastore_leaf
      - observations \ -- method-visible payloads #datastore_group
        - #ds-symbol[$bold(cal(I))^"rgb", bold(cal(D))$] \ -- RGB-D frames #datastore_array
        - metadata \ -- per-frame rows and manifests #datastore_leaf
      - benchmark \ -- held-out references #datastore_group
        - #ds-symbol[$bold(cal(T))^"ref"$] \ -- trajectories #datastore_array
        - #ds-symbol[$bold(cal(P))^"ref"$] \ -- point clouds #datastore_array
  ]
}
