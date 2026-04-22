# Methods Guide

This package owns backend ids, backend-private config, runtime session and
update seams, backend descriptors, and the thin wrappers that adapt external
SLAM systems to the repository’s normalized pipeline contracts. Shared pipeline
planning and provenance logic does not live here; this package exists to answer
two narrower questions: which backends the repository knows about, and how a
concrete backend consumes normalized repo-owned inputs and returns normalized
[`SlamArtifacts`](../pipeline/contracts/artifacts.py#L25).

The package is intentionally small. The public center of gravity is
[`MethodId`](./contracts.py#L12),
[`SlamBackendConfig`](./contracts.py#L41),
[`SlamOutputPolicy`](./contracts.py#L31),
[`StreamingSlamBackend`](./protocols.py#L17),
[`OfflineSlamBackend`](./protocols.py#L31),
[`StreamingSlamBackend`](./protocols.py#L49),
[`BackendDescriptor`](./descriptors.py#L21),
[`BackendFactory`](./factory.py#L25), and the method-owned
[`SlamUpdate`](./updates.py#L13) plus explicit backend-event translation in
[`translate_slam_update()`](./events.py#L102). At the concrete-wrapper level,
the current executable backends are the repository-local
[`MockSlamBackend`](./mock_vslam.py#L44) and the canonical
[`VistaSlamBackend`](./vista/adapter.py#L22).

## Current Implementation

The pipeline never instantiates backends directly. It goes through
[`BackendFactory.describe()`](./factory.py#L28) to discover capabilities and
resource defaults, and through [`BackendFactory.build()`](./factory.py#L78) to
construct one executable backend from the typed backend spec embedded in the
pipeline request. That factory is intentionally thin: it maps request-time
backend specs to repo-local wrapper configs and then lets those configs build
their concrete targets.

The actual execution seams live in [`protocols.py`](./protocols.py#L16). Offline
backends implement [`run_sequence()`](./protocols.py#L36) over a normalized
[`SequenceManifest`](../pipeline/contracts/sequence.py#L10), optional prepared
benchmark inputs, and a method-owned output policy. Streaming backends implement
[`start_streaming(...)`](./protocols.py#L54), which receives one method-owned
session-init bundle plus the runtime controls before returning a
[`StreamingSlamBackend`](./protocols.py#L17) that consumes incremental
[`FramePacket`](../interfaces/runtime.py#L68) values and produces
[`SlamUpdate`](./updates.py#L13) telemetry before closing into the same
normalized [`SlamArtifacts`](../pipeline/contracts/artifacts.py#L25) contract.

The current package therefore has three layers. The contract layer lives in
[`contracts.py`](./contracts.py#L12), [`descriptors.py`](./descriptors.py#L10),
[`protocols.py`](./protocols.py#L17), [`updates.py`](./updates.py#L13), and
[`events.py`](./events.py#L15). The construction layer lives in
[`factory.py`](./factory.py#L25). The wrapper layer lives in
[`mock_vslam.py`](./mock_vslam.py#L44) and the
[`vista/`](./vista/README.md) subtree. The package root
[`__init__.py`](./__init__.py#L1) re-exports only the small surface that other
packages are expected to import directly.

## Design Rationale

This package is not supposed to own benchmark policy, app orchestration, or
viewer orchestration. It exists to keep backend-specific concerns local. That is
why method selection is encoded as the small enum
[`MethodId`](./contracts.py#L12), backend runtime controls stay in the
method-owned [`SlamBackendConfig`](./contracts.py#L41), and output materialization
preferences stay in [`SlamOutputPolicy`](./contracts.py#L31) rather than being
smuggled through app-layer settings or benchmark configs.

The wrappers also stay deliberately importer-oriented. A wrapper is allowed to
resolve upstream repo paths, check for required checkpoints, instantiate
upstream runtime objects, preserve selected upstream-native outputs, and
normalize those outputs back into repository contracts. It is not supposed to
re-implement upstream algorithms or own pipeline semantics. That design is
clearest in the ViSTA wrapper, where the main adapter stays thin and delegates
upstream bootstrap, preprocessing, live session stepping, and artifact import
to package-local helpers inside [`vista/config.py`](./vista/config.py#L17),
[`vista/runtime.py`](./vista/runtime.py#L75),
[`vista/preprocess.py`](./vista/preprocess.py#L39),
[`vista/session.py`](./vista/session.py#L28), and
[`vista/artifacts.py`](./vista/artifacts.py#L27).

The package also keeps a strict split between method-owned live updates and
pipeline-owned transport. Backends emit [`SlamUpdate`](./updates.py#L13) because
that is the method-layer view of incremental SLAM state. The pipeline then
translates those updates into transport-safe backend notices through
[`translate_slam_update()`](./events.py#L102), which yields typed
[`BackendEvent`](./events.py#L90) values such as
[`PoseEstimated`](./events.py#L15) and
[`KeyframeVisualizationReady`](./events.py#L38). That split keeps the wrappers
free to think in backend-native terms while still giving the pipeline one stable
transport vocabulary.

## Package Map

The methods package is smaller than `pipeline`, but the same symbol-first map is
still useful.

```text
src/prml_vslam/methods
├── README.md                                      # package guide
├── REQUIREMENTS.md                                # package constraints
├── __init__.py                                    # curated public methods surface
│   ├── MethodId                                   # public backend id enum
│   ├── MockSlamBackendConfig                      # mock wrapper config export
│   ├── VistaSlamBackend                           # ViSTA backend export
│   └── VistaSlamBackendConfig                     # ViSTA config export
├── contracts.py                                   # method ids and backend-owned config
│   ├── MethodId                                   # supported backend ids
│   ├── SlamOutputPolicy                           # output materialization policy
│   └── SlamBackendConfig                          # shared backend runtime controls
├── descriptors.py                                 # backend capability and resource descriptors
│   ├── BackendCapabilities                        # capability surface
│   └── BackendDescriptor                          # descriptor returned to pipeline
├── events.py                                      # transport-safe backend notice contracts
│   ├── PoseEstimated                              # pose telemetry notice
│   ├── KeyframeAccepted                           # keyframe-acceptance notice
│   ├── KeyframeVisualizationReady                 # preview/image/depth/pointmap handles
│   ├── MapStatsUpdated                            # sparse/dense map telemetry
│   ├── BackendWarning                             # non-fatal backend warning
│   ├── BackendError                               # fatal or actionable backend error
│   ├── SessionClosed                              # terminal session notice
│   ├── BackendEvent                               # backend notice union
│   └── translate_slam_update                      # update -> event translator
├── factory.py                                     # typed backend factory
│   ├── BackendFactoryProtocol                     # factory seam
│   └── BackendFactory                             # repo-local factory implementation
├── mock_vslam.py                                  # repository-local mock backend
│   ├── MockSlamBackendConfig                      # mock backend config
│   ├── MockSlamBackend                            # mock offline/streaming backend
│   └── MockStreamingSlamBackend                            # mock streaming runtime
├── protocols.py                                   # backend and session seams
│   ├── StreamingSlamBackend                                # streaming backend protocol
│   ├── OfflineSlamBackend                         # offline execution protocol
│   ├── StreamingSlamBackend                       # streaming execution protocol
│   └── SlamBackend                                # combined offline + streaming protocol
├── updates.py                                     # method-owned live update DTO
│   └── SlamUpdate                                 # incremental backend update
└── vista                                           # canonical ViSTA integration
    ├── README.md                                  # ViSTA-specific wrapper guide
    ├── REQUIREMENTS.md                            # ViSTA wrapper constraints
    ├── __init__.py                                # ViSTA export surface
    │   ├── VistaSlamBackend                       # ViSTA backend export
    │   ├── VistaSlamBackendConfig                 # ViSTA config export
    │   └── VistaSlamRuntime                       # ViSTA session export
    ├── adapter.py                                 # thin backend adapter
    │   └── VistaSlamBackend                       # offline + streaming ViSTA wrapper
    ├── artifacts.py                               # native-export normalization
    │   └── build_vista_artifacts                  # native output -> SlamArtifacts
    ├── config.py                                  # ViSTA-specific backend config
    │   └── VistaSlamBackendConfig                 # concrete ViSTA config
    ├── preprocess.py                              # upstream-faithful image preprocessing
    │   ├── PreparedVistaFrame                     # prepared frame bundle
    │   ├── VistaFramePreprocessor                 # preprocessing protocol
    │   ├── UpstreamVistaFramePreprocessor         # upstream crop/resize implementation
    │   └── vista_numpy_array                      # array normalization helper
    ├── runtime.py                                 # upstream runtime bootstrap helpers
    │   ├── VistaRuntimeComponents                 # concrete runtime bundle
    │   ├── build_vista_runtime_components         # upstream runtime builder
    │   └── resolve_vocab_path                     # vocabulary cache resolver
    └── session.py                                 # streaming session wrapper
        ├── VistaSlamRuntime                       # live session adapter
        └── create_vista_runtime                   # session construction helper
```

## Core Contracts

The smallest stable public contract here is [`MethodId`](./contracts.py#L12),
which names the backends that the repository understands. That enum is paired
with [`SlamBackendConfig`](./contracts.py#L41), which holds shared backend
runtime knobs such as `max_frames`, and with
[`SlamOutputPolicy`](./contracts.py#L31), which lets the pipeline tell a method
whether dense or sparse geometry should actually be materialized.

Capability discovery is deliberately separate from runtime execution. The
pipeline sees backend capability and resource metadata only through
[`BackendDescriptor`](./descriptors.py#L21) and
[`BackendCapabilities`](./descriptors.py#L10), both returned by
[`BackendFactory.describe()`](./factory.py#L28). Actual execution is then
governed by the protocol layer in [`protocols.py`](./protocols.py#L17). A method
that only supports batch processing can implement
[`OfflineSlamBackend`](./protocols.py#L31). A method that supports incremental
execution can implement [`StreamingSlamBackend`](./protocols.py#L49). The
repository currently prefers backends that satisfy the combined
[`SlamBackend`](./protocols.py#L64) protocol, because the pipeline supports both
offline and streaming runs.

The method-owned live update surface is [`SlamUpdate`](./updates.py#L13). It is
allowed to carry backend-facing notions such as keyframe acceptance,
camera-local pointmaps, preview images, and backend warnings. The transport-safe
surface that the pipeline consumes is different. That surface is the explicit
backend-event vocabulary in [`events.py`](./events.py#L15), especially
[`BackendEvent`](./events.py#L90) and
[`translate_slam_update()`](./events.py#L102). The translation step is what
lets the method package stay backend-aware without forcing the pipeline to
depend on one backend’s internal update shape.

## Module Responsibilities

The package root [`__init__.py`](./__init__.py#L1) is intentionally small and
re-exports only the symbols that other packages are expected to import
regularly. The concrete ids and shared backend controls live in
[`contracts.py`](./contracts.py#L12), while capability and scheduling metadata
live in [`descriptors.py`](./descriptors.py#L10). The live transport notice
layer lives in [`events.py`](./events.py#L15), and the abstract backend and
session seams live in [`protocols.py`](./protocols.py#L17).

[`factory.py`](./factory.py#L25) is the bridge from pipeline request-time
backend specs into real wrapper instances. It is the only place in this package
that should know how to describe all backends centrally. Wrapper-local bootstrap
logic belongs in the wrapper itself. The repository-local
[`mock_vslam.py`](./mock_vslam.py#L32) backend exists for smoke runs and live
preview development; it is not trying to be a faithful research baseline. It
implements the same repository protocols as the real wrappers, which makes it a
useful reference for the minimum offline and streaming backend surface.

The canonical real integration is the [`vista/`](./vista/README.md) subtree.
[`adapter.py`](./vista/adapter.py#L22) is the thin backend wrapper that the
factory instantiates. [`config.py`](./vista/config.py#L17) owns ViSTA-specific
configuration. [`runtime.py`](./vista/runtime.py#L75) owns upstream runtime
bootstrap, vocabulary resolution, and namespace-package setup. [`preprocess.py`](./vista/preprocess.py#L39)
preserves the upstream image preprocessing path instead of duplicating it ad
hoc. [`session.py`](./vista/session.py#L28) exposes the upstream live path
through repo-owned streaming contracts, and [`artifacts.py`](./vista/artifacts.py#L27)
normalizes native end-of-run outputs back into the shared pipeline-owned
artifact contract.

## Execution Shape

From the methods package’s point of view, offline and streaming execution are
much simpler than they are in the pipeline package. Offline execution means a
wrapper consumes a normalized
[`SequenceManifest`](../pipeline/contracts/sequence.py#L10), optional prepared
benchmark inputs, and a method-owned config bundle, then writes normalized
[`SlamArtifacts`](../pipeline/contracts/artifacts.py#L25). Streaming execution
means a wrapper constructs a session, accepts incremental
[`FramePacket`](../interfaces/runtime.py#L68) values, emits method-owned
[`SlamUpdate`](./updates.py#L13) telemetry, and eventually closes into the same
artifact contract.

The important ownership rule is that methods never decide pipeline stage order
or run summary semantics. They only implement the backend-specific execution
body. If a backend has native output directories or native visualization files,
those may be preserved as extras, but the canonical repository contract remains
the normalized artifact bundle that the pipeline knows how to consume.

## Adding Or Editing A Backend

Adding a new backend usually starts in [`contracts.py`](./contracts.py#L12) and
[`factory.py`](./factory.py#L25). Add a new `MethodId`, define a concrete config
if the backend needs wrapper-specific controls, extend
[`BackendFactory.describe()`](./factory.py#L28) with truthful capabilities, and
extend [`BackendFactory.build()`](./factory.py#L78) so the typed pipeline spec
can actually produce the wrapper instance. The wrapper itself should then
implement the relevant protocol in [`protocols.py`](./protocols.py#L17) and
return normalized [`SlamArtifacts`](../pipeline/contracts/artifacts.py#L25)
instead of exposing upstream-native outputs as the main API.

Editing an existing backend interface follows the same pattern as in the
pipeline package, but with a narrower surface. If you widen live telemetry,
update [`SlamUpdate`](./updates.py#L13) and
[`translate_slam_update()`](./events.py#L102) together. If you widen final
artifacts, update the wrapper output normalization logic together with the
pipeline-side artifact flattening logic that consumes those artifacts. If you
change capability or resource assumptions, update
[`BackendDescriptor`](./descriptors.py#L21) through the factory at the same
time; the planner relies on that descriptor remaining truthful.

## ViSTA Notes

The ViSTA wrapper is the main example of the intended shape for a real backend
integration. It keeps the adapter thin, preserves upstream crop-and-resize
semantics inside the methods package, requires explicit upstream prerequisites,
and converts native exports back into normalized repository artifacts. It is
also the clearest place to see the split between method-owned live updates and
pipeline-owned transport. The session emits backend-facing
[`SlamUpdate`](./updates.py#L13) payloads, the methods package translates them
into explicit transport notices, and the pipeline handles the rest.

The package-specific details for ViSTA are intentionally kept out of this
top-level README. For preprocessing, live session semantics, export surfaces,
and Rerun layout notes, read [`methods/vista/README.md`](./vista/README.md).

## Contributor Starting Point

If you need to orient yourself quickly, start with
[`MethodId`](./contracts.py#L12),
[`SlamBackendConfig`](./contracts.py#L41),
[`StreamingSlamBackend`](./protocols.py#L17),
[`BackendFactory`](./factory.py#L25), and
[`SlamUpdate`](./updates.py#L13). Then read either
[`mock_vslam.py`](./mock_vslam.py#L32) for the minimum wrapper shape or
[`vista/adapter.py`](./vista/adapter.py#L22) plus
[`vista/session.py`](./vista/session.py#L28) for the canonical real wrapper.
