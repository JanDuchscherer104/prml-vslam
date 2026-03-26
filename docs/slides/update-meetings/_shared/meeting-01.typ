#let team_charter = [
  - Communication happens through GitHub issues and pull requests, with short sync notes in the
    weekly update deck.
  - Meetings focus on concrete benchmark progress, blockers, and upcoming experiments.
  - Structural decisions are made in the repo so they remain reviewable and reproducible.
  - Conflicts are handled by documenting assumptions and reducing ownership overlap.
]

#let goals = [
  - Deliver an installable and reproducible benchmark scaffold for uncalibrated monocular VSLAM.
  - Compare at least two state-of-the-art methods on trajectory and dense reconstruction quality.
  - Establish the capture, evaluation, and reporting workflow before method-heavy work starts.
]

#let non_goals = [
  - Do not reimplement a full SLAM system from scratch.
  - Do not vendor large external method repositories into this repo during bootstrap.
  - Do not optimize for edge deployment before the benchmark pipeline exists.
]
