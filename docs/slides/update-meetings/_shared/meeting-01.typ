#let team_charter = [
  - Communication happens through GitHub issues and pull requests, with short sync notes in the weekly update deck.
  - Meetings focus on concrete progress, blockers, upcoming experiments and design decisions.
  - Early mock and interface defintions to allow parallel work on different components.
  - Aim for hackathon-style sprints early on.
]

#let goals = [
  - Evaluate methods on suited dataset (i.e. ADVIO) and on a custom self-recorded dataset with raw video and odometry logs.
    - Compare different GT sources (e.g. colmap vs iPhone pose logs)
  - Deliver an installable and reproducible benchmark scaffold for uncalibrated monocular VSLAM.
  - Compare at least two state-of-the-art methods on trajectory, point cloud, and dense reconstruction quality as well as runtime performance.
    - Use Open3D, Pytorch3D or similar packages for 3D metrics.
    - Use evo for trajectory evaluation.
    - Find and implement 3DGS-specific metrics.
  - Deliver a streaming real-time demo of the best performing method with subsequent 3DGS reconstruction visualization. Use Nerfstudio for 3D reconstruction visualization.
  -
  // - Get familiar with ARCore functionalities and APIs.
]

#let non_goals = [
  - Do not implement a full mobile AP from scratch.
  - Do not reimplement a full SLAM system from scratch.
  - Do not implement the streaming system before benchmarking is complete.
  - Do not over-engineer fully-typed, modular and generic pipelines before having a better overview of the problem space and the concrete requirements.
]
