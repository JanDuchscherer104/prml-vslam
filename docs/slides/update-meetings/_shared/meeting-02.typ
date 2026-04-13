#let goals_refined = [
  // - Keep the initial repository lightweight, installable, and stable under `uv`.
  // - Define a common output format for trajectories and dense point clouds across methods.
  // - Build the benchmark around public and custom data from the start.
]

#let non_goals_refined = [
  // - Avoid locking the repo into one heavyweight external method stack.
  // - Avoid custom one-off evaluation notebooks without reproducible scripts.
  // - Avoid storing generated outputs in the repository.
]

#let reference_links = [
  - #link("https://arxiv.org/abs/2509.01584")[ViSTA-SLAM: Visual SLAM with Symmetric Two-view Association]
  - #link("https://arxiv.org/abs/2412.12392")[MASt3R-SLAM: Real-Time Dense SLAM with 3D Reconstruction Priors]
  - #link("https://arxiv.org/abs/1807.09828")[ADVIO: An authentic dataset for visual-inertial odometry]
  - #link("https://github.com/AaltoVision/ADVIO")[ADVIO]
  - #link("https://github.com/MichaelGrupp/evo")[evo: Python package for the evaluation of odometry and SLAM]
  - #link("https://www.cloudcompare.org/")[CloudCompare]
  - #link("https://www.open3d.org/")[Open3D]
]
