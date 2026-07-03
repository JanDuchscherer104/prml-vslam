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
    hm_author("Florian Beck"),
  ),
  shared_affiliation: hm_shared_affiliation,
  abstract: [
    We describe a reproducible benchmark substrate for off-device uncalibrated monocular visual
    simultaneous localization and mapping (VSLAM) on smartphone video. Recent learned dense SLAM
    systems relax some calibration assumptions, but their outputs are interpretable only when
    ingestion, frame conventions, scale, dense geometry, and provenance are explicit. The
    implementation materializes ADVIO, TUM RGB-D, and Record3D as normalized observation sequences;
    adapts ViSTA-SLAM, MASt3R-SLAM, and LingBot-Map; and persists trajectories, dense clouds,
    transform metadata, and metric inputs. The paper specifies an artifact contract with RDF camera
    frames, ADVIO fixedpoint-common-start registration, first-pose-relative RGB-D sources, Sim(3)
    and gravity-aware trajectory placement, and ICP-based dense-geometry diagnostics. The resulting
    local evidence pass reports matched trajectory medians, ADVIO provider baselines, dense-cloud
    metrics, render diagnostics, and runtime telemetry. These results characterize
    method-dependent tradeoffs across controlled RGB-D, self-recorded RGB-D, and ADVIO phone-video
    regimes while remaining a local artifact-scoped comparison rather than a statistically powered
    leaderboard.
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
#include "sections/03-benchmark-framework.typ"
#include "sections/04-candidate-methods.typ"
#include "sections/05-datasets.typ"
#include "sections/06-metrics.typ"
#include "sections/07-experiments.typ"
#include "sections/08-discussion.typ"
#include "sections/11-retrospective.typ"
#include "sections/09-conclusion.typ"
