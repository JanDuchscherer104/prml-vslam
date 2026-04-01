#let team_charter = [
  - Communication happens through GitHub issues and pull requests, with short sync notes in the weekly update deck.
  - Status updates are shared in weekly team-internal meetings
  - Meetings focus on concrete progress, blockers, upcoming experiments, and design decisions.
  - Early mock and interface definitions to allow parallel work on different components.
  - Aim for hackathon-style sprints early on.
]

#let challenge_clarifications = [
  - Target use case: off-device processing of a live smartphone video stream from an emergency-call setting.
  - Assumed modality in the target setting: monocular RGB video only.
  - The smartphone primarily acts as the capture device; operator-facing visualization is off-device.
  - #link("https://developers.google.com/ar")[ARCore] is a baseline and logging aid for comparison.
  - For self-recorded data, ground truth may come from #link("https://record3d.app/")[Record3D] / iPhone RGB-D or offline #link("https://colmap.github.io/index.html")[COLMAP], not necessarily from ARCore.
]


#let goals = [
  - Evaluate methods on #link("https://github.com/AaltoVision/ADVIO")[ADVIO] and on a custom self-recorded dataset with raw video and baseline #link("https://developers.google.com/ar")[ARCore] logs.
    - Define the custom-dataset GT source up front: #link("https://record3d.app/")[Record3D] / iPhone RGB-D where available, otherwise offline #link("https://colmap.github.io/index.html")[COLMAP].
  - Deliver an installable and reproducible benchmark scaffold for off-device uncalibrated monocular VSLAM.
  - Compare at least two state-of-the-art VSLAM methods on trajectory, point cloud, and dense reconstruction quality, as well as latency and memory usage.
    - Use #link("https://github.com/MichaelGrupp/evo")[evo] for trajectory evaluation and #link("https://www.open3d.org/")[Open3D], #link("https://pytorch3d.org")[PyTorch3D] or similar packages for 3D metrics.
    - Explicit evaluation priorities: trajectory > point cloud #text(size: 13pt, fill: red)[$limits(>=)^?$] dense reconstruction > 3DGS reconstruction.
  - Deliver a streaming real-time demo of the best-performing benchmarked method on a smartphone video stream.
    - Treat #link("https://nerf.studio/")[Nerfstudio]-based 3DGS visualization as an optional stretch goal.
  - Deliver a raw-video capture and logging workflow plus a final recommendation for the most suitable pipeline in this challenge setting.
]

#let non_goals = [
  - Do not implement a full mobile app from scratch.
  - Do not reimplement a full SLAM system from scratch.
  - Do not build production-style streaming infrastructure before narrowing down the benchmark candidates.
  - Do not make operator-facing UI or 3DGS visualization a hard dependency for the core benchmark.
  - Do not over-engineer fully-typed, modular, and generic pipelines before having a better overview of the problem space and the concrete requirements.
  - Do not train or fine-tune new models unless benchmarking clearly requires it.
]
