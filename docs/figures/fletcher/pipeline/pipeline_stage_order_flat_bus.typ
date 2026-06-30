#import "@preview/fletcher:0.5.8" as fletcher: diagram, edge, node

#set text(font: "New Computer Modern", size: 10pt)

#let green = rgb("d8ecd3")
#let green-stroke = rgb("7fb27d")
#let purple = rgb("eadcf2")
#let purple-stroke = rgb("9b75b8")
#let blue = rgb("d9e8fb")
#let blue-stroke = rgb("7da0d4")
#let yellow = rgb("fff1c7")
#let yellow-stroke = rgb("d9ad3f")
#let red = rgb("f8d2cf")
#let red-stroke = rgb("d97870")
#let gray = rgb("7f8da1")
#let tap = (paint: gray.lighten(10%), dash: "dashed", thickness: 0.55pt)

#let stage(title, subtitle, fill, stroke, w: 30mm, h: 16.3mm, title-size: 14.8pt, subtitle-size: 10.5pt) = block(
  width: w,
  height: h,
  fill: fill,
  stroke: 0.65pt + stroke,
  radius: 3pt,
  inset: (x: 3pt, y: 1.6pt),
)[
  #align(center + horizon)[
    #text(weight: "bold", size: title-size)[#title]
    #v(0.07em)
    #text(size: subtitle-size)[#subtitle]
  ]
]

#let tiny-stage(title, subtitle, fill, stroke, w: 28mm) = stage(
  title,
  subtitle,
  fill,
  stroke,
  w: w,
  h: 12.4mm,
  title-size: 14.8pt,
  subtitle-size: 10.5pt,
)

#let pipeline-stage-order-flat-bus() = align(center + horizon)[
  #box(width: 100%)[#diagram(
    spacing: (2.7mm, 2.4mm),
    node-inset: 0pt,
    node-stroke: none,
    edge-stroke: 0.72pt + gray,
    mark-scale: 58%,
    node(
      (0, 0),
      stage([source], [Record3D / TUM / ADVIO / iPhone Stream], green, green-stroke, w: 40mm, h: 16.9mm),
      name: <src>,
    ),
    node((1, 0), stage([vSLAM], [trajectory + depth maps], purple, purple-stroke, w: 34mm, h: 16.5mm), name: <slam>),
    node((2, 0), stage([align.Traj], [Sim(3)], blue, blue-stroke), name: <traj>),
    node((3, 0), stage([align.Cloud], [ICP], blue, blue-stroke), name: <cloud>),
    node((4, 0), stage([Reconstruction], [Mesh], blue, blue-stroke, w: 38mm), name: <recon>),

    node((2, -1), tiny-stage([eval.Traj], [metrics], yellow, yellow-stroke), name: <evaltraj>),
    node((3, -1), tiny-stage([eval.Cloud], [diagnostic], yellow, yellow-stroke), name: <evalcloud>),
    node((4, -1), tiny-stage([eval.Image], [diagnostic], yellow, yellow-stroke), name: <evalimage>),
    node((1.55, 1), tiny-stage([align.Gravity], [ground plane], blue, blue-stroke, w: 31mm), name: <gravity>),
    node((5, 1.72), tiny-stage([RerunSink], [live / export], red, red-stroke, w: 32mm), name: <rerun>),

    edge(<src>, <slam>, "-|>"),
    edge(<slam>, <traj>, "-|>"),
    edge(<traj>, <cloud>, "-|>"),
    edge(<cloud>, <recon>, "-|>"),

    edge(<traj>, <evaltraj>, "-|>"),
    edge(<cloud>, <evalcloud>, "-|>"),
    edge(<cloud>, <evalimage>, "-|>"),
    edge(<slam>, <gravity>, "-|>"),

    edge((-0.05, 1.72), (4.75, 1.72), "-|>", stroke: tap),
    edge((4.75, 1.72), <rerun>, "-|>", stroke: tap),
    edge(<src>, (0, 1.72), stroke: tap),
    edge(<slam>, (1, 1.72), stroke: tap),
    edge(<gravity>, (1.55, 1.72), stroke: tap),
    edge(<traj>, (2, 1.72), stroke: tap),
    edge(<cloud>, (3, 1.72), stroke: tap),
    edge(<recon>, (4, 1.72), stroke: tap),
  )]
]

#pipeline-stage-order-flat-bus()
