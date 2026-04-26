# PRML VSLAM Package Requirements

## Purpose

This document is the concise source of truth for the top-level package architecture in `src/prml_vslam/`.

Use this file for package-root ownership rules and cross-package contract constraints. Use package-local `README.md` or `REQUIREMENTS.md` files for deeper, package-specific explanations. Streamlit app requirements live in [`app/REQUIREMENTS.md`](./app/REQUIREMENTS.md), not here. Human-facing minimal-public-surface and migration rationale live in [`../../docs/architecture/interfaces-and-contracts.md`](../../docs/architecture/interfaces-and-contracts.md).

## Current State

- The repository has stable top-level package slices: `alignment`, `app`,
  `eval`, `interfaces`, `methods`, `pipeline`, `plotting`, `reconstruction`,
  `sources`, `utils`, and `visualization`.
- This file is the current canonical location for top-level module ownership and cross-package contract placement rules.
- Package-local `README.md` and `REQUIREMENTS.md` files already carry the deeper package-level guidance.
- The current architecture is typed and artifact-first, with offline benchmark execution as the core and bounded live streaming around it.

## Target State

- Keep top-level package ownership and cross-package contract placement rules centralized in this file.
- Keep package-local `README.md` files explanatory and package-local `REQUIREMENTS.md` files concise and normative.
- Keep one semantic concept attached to one owning module or namespace.
- Keep the app as a launch and monitoring surface rather than a second pipeline implementation.

## Responsibilities

- `alignment`
  - owns derived alignment logic that interprets normalized SLAM artifacts without mutating them
  - examples include dominant-ground detection, viewer-scoped ground alignment metadata, and future gravity/reference-assisted alignment helpers
  - does not own backend execution, benchmark metric computation, or Rerun logging
- `app`
  - owns Streamlit pages, typed page state (`prml_vslam.app.models`), UI composition, and launch surfaces
  - does not own pipeline semantics, transport decoding, dataset normalization, or stage-policy logic
- `eval`
  - owns explicit evaluation logic and typed evaluation contracts
  - owns typed comparison artifacts and statistics, including future persisted
    estimated-vs-reference intrinsics comparisons
  - does not own method execution, source normalization, or app state
- `interfaces`
  - owns repo-wide shared datamodels only
  - examples include `CameraIntrinsics`, `FrameTransform`, `Observation`,
    `PointCloud`, `PointMap`, and `DepthMap`
  - owns reusable camera artifact datamodels and pure camera-model transforms
    when the same intrinsics semantics cross method, evaluation, plotting, and
    app boundaries
- `sources`
  - owns source backend config variants, source-stage config/runtime/contracts,
    dataset catalogs, replay adapters, Record3D transports, sequence
    materialization, source-stage outputs, and prepared reference identifiers
    and DTOs such as `PreparedBenchmarkInputs`
  - preserves the currently supported dataset modalities and dataset-specific
    auxiliary/reference assets, including ADVIO Tango data and reference-cloud
    preparation
- `visualization`
  - owns viewer policy, preserved native viewer artifacts, and the repo-owned Rerun integration layer
- `methods`
  - owns backend-specific execution seams and thin method-wrapper integration
  - `prml_vslam.methods.protocols` owns package-local SLAM behavior seams such as `SlamBackend`
  - owns backend-native artifact interpretation and standardization, including
    method-specific preprocessing metadata needed to interpret native outputs
  - does not own pipeline planning or evaluation policy
- `pipeline`
  - owns orchestration, run contracts, artifact layout, stage planning, events,
    projected snapshots, manifests, summaries, pipeline-owned runtime
    coordination, and repo-local execution-lifecycle policy
  - uses `RunConfig` as the canonical launch/planning contract; domain
    stage-facing configs belong to each domain package's `stage/` modules
  - `RunPlan` source snapshots include configured source sampling policy and
    nullable expected source cadence, not measured runtime throughput
  - does not own transport decoding, app rendering, or benchmark metrics logic
- `plotting`
  - owns reusable figure construction helpers
  - does not own orchestration or domain-policy decisions
- `utils`
  - owns shared low-level infrastructure such as config helpers, path handling, logging, and generic geometry/runtime helpers
  - may own generic reusable IO/math helpers, such as color-preserving PLY IO,
    but not method-native artifact semantics or stage-specific comparison policy
  - does not own package-specific workflow policy

## Non-Negotiable Requirements

- One semantic concept must have one owning module.
- Derived alignment transforms remain explicit repo-owned artifacts; they must not silently replace native SLAM trajectories or point clouds.
- Runtime camera poses use explicit `T_world_camera` semantics at repo-owned
  boundaries. Inverse transforms belong only at call sites whose external APIs
  require world-to-camera matrices.
- Unstructured point clouds, raster-aligned pointmaps, and metric depth maps
  are distinct shared geometry contracts. Sparse source clouds such as ADVIO
  Tango payloads must not be represented as pointmaps without an explicit
  projection step.
- Promote a type into `prml_vslam.interfaces.*` only when multiple top-level packages import it and the semantics are truly identical across those packages.
- Shared repo-wide datamodels belong in `prml_vslam.interfaces.*`.
- `prml_vslam.sources.replay` owns `ObservationStream`.
- `prml_vslam.sources.protocols` owns source-provider seams such as
  `OfflineSequenceSource` and `StreamingSequenceSource`.
- Package-local DTOs, configs, manifests, requests, and results belong in `<package>/contracts.py` or
  `<package>/contracts/` when a package owns several distinct contract slices.
- Package-local `Protocol` seams belong in `<package>/protocols.py` when a package truly owns that behavior boundary.
- `prml_vslam.methods.protocols` owns `SlamBackend`.
- `prml_vslam.app.models` owns Streamlit-only UI and session state.
- `services.py` modules own implementations only; they must not become the home of public contract types.
- The app must stay a launch and monitoring surface rather than a second pipeline implementation.
- The pipeline owns SLAM stage lifecycle policy and the run association for
  normalized SLAM artifact bundles; backend-private config and output policy
  belong in `methods`.
- The pipeline owns public runtime events, projected snapshots, stage planning
  semantics, stage-key/config-section mapping, and execution/resource policy;
  Ray-specific refs and mailboxes stay behind runtime/proxy plumbing.
- External-method wrappers must stay thin and normalize into repo-owned pipeline artifacts instead of inventing parallel public result shapes.
- Method-native artifact standardization belongs with the method wrapper; shared
  DTOs and low-level helpers may be imported from `interfaces` and `utils`,
  but the pipeline must not interpret backend-native arrays directly.
- Persisted diagnostic or benchmark comparisons belong in `eval`; app pages and
  plotting helpers may render them but must not define their semantics.
- Record3D live pipeline requests must use a transport-aware typed source contract instead of encoding USB or Wi-Fi details into ad hoc `source_id` strings alone.
- `PathConfig` remains the single owner of repo-owned path semantics.

## Explicit Non-Goals

- This file is not the home for app UX requirements.
- This file is not a package-by-package implementation guide.
- This file must not duplicate package-local architecture notes that already belong in lower-level docs.
- This file must not become a second copy of the human-facing minimal-public-surface and migration rationale from [`docs/architecture/interfaces-and-contracts.md`](../../docs/architecture/interfaces-and-contracts.md).

## Validation

- It stays consistent with [`docs/architecture/interfaces-and-contracts.md`](../../docs/architecture/interfaces-and-contracts.md).
- It gives one clear answer to “which top-level package owns this concern?”
- It does not restate package-local requirements that already belong in lower package docs.
- It stays aligned with the shared section structure used by the other existing `REQUIREMENTS.md` files.

## Pipeline Stage Refactor Requirements

- Stage configs are declarative policy contracts. They validate stage policy,
  resource hints, telemetry, cleanup, and failure-provenance settings; they do
  not construct runtime objects or Ray actors.
- `RuntimeManager` is the current construction authority for lazy local stage
  runtime handles. Ray-backed run orchestration lives in `RayPipelineBackend`
  and `RunCoordinatorActor`; independent per-stage Ray-hosted runtimes are not
  a current public contract.
- Backend, source, and reconstruction variant configs may use
  `FactoryConfig.setup_target()` when they construct concrete domain or source
  implementations. Stage policy configs must not duplicate that construction
  role.
- Stage runtime boundaries use explicit typed contracts for terminal results,
  live updates, status, inputs, and private runtime-only wrappers where those
  wrappers carry real boundary semantics.
- DTOs, stage runtimes, and runtime proxies must not implement Rerun SDK
  conversion. Stage/domain-specific visualization adapters create neutral
  visualization items; Rerun sinks are the only SDK callers.
- Stage runtimes must expose queryable live status through pipeline-owned
  status DTOs for lifecycle, progress, throughput/FPS, latency, queue or
  credit counters that the runtime actually owns, and resource assignment.
