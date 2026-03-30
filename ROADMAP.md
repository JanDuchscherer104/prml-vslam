# PRML VSLAM Roadmap

This roadmap translates the current repo scaffold and research notes into an implementation order
that favors fast verification, low integration risk, and test-driven iteration.

The guiding rule is simple: implement repo-owned contracts and deterministic services before
wrapping heavy external systems. In practice, that means starting with the batch pipeline contract,
artifact layout, and normalization surfaces before attempting live streaming, dense SLAM execution,
or 3D Gaussian Splatting.

## Principles

- Prefer batch / offline execution first. It is easier to reproduce, test, and debug than streaming.
- Keep method execution, normalization, evaluation, and visualization as separate stages.
- Treat external methods as thin wrappers with explicit boundaries.
- Write tests before each new unit under test, and keep the red-green-refactor loop short.
- Do not let rendering quality hide trajectory or geometry failures.

## Phase 0: Keep the Scaffold Healthy

Goal: preserve a clean baseline while implementation work starts.

Deliverables:

- passing `pytest`
- passing `make report-pdf`
- stable CLI and package imports
- up-to-date planning docs and benchmark contract notes

Exit criteria:

- the repo remains installable and testable
- report and slides keep compiling without regressions

## Phase 1: Batch Pipeline Contract Foundation

Goal: make the benchmark pipeline concrete without depending on external SLAM tools.

Why this comes first:

- it is the easiest surface to verify with unit tests
- it locks down artifact layout and metadata semantics early
- later wrappers and evaluators can target stable repo-owned contracts

Deliverables:

- explicit pipeline mode support, with batch as the first-class path
- richer canonical stage IDs and stage metadata
- `capture_manifest` contract
- normalized trajectory and dense artifact sidecar contracts
- workspace / artifact materialization service
- CLI support for planning and materializing runs

Recommended first units under test:

- plan stage ordering
- optional stage inclusion and exclusion
- artifact root layout
- manifest serialization and validation
- sidecar metadata validation
- workspace materialization against `tmp_path`

Exit criteria:

- a planned run can be materialized deterministically into repo-owned directories and stub artifacts
- all new behavior is covered by targeted pytest tests

## Phase 2: Method Wrapper Preflight and Fake Execution

Goal: define method boundaries before attempting real integration.

Deliverables:

- `BaseSettings` application settings for repo roots, dataset roots, checkpoints, and output roots
- method-specific config models for ViSTA-SLAM and MASt3R-SLAM
- wrapper preflight checks for required paths, checkpoints, and modes
- fake or dry-run method runners that emit deterministic stub outputs

Why this order:

- command construction and preflight can be tested without GPUs or external repos
- failures become explicit before runtime execution exists
- config-as-factory patterns can stabilize before the wrappers grow

Exit criteria:

- method wrappers fail early and clearly when misconfigured
- wrapper configs can produce deterministic execution requests or shell commands

## Phase 3: Output Normalization

Goal: normalize upstream outputs into repo-owned benchmark artifacts.

Deliverables:

- trajectory normalization to TUM plus JSON sidecar
- dense geometry normalization to PLY plus metadata sidecar
- explicit frame, unit, and timestamp provenance recording
- alignment-policy metadata surfaces

Why this matters:

- cross-method evaluation is invalid until conventions are normalized
- downstream evaluation and visualization should never depend on raw upstream folder layouts

Exit criteria:

- at least one fake backend output and one real sample output can be normalized into the shared
  artifact contract

## Phase 4: Batch Evaluation

Goal: evaluate the normalized artifacts independently of the method wrappers.

Deliverables:

- trajectory metrics stage backed by `evo`
- dense metrics stage backed by Open3D and optionally CloudCompare
- persisted alignment transforms and preprocessing metadata
- comparison-ready metric summaries and plots

Testing strategy:

- unit tests for config and command/request assembly
- fixture-based tests for metric adapters on tiny synthetic artifacts
- golden-file tests for emitted summary JSON

Exit criteria:

- one batch benchmark can produce trajectory and dense metric artifacts reproducibly

## Phase 5: Real Method Integration

Goal: replace fake runners with actual external execution.

Priority:

1. ViSTA-SLAM batch path
2. MASt3R-SLAM batch path

Deliverables:

- documented setup for both external repos
- runnable wrapper entry points
- normalized outputs for at least one public and one custom sequence

Why batch first:

- fewer moving parts than streaming
- easier failure analysis
- closer to the paper-comparison deliverable

Exit criteria:

- both benchmark methods can run through the repo-owned batch pipeline

## Phase 6: Streaming Pipeline

Goal: add the operator-facing real-time path after the batch foundation is stable.

Deliverables:

- streaming stage subset
- chunk persistence and stream finalization
- online trajectory and local-map previews
- operator-facing visualization hooks

Constraints:

- do not couple streaming-specific latency concerns into the batch path
- keep live visualization downstream of normalized streaming artifacts where practical

Exit criteria:

- one live or pseudo-live sequence can be processed through the streaming path with explicit partial
  outputs

## Phase 7: Reference Reconstruction and 3DGS

Goal: add high-quality offline references and downstream scene rendering.

Deliverables:

- reference reconstruction stage using COLMAP, Meshroom, or equivalent
- optional Nerfstudio or 3DGS stage initialized from stable poses and geometry
- comparison between SLAM geometry and offline references

Important design choice:

- 3DGS is downstream, not the first benchmark target
- use it only after trajectory and coarse geometry are trustworthy

Exit criteria:

- at least one benchmark sequence can be rendered from normalized camera geometry into a useful
  downstream scene representation

## Phase 8: Benchmark Consolidation and Final Recommendation

Goal: turn the working pipeline into a benchmark with defensible conclusions.

Deliverables:

- batch and streaming benchmark tables
- qualitative failure analysis
- final method tradeoff summary
- integrated report and presentation updates

Exit criteria:

- the repo can support a final recommendation grounded in trajectory quality, dense geometry quality,
  and practical execution constraints

## Recommended Immediate Start

The best first implementation is the batch contract foundation:

1. extend pipeline contracts for mode and stage semantics
2. add `capture_manifest` and normalized sidecar models
3. implement a workspace materializer service
4. expose the flow through the CLI

This gives the shortest, cleanest TDD cycle in the repo and creates the boundaries every later
stage will rely on.
