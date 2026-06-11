#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let done_table_row = (
  [WP4],
  [Florian Beck],
  [Implemented artifact-based point-cloud evaluation and Streamlit metric views.],
)

#let challenges_table_row = (
  [WP4],
  [Florian Beck],
  [Point-cloud metrics are currently dataset-dependent: TUM RGB-D has reference clouds, ADVIO does not.],
)

#let next_steps_table_row = (
  [WP4],
  [Florian Beck],
  [Run complete benchmark sweeps and document dataset-specific cloud availability.],
)

#let done_detail_body = items => [
  #meeting_detail_slide(items, title: [Florian Beck: Point-Cloud Evaluation])[
    - Added a pipeline stage for dense-cloud evaluation.
    - Compares full benchmark clouds after Sim(3) alignment; reconstruction is included when available.
    - Streamlit now shows point-cloud values and plots next to trajectory metrics.

    #v(0.5em)
    #grid(
      columns: (1.08fr, 1fr),
      gutter: 0.45cm,
      [
        #figure(
          image("../../../figures/pointcloud/pc-values.jpg", width: 100%),
          caption: [Persisted point-cloud metric table in Streamlit.],
        ) <m04-fb-pc-values>
      ],
      [
        #figure(
          image("../../../figures/pointcloud/pc-graphs.jpg", width: 100%),
          caption: [Distance, quality, and point-count plots.],
        ) <m04-fb-pc-graphs>
      ],
    )
  ]

  #meeting_detail_slide(items, title: [Florian Beck: Metrics Used])[
    #set text(size: 17pt)
    Let $E$ be the estimated cloud, $R$ the reference cloud, and $tau = 0.05 m$. Nearest-neighbor distances follow Open3D's point-cloud distance API.#footnote[Open3D, `PointCloud.compute_point_cloud_distance`: https://www.open3d.org/docs/release/python_api/open3d.geometry.PointCloud.html]

    #v(0.35em)
    - *Accuracy:* mean nearest-neighbor distance from estimate to reference. \
      $ 1 / |E| sum_(e in E) min_(r in R) ||e - r||_2 $
    - *Completeness:* mean nearest-neighbor distance from reference to estimate. \
      $ 1 / |R| sum_(r in R) min_(e in E) ||r - e||_2 $
    - *Chamfer distance:* symmetric cloud error used here as accuracy + completeness.#footnote[Open3D tensor point-cloud metrics define Chamfer distance from nearest-neighbor distances: https://www.open3d.org/docs/release/python_api/open3d.t.geometry.Metric.html]
    - *F1 score:* thresholded overlap. Precision = share of $E$ within $tau$ of $R$; recall = share of $R$ within $tau$ of $E$; $F_1 = 2 P R / (P + R)$.#footnote[Open3D point-cloud metrics include F-score at configurable radii: https://www.open3d.org/docs/release/python_api/open3d.t.geometry.PointCloud.html]
    - *ICP fitness/RMSE:* Open3D registration diagnostics: correspondence ratio and inlier residual after ICP.#footnote[Open3D ICP tutorial and `RegistrationResult`: https://www.open3d.org/docs/release/tutorial/pipelines/icp_registration.html]
  ]
]

#let challenges_detail_body = items => [
  #meeting_detail_slide(items, title: [Florian Beck: Dataset Difference])[
    - TUM RGB-D provides RGB-D frames and lets us build an aligned reference cloud.
    - Therefore we can compute point-cloud metrics for ViSTA outputs against a dense reference.
    - ADVIO currently provides trajectory references in our adapter, but no benchmark reference cloud.
    - Result: ADVIO can validate trajectory metrics, but point-cloud metrics are not available yet.
  ]
]

#let next_steps_detail_body = none
