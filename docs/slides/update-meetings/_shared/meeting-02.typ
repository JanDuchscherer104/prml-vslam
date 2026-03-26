#let goals_refined = [
  - Keep the initial repository lightweight, installable, and stable under `uv`.
  - Define a common output format for trajectories and dense point clouds across methods.
  - Build the benchmark around public and custom data from the start.
]

#let non_goals_refined = [
  - Avoid locking the repo into one heavyweight external method stack.
  - Avoid custom one-off evaluation notebooks without reproducible scripts.
  - Avoid storing generated outputs in the repository.
]

#let reference_links = [
  - Candidate methods: #link("https://arxiv.org/pdf/2509.01584")[ViSTA-SLAM] and
    #link("https://arxiv.org/abs/2412.12392")[MASt3R-SLAM].
  - Evaluation references: #link("https://github.com/AaltoVision/ADVIO")[ADVIO],
    #link("https://github.com/MichaelGrupp/evo")[evo], and
    #link("https://colmap.github.io/index.html")[COLMAP].
  - Geometry tooling: #link("https://www.open3d.org/")[Open3D] for inspection and metric support.
]
