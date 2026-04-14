#let goals_refined = [
  - ViSTA-SLAM already implements much of the benchmark and streaming pipeline we expected to build ourselves (webcam stream, benchmark pipeline)
  - Use #link("https://arxiv.org/pdf/2509.01584")[ViSTA-SLAM] as upstream baseline and inspiration.
  - Keep the repository centered on a reproducible benchmark scaffold with typed contracts, canonical artifact paths, and TOML-first run planning.
  - Evaluate methods on #link("https://github.com/AaltoVision/ADVIO")[ADVIO], TUM-RGBD and our own custom dataset.
  - Use Record3D as data source for custom offline dataset and streaming demo.
  - Develop a more modular, streamlined evaluation and streaming framework inspired by ViSTA-SLAM's architecture.
    + Strong artifact contracts.
    + Modularity and configurability.
    + CLI and Streamlit app surfaces.
    + Multiprocessing and distributed execution support.
]

#let non_goals_refined = [
  - Do not start with 3DGS before Open3D-based TSDF reconstruction.
]

#let reference_links = [
  - Upstream methods: #link("https://arxiv.org/pdf/2509.01584")[ViSTA-SLAM] as the primary baseline and #link("https://arxiv.org/abs/2412.12392")[MASt3R-SLAM] as the secondary comparison target.
  - Data and baselines: #link("https://github.com/AaltoVision/ADVIO")[ADVIO], #link("https://record3d.app/")[Record3D], and #link("https://developers.google.com/ar")[ARCore].
  - Evaluation and reconstruction tools: #link("https://github.com/MichaelGrupp/evo")[evo], #link("https://www.open3d.org/")[Open3D], #link("https://www.cloudcompare.org/")[CloudCompare], #link("https://colmap.github.io/index.html")[COLMAP], #link("https://meshroom.org/")[Meshroom], and #link("https://nerf.studio/")[Nerfstudio].
]
