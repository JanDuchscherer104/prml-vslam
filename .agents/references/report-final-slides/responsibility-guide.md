# JD-First Report Responsibility Guide

This guide maps final-report sections to JD-first evidence clusters, theory
depth, source constraints, and validation gates. It is a planning and
bootstrapping artifact for future report agents. It is not final report prose,
not a final work-breakdown, and not a final contribution-credit assignment.

The wording here uses evidence ownership: it identifies where our strongest
seed material exists. It does not assign final writing roles, presentation
segments, speaking shares, or final team credit. The final deliverables still
need to preserve five-member equal participation across code, report, and
presentation.

## Source Tiers

- Strongest evidence: merged code, tracked repository documentation, committed
  figures, final run artifacts, metrics CSV/JSON files, manifests, and current
  package README/REQUIREMENTS contracts.
- Planning-accepted evidence: PR 86 update-slide material, PR 88 Record3D and
  normalized-store material, PR 91 LingBot material, and
  `.omx/specs/report-final-slides/report-section-candidates.md`.
- Explanatory evidence: `docs/references.bib`, local arXiv source trees under
  `docs/literature/tex-src/`, and local ignored lecture material summarized in
  tracked guidance.
- Missing bibliography: add citations before final prose if using Umeyama,
  ICP, TUM RGB-D, TSDF/KinectFusion, LingBot, Record3D, or Rerun as substantive
  external claims.

Path labels in this guide are intentional. Paths prefixed with `PR 86`,
`PR 88`, or `PR 91` are `PR-only` planning paths unless they also exist in the
current worktree. `local ignored` sources are readable on this machine but are
not tracked. `missing bibliography` items must be added before final prose.

PR 86, PR 88, and PR 91 are final planning inputs for this guide. They are not
publication-proof by themselves: final prose and numerical claims still need
validation against merged code, final artifact paths, final configs, and final
metric files.

## Selective Deep Theory Policy

Use deep theory only where it explains a real project difficulty or a metric
choice:

- source normalization and benchmark comparability;
- frame semantics and transform conventions;
- monocular scale ambiguity and Sim(3);
- gravity-locked ADVIO alignment;
- ICP/cloud alignment and threshold sensitivity;
- trajectory metric interpretation and artifact-backed evaluation.

Keep other theory concise: define the term, cite the source, and move back to
the artifact-backed project evidence. Put derivations, full equations, and
extended metric notes into an appendix unless they are essential to understand
the main result.

## Section Map

### Introduction

Evidence owner cluster: shared section, JD-first seed material for challenge
framing and pipeline outcome.

JD evidence:

- `README.md` for the core challenge: off-device monocular VSLAM on smartphone
  video with unknown intrinsics.
- `docs/Questions.md` for the operator-facing motivation, streaming constraint,
  smartphone capture role, Record3D/custom dataset expectation, and optional
  ARCore baseline status.
- `.omx/specs/report-final-slides/report-section-candidates.md` for the
  current report-shape synthesis.

Non-JD evidence needed:

- Team-level motivation and final contribution summary.
- Final wording for the shared project recommendation.

Theory depth: concise. Introduce VSLAM, unknown intrinsics, dense point clouds,
and off-device benchmarking only as needed for the reader to understand the
challenge.

Allowed sources:

- Tracked repo docs and final artifacts for project claims.
- Bibliography entries for method background.
- Lecture criteria for required deliverable framing.

PR caveat:

- PR 86, PR 88, and PR 91 may inform the final framing, but do not use their
  metric examples as final results until artifact-validated.

Validation before final prose:

- Confirm the final report still targets the same challenge statement.
- Confirm any claim about evaluated methods matches the final merged method set.
- Keep this section short enough that methodology and results retain space.

### Related Work

Evidence owner cluster: shared section, JD-first seed material for evaluation
and alignment sources.

JD evidence:

- `docs/references.bib` currently contains ViSTA-SLAM, MASt3R-SLAM, ADVIO,
  COLMAP/SfM, COLMAP/MVS, Open3D, and evo.
- `docs/literature/tex-src/README.md` and
  `docs/literature/tex-src/sources.jsonl` identify local source trees for
  ViSTA-SLAM, MASt3R-SLAM, DROID-SLAM, and ADVIO.
- `.agents/references/agent_reference.md` points to primary sources for evo,
  Open3D, Rerun, ViSTA-SLAM, and MASt3R-SLAM.

Non-JD evidence needed:

- MASt3R-specific final method summary if that remains a team result.
- Any image-quality, 3DGS, or additional reconstruction literature owned by
  other evidence clusters.

Theory depth: concise with selective deep theory references. Related work
should not become a tutorial; reserve equations and alignment details for
Metrics or Discussion.

Allowed sources:

- `docs/references.bib`
- `docs/literature/tex-src/`
- External primary papers or official project docs when bibliography entries
  are missing.

PR caveat:

- Treat PR 91 LingBot as in-scope for planning, but add a bibliography or
  official upstream citation before presenting LingBot as a final related-work
  method.

Validation before final prose:

- Add missing bibliography entries before using Umeyama, ICP, TUM RGB-D,
  TSDF/KinectFusion, LingBot, Record3D, or Rerun claims.
- Ensure each related-work paragraph supports a method, dataset, metric, or
  limitation used later in the report.

### Challenge And Scope

Evidence owner cluster: JD-first seed material with shared final constraints.

JD evidence:

- `README.md` for implemented and limited status.
- `docs/Questions.md` for real-time streaming, smartphone capture, custom
  dataset, ARCore baseline, and 3DGS role clarifications.
- `src/prml_vslam/pipeline/README.md` for the current public pipeline surface.
- `src/prml_vslam/eval/README.md` for implemented trajectory evaluation and
  current cloud-evaluation limitation.

Non-JD evidence needed:

- Final team decision on which limitations are still true at report freeze.
- Final shared work-breakdown facts for report and code.

Theory depth: concise. Use this section to bound the problem, not to derive
metrics.

Allowed sources:

- Tracked docs, package README/REQUIREMENTS files, and lecture criteria.
- PR 86/88/91 as planning-final scope inputs.

PR caveat:

- PR 88 and PR 91 can be described as planned-final scope for this guide, but
  final text must check whether they are merged or explicitly included at
  report freeze.

Validation before final prose:

- Confirm current final method set and dataset set.
- Confirm cloud and efficiency evaluation maturity.
- Avoid presenting optional ARCore or 3DGS work as required if it remained
  outside the final pipeline.

### Candidate Methods

Evidence owner cluster: shared section, JD-first seed material for ViSTA and
LingBot integration boundaries.

JD evidence:

- `src/prml_vslam/methods/vista/README.md` for ViSTA preprocessing,
  postprocessing, RDF camera frame semantics, `T_world_camera`, live pointmaps,
  exported PLY clouds, and SLAM-local world frame.
- `src/prml_vslam/methods/vista/adapter.py` and
  `src/prml_vslam/methods/vista/artifacts.py` for implementation-backed ViSTA
  claims.
- PR 91 `src/prml_vslam/methods/lingbot/README.md` for LingBot benchmark
  profile, memory-aware settings, and normalized artifact policy.
- PR 91 `.configs/pipelines/lingbot-full.toml` and
  method package code for LingBot configuration and adapter evidence.

Non-JD evidence needed:

- MASt3R final implementation and result evidence from the responsible team
  cluster.
- Any method-quality interpretation that depends on final benchmark tables.

Theory depth: selective. Explain unknown-intrinsics handling, learned dense
SLAM output semantics, monocular scale ambiguity, and method-specific frame
conventions only where they affect evaluation.

Allowed sources:

- Method package docs and code for implementation facts.
- Method papers and official upstream docs for algorithm claims.
- Final run artifacts for result claims.

PR caveat:

- PR 91 is planning-final for the guide. Publication text must verify the final
  LingBot branch state, final config, and final artifact outputs.

Validation before final prose:

- Confirm every named method has a final config, final run, or explicit
  limitation.
- Do not compare method quality without final metrics.
- Distinguish integration maturity from algorithmic performance.

### Datasets

Evidence owner cluster: JD-first seed material.

JD evidence:

- `src/prml_vslam/sources/README.md` for source-stage contracts,
  `SequenceManifest`, `PreparedBenchmarkInputs`, replay, and streaming
  observations.
- `src/prml_vslam/sources/datasets/advio/README.md` for ADVIO dataset serving.
- `src/prml_vslam/sources/datasets/tum_rgbd/README.md` for TUM RGB-D support.
- `src/prml_vslam/sources/record3d/README.md` for live Record3D USB and Wi-Fi
  Preview transport support.
- PR 88 `src/prml_vslam/sources/datasets/normalized_store.py` for deterministic
  normalized entries and reusable full-frame payloads.
- PR 88 `src/prml_vslam/sources/datasets/record3d/record3d_sequence.py` for
  offline `.r3d` archive loading, ARKit trajectory reference, RGB-D
  observation sequence, and depth-derived reference cloud.
- PR 86 `meeting-05/jd.typ` for nine recorded Record3D scenes and normalized
  dataset-store reporting.

Non-JD evidence needed:

- Final custom dataset description from the team, including which scenes are
  actually submitted or evaluated.
- Any teammate-specific acquisition notes and dataset-quality limitations.

Theory depth: selective deep theory. Explain why normalization is a benchmark
requirement: timestamps, intrinsics, rasters, pose providers, depth units, and
frame conventions must be comparable before method results are meaningful.

Allowed sources:

- Source package docs/code, PR 88 files, final dataset artifacts, and final
  dataset stats.
- Dataset papers or official docs for ADVIO, TUM RGB-D, and Record3D claims.

PR caveat:

- PR 88 is planning-final for the guide. Final report claims must validate the
  merged normalized-store layout and final Record3D artifact paths.

Validation before final prose:

- Confirm dataset sequences, frame sampling, and source profiles used in final
  runs.
- Confirm every reference trajectory/cloud claim points to a final artifact.
- Do not use local ignored raw datasets as report evidence without a tracked or
  citable summary.

### Metrics

Evidence owner cluster: JD-first seed material for alignment and artifact-backed
evaluation; shared section for final metric interpretation.

JD evidence:

- `src/prml_vslam/eval/README.md` for trajectory evaluation, translation APE,
  long-form metric rows, and error-series references.
- `src/prml_vslam/alignment/README.md` for derived ground-plane alignment and
  explicit frame semantics.
- PR 86 `meeting-05/jd.typ` for Sim(3), gravity-locked ADVIO alignment, ICP,
  and candidate metric examples.
- `docs/references.bib` for evo and Open3D references.

Non-JD evidence needed:

- Final point-cloud metric implementation details if owned outside the JD
  cluster.
- Final image-quality or reconstruction-quality metrics if used.

Theory depth: selective deep theory. This is the primary place for:

- monocular scale ambiguity and Sim(3);
- gravity-locked yaw/scale/translation alignment;
- trajectory APE interpretation;
- ICP fitness, inlier RMSE, and inlier-threshold sensitivity.

Allowed sources:

- Evaluation package docs/code, final metrics files, final alignment JSON/CSV,
  bibliography, and missing primary citations once added.

PR caveat:

- PR 86 metric values are planning-final candidates. Publication text must
  validate final artifact paths, final configs, and final metric files before
  using numbers.

Validation before final prose:

- Confirm final metric definitions, alignment mode, reference source, and
  thresholds.
- Confirm metric values from JSON/CSV artifacts, not slides alone.
- Add missing Umeyama and ICP citations before using equations or formal
  metric derivations.

### Experiments

Evidence owner cluster: shared section, JD-first seed material for reproducible
artifact protocol and candidate run matrix.

JD evidence:

- `src/prml_vslam/pipeline/README.md` for run planning, runtime contracts, and
  artifact ownership.
- `.configs/pipelines/*.toml` for final run configs.
- PR 86 `meeting-05/jd.typ` for candidate TUM `cabinet`, Record3D `29-08`, and
  TUM `cabinet` LingBot result rows.
- Final `.artifacts/<experiment>/<run>/summary/`,
  `.artifacts/<experiment>/<run>/evaluation/`,
  `.artifacts/<experiment>/<run>/slam/`, and
  `.artifacts/<experiment>/<run>/visualization/` directories when available.

Non-JD evidence needed:

- Final method runs or limitations from other method clusters.
- Final team decision on the table layout and which runs are report-worthy.

Theory depth: concise in the main section. Put metric derivations in Metrics;
use Experiments for protocol, matrix, configs, and results.

Allowed sources:

- Final configs, final artifacts, final metrics, run logs, and tracked figures.
- PR 86 result rows as planning-final candidates only until artifact-validated.

PR caveat:

- PR 86 and PR 91 evidence may seed the experiment matrix, but final claims
  require final artifact validation.

Validation before final prose:

- For every reported run, record config path, commit or PR state, dataset
  sequence, frame sampling, method config, artifact root, reference source, and
  metric files.
- Do not use Rerun screenshots as substitutes for metrics.
- Keep failed or partial runs as limitations, not hidden exclusions.

### Discussion

Evidence owner cluster: JD-first seed material for debugging lessons; shared
section for final team interpretation.

JD evidence:

- `src/prml_vslam/methods/vista/README.md` for method-local world frame and
  live/export geometry asymmetry.
- `src/prml_vslam/visualization/README.md` and
  `src/prml_vslam/visualization/RERUN_SEMANTICS.md` for viewer artifact
  boundaries and entity semantics.
- `src/prml_vslam/eval/README.md` for current evaluation limits.
- PR 86 `meeting-03/jd.typ`, `meeting-04/jd.typ`, and `meeting-05/jd.typ` for
  typed multiprocessing, frame-convention challenges, Rerun stabilization, and
  ADVIO/Record3D alignment lessons.

Non-JD evidence needed:

- Teammate-specific retrospective points.
- Final method-quality interpretation across all contributed methods.

Theory depth: selective. Use theory to explain why failures happened and why
the final evaluation protocol is defensible.

Allowed sources:

- Debugging evidence from tracked docs/code, final artifacts, PR 86 planning
  material, and final team retrospective notes.

PR caveat:

- PR 86 lessons are planning-final, but final wording should match the final
  implementation and final artifact evidence.

Validation before final prose:

- Separate viewer correctness from scientific artifact correctness.
- Separate integration maturity from method quality.
- Discuss limitations honestly: cloud evaluation, efficiency evaluation, local
  GPU constraints, PR-dependent work, and dataset coverage if still true.

### Conclusion

Evidence owner cluster: shared section, JD-first seed material for the final
pipeline recommendation once final metrics exist.

JD evidence:

- `README.md` for deliverables and final recommendation framing.
- Final experiment artifacts and metrics for the actual recommendation.
- `.omx/specs/report-final-slides/report-section-candidates.md` for candidate
  future-work items.

Non-JD evidence needed:

- Final team consensus on recommendation and future work.
- Final team contribution summary.

Theory depth: concise. Do not introduce new theory in the conclusion.

Allowed sources:

- Final metrics, final artifacts, tracked report sections, and agreed team
  conclusions.

PR caveat:

- PR 88 and PR 91 may shape the final recommendation only after their final
  code/artifacts are validated for the report freeze.

Validation before final prose:

- Ensure the recommendation is backed by final results.
- Keep future work concrete: full benchmark sweep, dense-cloud evaluation,
  efficiency measurement, custom dataset expansion, optional ARCore baseline,
  and operator-facing visualization or reconstruction.

## Cross-Section Validation Checklist

- Every final claim must be traceable to a code path, artifact path, figure
  path, metric file, bibliography entry, or lecture requirement.
- Numerical results must come from final artifact files, not only PR 86 slides.
- PR-derived seed material must be rechecked against final branch state.
- Missing bibliography entries must be added before final prose uses the
  corresponding theory.
- Equal participation remains a deliverable constraint; this guide only maps
  evidence clusters.
