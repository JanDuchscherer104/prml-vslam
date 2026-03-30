#import "charged_ieee_local.typ": ieee

#let report_link_blue = rgb("#2563eb")
#show link: set text(fill: report_link_blue)

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
    hm_author("Florian Beck"),
    hm_author("Valentin Bumeder"),
    hm_author("Lukas Röß"),
    hm_author("Christopher Kirschner"),
    hm_author("Jan Duchscherer", email: "j.duchscherer@hm.edu"),
  ),
  shared_affiliation: hm_shared_affiliation,
  abstract: [
    This report documents the project scaffold, evaluation protocol, and benchmark plan for
    uncalibrated monocular VSLAM on smartphone video. The focus is on comparing modern methods,
    handling unknown intrinsics, and evaluating both trajectory quality and dense reconstruction
    quality against public and custom datasets.
  ],
  index-terms: (
    "VSLAM",
    "monocular SLAM",
    "dense reconstruction",
    "trajectory evaluation",
    "ADVIO",
  ),
  bibliography: bibliography("../references.bib"),
  figure-supplement: [Fig.],
  paper-size: "a4",
)

#include "sections/01-introduction.typ"
#include "sections/02-related-work.typ"
#include "challenge-intro/challenge-from-Vslam-to-3DGS.typ"
#include "sections/03-challenge-and-scope.typ"
#include "sections/04-candidate-methods.typ"
#include "sections/05-datasets.typ"
#include "sections/06-metrics.typ"
#include "sections/07-experiments.typ"
#include "sections/08-discussion.typ"
#include "sections/09-conclusion.typ"
