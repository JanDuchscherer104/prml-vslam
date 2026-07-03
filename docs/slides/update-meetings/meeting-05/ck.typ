#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let done_table_row = (
  [WP4.4],
  [CK],
  [Output-Bildqualität: Point-Cloud-Renderer (Open3D-Projektion) + maskierte Metriken (PSNR, SSIM, L1, L2); in die Pipeline als `evaluate.image`-Stage, CLI und Review-Page eingebaut.],
)

#let challenges_table_row = (
  [WP4.4],
  [CK],
  [Sparse Projektion lässt Löcher — Coverage-Maske, damit nur gefüllte Pixel bewertet werden;],
)

#let next_steps_table_row = (
  [WP4.4 / WP3],
  [CK],
  [Echte Reconstruction statt aus der rohen Punktwolke; direkter Bildmetrik-Vergleich ViSTA vs. MASt3R-SLAM.],
)

// Kleines Datenfluss-Schema — kein externes Asset nötig.
#let _flow_box(body) = rect(
  radius: 4pt,
  inset: 7pt,
  stroke: 0.6pt,
)[#align(center)[#text(size: 13pt)[#body]]]

#let _render_flow = align(center)[
  #grid(
    columns: (auto, auto, auto, auto, auto, auto, auto),
    align: horizon,
    gutter: 0.45em,
    _flow_box[Punktwolke \ + Pose],
    text(size: 16pt)[$arrow.r$],
    _flow_box[`PointCloudRenderer` \ (Open3D-Projektion)],
    text(size: 16pt)[$arrow.r$],
    _flow_box[`RenderedView` \ rgb · coverage],
    text(size: 16pt)[$arrow.r$],
    _flow_box[maskierte Metriken \ PSNR · SSIM · L1 · L2],
  )
]

#let done_detail_body = items => [
  #meeting_detail_slide(items, title: [Christopher Kirschner: Bildqualität via Point-Cloud-Projektion])[
    == Idee
    - Dense Pointcloud zurück projizieren und das Render gegen das echte aufgenommene Bild vergleichen.

    #v(0.4em)
    #_render_flow

    == Renderer — `rendering/PointCloudRenderer`
    #grid(
      columns: (1fr, 1fr),
      column-gutter: 0.9em,
      align: horizon,
      [
        - Open3D Tensor-Projektion.
        - Pro `(Pose, Intrinsics)` → `RenderedView`: RGB-Bild und eine boolesche
          Coverage-Maske.
      ],
      figure(
        image("../../../figures/image_quality/render_side_by_side.png", height: 6cm),
        caption: [Links: echtes Frame · rechts: Point-Cloud-Render],
      ),
    )
  ]

  #meeting_detail_slide(items, title: [Christopher Kirschner: Metriken & Pipeline])[
    == Metriken — `eval/image_metrics`
    - PSNR, SSIM, L1, L2, auf normalisierter `[0, 1]`-Skala.
    - *Maskiert*: Pointcloud lässt Löcher, daher werte ich nur die Pixel, die ein
      Punkt tatsächlich gefüllt hat
    - Gibt pro Frame die *Coverage* aus, damit die Werte vergleichbar bleiben.

    == Pipeline-Integration
    - `evaluate.image`-Stage: rendert pro geschätzter Pose eine View, paart sie mit dem  zeitlich nächsten Eingabe-Frame
      und persistiert `evaluation/image_metrics.json` + eine Side-by-Side-Galerie.
    - Dieselbe Engine hinter CLI (`render-run`, `eval-image`) und einer Streamlit-
      Review-Page — gleiches `evaluation/`-Layout wie Trajektorien- und Cloud-Metriken.
  ]
]

#let challenges_detail_body = items => [
  #meeting_detail_slide(items, title: [Christopher Kirschner: Challenges])[
    == Löcher durch Projektion
    - Eine naive Metrik würde jedes leere Pixel bestrafen. Lösung: Coverage-Maske aus
      `depth > 0`.
  ]
]

#let next_steps_detail_body = items => [
  #meeting_detail_slide(items, title: [Christopher Kirschner: Nächste Schritte])[
    == Aus der Reconstruction rendern
    - Die rohe Punktwolken-Projektion durch die Reconstruction
      (TSDF-Mesh #sym.arrow 3DGS) ersetzen, sobald verfügbar — dichter, weniger
      Löcher, höhere Coverage und eine stärkere obere Schranke für die Bildqualität.

    == Direkter Vergleich ViSTA vs. MASt3R-SLAM
    - `evaluate.image` für beide Backends auf derselben ADVIO-Sequenz laufen lassen.
    - PSNR / SSIM / L1 / L2 vergleichen und mit den Trajektorien- und Punktwolken-Metriken zu einem kombinierten Bild pro Methode verknüpfen.
  ]
]

#let proposal_detail_body = none
