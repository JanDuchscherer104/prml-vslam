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
    hm_author("Lukas Röß"),
    hm_author("Christopher Kirschner"),
    hm_author("Valentin Bumeder"),
    hm_author("Florian Beck"),
  ),
  shared_affiliation: hm_shared_affiliation,
  abstract: [
    We present a benchmark framework for off-device uncalibrated monocular visual simultaneous
    localization and mapping (VSLAM) on smartphone video. The framework addresses a practical
    reproducibility gap: recent learned dense SLAM methods can process monocular image streams with
    weak or absent calibration assumptions, but their outputs are difficult to compare unless data
    ingestion, coordinate frames, scale alignment, dense geometry, and provenance are made explicit.
    The system normalizes ADVIO, TUM RGB-D, and Record3D sources into a common observation contract,
    integrates ViSTA-SLAM, MASt3R-SLAM, and LingBot-Map through method adapters, and persists the
    artifacts needed to interpret trajectories and point clouds. The paper therefore contributes a
    framework description rather than a leaderboard: it specifies source and method contracts,
    transform semantics, similarity and gravity-aware alignment, local point-cloud registration, and
    the validation gates required before quantitative results are reported.
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
  figure-supplement: [Fig.],
  paper-size: "a4",
)

#include "sections/01-introduction.typ"
#include "sections/02-related-work.typ"
#include "sections/03-challenge-and-scope.typ"
#include "sections/04-candidate-methods.typ"
#include "sections/05-datasets.typ"
#include "sections/06-metrics.typ"
#include "sections/07-experiments.typ"
#include "sections/08-discussion.typ"
#include "sections/09-conclusion.typ"
#include "sections/10-appendix-workpackages.typ"
