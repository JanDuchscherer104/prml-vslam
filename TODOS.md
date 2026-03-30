# PRML VSLAM TODOs

This file tracks the active implementation backlog. The older bootstrap checklist remains in
`docs/TODOS.md`; this file is the current project-facing task list.

The working rule is strict: write tests first for each new unit under test, then implement the
smallest change that makes them pass, then refactor.

## Now

- [ ] Keep the baseline healthy:
  - `uv run pytest`
  - `make report-pdf`
  - fix regressions before adding new features
- [ ] Extend the pipeline contract for explicit execution modes:
  - add `PipelineMode`
  - distinguish batch and streaming stage subsets
  - add tests before updating `src/prml_vslam/pipeline/contracts.py`
- [ ] Expand stage planning tests:
  - batch stage ordering
  - optional stage inclusion and exclusion
  - artifact root naming
  - invalid request validation
- [ ] Add a `capture_manifest` config model:
  - define required fields for video path, timestamps, device metadata, and optional ARCore side
    channels
  - add round-trip serialization tests first
- [ ] Add normalized artifact metadata models:
  - trajectory sidecar contract
  - dense geometry sidecar contract
  - explicit frame, unit, and timestamp provenance
  - validation tests before implementation
- [ ] Implement a workspace materializer service:
  - create planned directories and stub artifact files under `tmp_path`
  - persist manifest and config snapshots
  - fail clearly on invalid or conflicting filesystem state
- [ ] Add CLI coverage for the planning surface:
  - test `plan-run`
  - add a materialization command only after tests define its output contract

## Next

- [ ] Add application settings with `pydantic-settings`:
  - method repo roots
  - checkpoint roots
  - dataset roots
  - default output roots
- [ ] Add method config models for ViSTA-SLAM and MASt3R-SLAM:
  - keep machine-local paths out of experiment configs
  - use config-as-factory consistently
- [ ] Implement wrapper preflight services:
  - repo path checks
  - checkpoint checks
  - mode support checks
  - dry-run command assembly tests first
- [ ] Add fake method runners:
  - emit deterministic stub trajectory and point-cloud outputs
  - use these to unblock normalization and evaluation tests
- [ ] Update `docs/agent_reference.md` as soon as artifact contracts or alignment semantics change

## After That

- [ ] Implement trajectory normalization:
  - normalize to TUM plus JSON sidecar
  - record frame naming and alignment assumptions
- [ ] Implement dense normalization:
  - normalize to PLY plus metadata sidecar
  - record units, color availability, and preprocessing
- [ ] Add trajectory evaluation adapters around `evo`
- [ ] Add dense evaluation adapters around Open3D
- [ ] Generate comparison-ready plots from normalized artifacts rather than raw method output

## External Integration

- [ ] Integrate ViSTA-SLAM batch mode first
- [ ] Integrate MASt3R-SLAM batch mode second
- [ ] Document external environment setup and unsupported cases
- [ ] Run both methods on at least one small public sequence and one custom sequence

## Streaming

- [ ] Define the streaming stage subset explicitly
- [ ] Add chunk persistence and stream finalization contracts
- [ ] Add online visualization/export hooks
- [ ] Keep streaming concerns isolated from the batch pipeline

## Reference Reconstruction and 3DGS

- [ ] Select the reference reconstruction path:
  - COLMAP
  - Meshroom
  - Nerfstudio / 3DGS only as downstream stages
- [ ] Define how reference geometry is aligned to benchmark artifacts
- [ ] Treat 3DGS as a downstream consumer of stable poses and geometry, not as the first benchmark
  target

## Reporting and Benchmarking

- [ ] Wire the new report fragment into the report only when its placement is agreed
- [ ] Keep citations and benchmark protocol docs in sync with implementation
- [ ] Build result tables only after alignment policy and artifact contracts are stable
- [ ] Write the final recommendation only after both methods have passed through the same normalized
  pipeline

## Do Not Start With

- [ ] Do not start with live streaming integration
- [ ] Do not start with end-to-end 3DGS
- [ ] Do not start with dense metric dashboards before artifact normalization exists
- [ ] Do not hide alignment or evaluation inside method wrappers
