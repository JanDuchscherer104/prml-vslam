#import "charged_ieee_local.typ": ieee
#import "@preview/booktabs:0.0.4": *

#show: booktabs-default-table-style

#let hm_author(name, email: none) = if email == none {
  (name: name)
} else {
  (name: name, email: email)
}

#let hm_shared_affiliation = (
  department: [Department of Computer Science & Mathematics],
  organization: [Munich University of Applied Sciences],
  location: [Munich, Germany],
)

#show: ieee.with(
  title: [Uncalibrated Monocular VSLAM for Smartphone Video Benchmarking],
  authors: (
    hm_author("Jan Duchscherer", email: "j.duchscherer@hm.edu"),
    hm_author("Lukas Röß", email: "lukas.roess@hm.edu"),
    hm_author("Christopher Kirschner"),
    hm_author("Valentin Bumeder", email: "Valentin.Bumeder@hm.edu"),
    hm_author("Florian Beck", email: "florian.beck@hm.edu"),
  ),
  shared_affiliation: hm_shared_affiliation,
  abstract: [
    We present a benchmark pipeline for monocular visual simultaneous localization and mapping
    (VSLAM) on ordinary smartphone videos when the camera intrinsics and metric scale are not known in
    advance. The long-term use case is off-device scene understanding from a caller's video stream.
    The phone provides the video, while a workstation estimates the camera motion and a dense 3D scene
    representation. The main difficulty is not only running a SLAM method, but making its output
    comparable. Modern learned systems use different coordinate frames, scale assumptions, and dense
    map representations, so a visual overlay alone is not enough evidence.

    Our implementation normalizes ADVIO, TUM RGB-D, and Record3D sequences, runs ViSTA-SLAM,
    MASt3R-SLAM, and LingBot-Map through common adapters, and records trajectories and point clouds.
    It also catches transforms, references, and metric inputs. The report describes the resulting artifact contract,
    including frame conventions, trajectory alignment, cloud placement and ICP diagnostics.
    A local evidence pass reports trajectory medians, ARCore and ARKit provider baselines
    on ADVIO, dense-cloud metrics (where reference clouds exist), render diagnostics, and runtime
    telemetry. These results should be taken as an artifact-scoped comparison and reproducibility
    framework, not as a statistically sourced leaderboard.
  ],
  index-terms: (
    "VSLAM",
    "monocular SLAM",
    "visual odometry",
    "benchmarking",
    "similarity alignment",
    "dataset normalization",
    "dense reconstruction",
  ),
  bibliography: bibliography("../references.bib"),
  body-appendix: [
    #include "sections/10-appendix-workpackages.typ"
  ],
  figure-supplement: [Fig.],
  paper-size: "a4",
)

#include "sections/01-introduction.typ"
#include "sections/02-related-work.typ"
#include "sections/04-candidate-methods.typ"
#include "sections/03-benchmark-framework.typ"
#include "sections/05-datasets.typ"
#include "sections/06a-trajectory.typ"
#include "sections/06b-point-cloud.typ"
#include "sections/06c-image-quality.typ"
#include "sections/06d-performance-metrics.typ"
// #include "sections/06-metrics.typ"
// #include "sections/07-experiments.typ"
// #include "sections/08-discussion.typ" TODO: include into conclusion
// future work
#include "sections/11-retrospective.typ"
#include "sections/12-future-work.typ"
#include "sections/09-conclusion.typ"
#include "sections/13-work-breakdown.typ"
