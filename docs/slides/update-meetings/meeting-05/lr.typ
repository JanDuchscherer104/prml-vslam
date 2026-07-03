#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let done_table_row = (
  [WP 2.2 / 3],
  [Lukas Röß],
  [Implemented native point-cloud reconstruction backends (NKSR and Poisson) and refined SLAM parameters.],
)

#let challenges_table_row = (
  [WP 3],
  [Lukas Röß],
  [NKSR environment constraints and Poisson mesh tuning issues.],
)

#let next_steps_table_row = (
  [WP 3],
  [Lukas Röß],
  [Resolve NKSR build issues and refine Poisson density parameters.],
)

#let done_detail_body = items => [
  #meeting_detail_slide(items, title: [Lukas Röß: Reconstruction & Alignment])[
    - Replaced the obsolete TSDF algorithm with native point-cloud backends (*NKSR* and *Screened Poisson*).
    - Adapted the `OfflineReconstructionBackend` protocol to directly support `run_point_cloud` for dense meshing.
    - Integrated normal estimation into the reconstruction pipeline prior to meshing.
    - Refined SLAM parameters to align the SLAM algorithms with a comparable, paper-close parameter set for fair comparison.
  ]
]

#let challenges_detail_body = items => [
  #meeting_detail_slide(items, title: [Lukas Röß: Reconstruction Challenges])[
    - *NKSR Backend:* Currently facing runtime and environment compatibility issues requiring further fixes.
    - *Poisson Backend:* The generated mesh is closed, making it difficult to assess SLAM scene quality.
    - Parameter tuning (e.g., depth, density quantile) is necessary to ensure tight mesh fitting and filter out outliers.

    #v(0.8em)
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.6cm,
      [#image("../../../figures/pointcloud/poisson-mesh-inside-pointcloud.png", width: 100%) \ *Inappropriate Poisson mesh parameters (detail view)*],
      [#image("../../../figures/pointcloud/poisson-mesh-of-aligned-point-cloud.png", width: 100%) \ *Full Poisson mesh of TUM-RGBD scene*],
    )
  ]
]

#let next_steps_detail_body = items => [
  #meeting_detail_slide(items, title: [Lukas Röß: Next Steps])[
    - Resolve NKSR environment dependencies (e.g., compile against CUDA 12 or use a managed container).
    - Tune Poisson parameters to trim low-density areas and improve scene clarity.
  ]
]
