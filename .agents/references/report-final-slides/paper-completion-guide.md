# Final Paper Completion Guide

This guide records the current research state for completing the final PRML
VSLAM paper. It is derived from the prior transcript
`019ebae0-c954-7a20-8a2c-332e3b644144`, the existing OMX research artifacts,
the tracked agent references, current `origin/main`, and the planning-final
branches `codex/pr88-dataset-simplification` and
`codex/pr91-lingbot-simplify`.

The report should be written as a scientific benchmark-methodology paper, not
as a final leaderboard. The current repository has no frozen real benchmark
matrix yet. Therefore the strongest defensible contribution is the
measurement substrate: source normalization, method adapters, frame/scale
semantics, alignment protocol, artifacts, manifests, and diagnostic
visualization.

## Locked Decisions From The Transcript

- The first report/presentation work intentionally separated requirements,
  source maps, and evidence ownership from final authorship or speaking
  ownership.
- The report has a 15-page main-text target excluding bibliography and
  appendix; the final presentation has 20 minutes total and five equal speaking
  shares.
- All five team members must remain visible as equal participants. The
  JD-first material is seed material and evidence ownership, not final
  authorship or final team-credit assignment.
- The current paper iteration should focus on pipeline, dataset structure,
  source normalization, transforms, alignment, and method-interface boundaries.
- ViSTA, MASt3R, trajectory evaluation, and dense point-cloud metrics must not
  be overclaimed as final owned results. They can be explained where their
  interfaces and output contracts are necessary for interpreting the benchmark.
- Architecture diagrams are supplementary. Main text should describe
  scientific consequences rather than internal implementation mechanics.
- Report prose should avoid internal branch names, initials, PR numbers,
  variable names, and low-level runtime conventions unless the exact term is a
  scientific contract.

## Highest-Value Source Collection

Use these sources before adding or revising scientific claims:

- `README.md` and `docs/Questions.md` for challenge framing, scope, and
  emergency-call/operator motivation.
- `graphify-out/GRAPH_REPORT.md` for core abstractions:
  `StageKey`, `SequenceManifest`, `ArtifactRef`, `MethodId`,
  `PreparedBenchmarkInputs`, `PathConfig`, `FrameTransform`,
  `StageRuntimeUpdate`, and related communities.
- `src/prml_vslam/pipeline/README.md` and `REQUIREMENTS.md` for deterministic
  linear execution, artifacts, manifests, stage results, and live update
  boundaries.
- `src/prml_vslam/sources/README.md`, `sources/datasets/README.md`,
  `sources/datasets/advio/README.md`,
  `sources/datasets/tum_rgbd/README.md`, and `sources/record3d/README.md` for
  source normalization and dataset semantics.
- `src/prml_vslam/methods/README.md`, `methods/REQUIREMENTS.md`, and
  `methods/vista/README.md` for method-wrapper boundaries and ViSTA output
  semantics.
- `src/prml_vslam/alignment/README.md`, `eval/README.md`,
  `reconstruction/README.md`, and `visualization/README.md` for alignment,
  evaluation, reconstruction, and Rerun boundaries.
- `codex/pr88-dataset-simplification` source docs and code for offline
  Record3D archives, normalized dataset store, long-form dataset statistics,
  reusable observation sequences, and full-scene dataset simplification.
- `codex/pr91-lingbot-simplify` source docs and code for LingBot-Map backend
  configuration, normalized trajectory export, depth-backed dense PLY export,
  and checkpoint/runtime assumptions.
- `.omx/specs/report-final-slides/report-section-candidates.md` and
  `.agents/references/report-final-slides/responsibility-guide.md` for earlier
  section mapping and validation gates.
- `docs/literature/tex-src/arXiv-GCT/` and `docs/literature/pdf/GCT.pdf` for
  LingBot-Map method theory.
- `docs/literature/tex-src/arXiv-ViSTA-SLAM/` and
  `docs/literature/tex-src/arXiv-MASt3R-SLAM/` for method-theory summaries.

Do not use tests, app UI files, or raw chat text as manuscript evidence.
Tests may confirm implementation behavior during verification, but they are not
primary report references.

## Paper Contents To Prioritize

The paper should present the problem as uncalibrated monocular VSLAM for
smartphone video under heterogeneous source and frame conventions. The
scientific gap is not only method selection; it is the lack of a trustworthy
benchmark substrate when public datasets, self-recorded RGB-D captures,
method-local SLAM worlds, and viewer diagnostics all use different coordinate
and provenance conventions.

The most important current contribution is the normalized benchmark substrate.
Describe how the source stage converts ADVIO, TUM RGB-D, and Record3D into
timestamped observations with camera models, optional poses, optional depth,
and provenance. Explain why normalized stores matter: full-frame payloads are
materialized once, while frame stride and target frame rate remain run-local
policy. This is more scientifically relevant than UI or app mechanics.

The method section should compare method families by their scientific interface
rather than by unsupported results. ViSTA-SLAM contributes a symmetric
two-view association frontend plus Sim(3) pose-graph backend. MASt3R-SLAM
contributes learned two-view 3D reconstruction priors plus pointmap matching,
tracking, fusion, loop closure, and global optimization under a central-camera
assumption. LingBot-Map contributes Geometric Context Attention with anchor
context, a local pose-reference window, and trajectory memory for causal
streaming reconstruction. Our project contribution is the adapter and
normalization layer that makes their outputs comparable.

The alignment/evaluation section should remain equation-rich. Keep pinhole
backprojection, Sim(3) trajectory alignment, gravity-aware alignment, and ICP
registration. Treat ICP as a placement and dense-geometry diagnostic unless
final dense metric artifacts are available. State the reference trajectory,
association rule, alignment mode, cloud reference, and threshold before any
metric value.

The experiment section should be a protocol and matrix until final runs exist.
Do not report method rankings, dense-cloud scores, or efficiency results
without frozen artifacts. A valid final result row should include dataset,
sequence, method, source sampling policy, trajectory reference, alignment mode,
cloud reference, ICP threshold, processed frame count, hardware/runtime, and
metric artifact path.

## GCT Distillation

LingBot-Map is a feed-forward streaming 3D reconstruction model built on a
Geometric Context Transformer. It processes each new image causally, predicts
camera pose and depth, and uses three learned context types. Anchor context
uses initial frames to establish coordinate and scale grounding. The local
pose-reference window keeps dense recent image tokens for local geometry. The
trajectory memory retains compact per-frame tokens for older observations so
long-range trajectory context is not discarded.

The paper distinguishes Direct Output mode and visual-odometry mode. Direct
mode keeps one continuous state and directly predicts absolute poses and dense
depth; it is preferred within the effective sequence-length range. The
visual-odometry mode partitions very long sequences into overlapping windows
and fuses consecutive windows through Sim(3), trading bounded memory for
additional boundary drift.

For this repository, do not claim upstream leaderboard results as project
results. The project-facing LingBot contribution is an adapter that consumes
normalized observations and persists a normalized trajectory plus a dense PLY
derived from predicted depth. Depth maps, point maps, and confidence rasters
are upstream-native internals unless the repository later promotes them to
first-class tested artifacts.

## Validation Before Final Prose

Before any final-result sentence is added, verify that the claimed run exists
as a frozen artifact with manifest, config, normalized input, method output,
alignment metadata, and metric CSV/JSON files. Before any external method claim
is added, verify it against the local TeX/PDF source or the cited primary
paper. Before any dataset claim is added, verify it against the package README
and the source adapter code for that dataset. Before any figure or table is
used as evidence, verify that its caption states what produced it and whether
it is a result, protocol checklist, or supplementary architecture diagram.
