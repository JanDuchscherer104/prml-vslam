# Datasets

This README is the implementation guide for the current dataset package in `prml_vslam.sources.datasets`.

Use [../REQUIREMENTS.md](../REQUIREMENTS.md) for top-level ownership rules. Use this file for the current code surfaces and typical usage patterns.

## Current Implementation

This package owns repository-local dataset adapters and dataset-facing contracts. The implemented targets are ADVIO,
TUM RGB-D, and Record3D.

Current simplification work must preserve the supported dataset surface. In particular:

- full-scene dataset downloads remain the only supported local fetch surface
- ADVIO remains trajectory-only for benchmark inputs
- TUM RGB-D dataset-provided reference cloud preparation remains in scope
- Record3D downloads cache full `.r3d` archives and derive RGB-D observations plus reference clouds from those archives
- the current ray-pipeline-facing dataset service and sequence surfaces remain the public integration boundary

The current ADVIO stack includes:

- typed ADVIO metadata plus dataset-contract specializations in `advio_models.py`
- typed ADVIO serving semantics and manifest payload contracts in `contracts.py`
- local path resolution and catalog lookups in `advio_layout.py` and `advio_sequence.py`
- typed file loading for timestamps, calibration, and trajectories in `advio_loading.py`
- dataset fetch and cache mechanics in `fetch.py` plus archive extraction flows in `advio_download.py`
- a high-level app- and pipeline-facing service in `advio_service.py`
- ADVIO replay stream assembly in `advio_replay_adapter.py`
- offline benchmark-input preparation, including typed reference trajectories, in `advio_sequence.py` and
  `advio_service.py`

The replay path is layered on purpose:

- `prml_vslam.sources.replay` owns generic replay pacing plus PyAV video and image-sequence observation sources
- `advio_replay_adapter.py` adds ADVIO-specific timestamps, calibration, and pose alignment
- `advio_sequence.py` exposes the sequence-level entry points used by the app and tests

The TUM RGB-D stack mirrors the same service shape where practical:

- typed metadata plus dataset-contract specializations in `tum_rgbd/tum_rgbd_models.py`
- ViSTA-compatible scene catalog and local path resolution in `tum_rgbd/tum_rgbd_layout.py`
- TUM timestamp-list parsing, RGB/depth/pose association, and Freiburg intrinsics in
  `tum_rgbd/tum_rgbd_loading.py`
- TGZ download/extraction flows in `tum_rgbd/tum_rgbd_download.py`
- sequence manifest and benchmark input preparation in `tum_rgbd/tum_rgbd_sequence.py`
- image-sequence loop preview in `tum_rgbd/tum_rgbd_replay_adapter.py`

The Record3D stack follows the same dataset-service boundary for full `.r3d` archives:

- static Zenodo catalog and local archive path resolution in `record3d/record3d_layout.py`
- full-archive download and SHA-256 verification in `record3d/record3d_download.py`
- RGB-D frame decoding, trajectory preparation, and reference-cloud generation in `record3d/record3d_sequence.py`
- replay and offline source integration through `record3d/record3d_service.py`

Package-local guides:

- [ADVIO guide](./advio/README.md)
- [TUM RGB-D guide](./tum_rgbd/README.md)

## Stage Boundaries

The dataset layer feeds the current pipeline/app/runtime stack through a small
set of typed boundaries. Those boundaries are the current source of truth for
what downstream code is allowed to rely on.

### Source-Config Boundary

Upstream of the dataset package, pipeline source-stage configs use:

- [AdvioSourceConfig](../config.py)
  - selects `source_id = "advio"` and `sequence_id`
  - carries shared frame sampling via [FrameSelectionConfig](./contracts.py:115)
- [TumRgbdSourceConfig](../config.py)
  - selects `source_id = "tum_rgbd"` and `sequence_id`

The persisted source-stage wrapper is
[`SourceStageConfig`](../stage/config.py). Source-stage runtime inputs and
outputs live in [`../stage/contracts.py`](../stage/contracts.py).

Dataset-serving semantics currently live in `prml_vslam.sources.datasets.contracts`:

- [AdvioServingConfig](./contracts.py:75)
  - selected ADVIO pose provider
  - selected ADVIO pose-frame mode
- [AdvioPoseSource](./contracts.py:33)
  - `GROUND_TRUTH`, `ARCORE`, `ARKIT`
- [AdvioPoseFrameMode](./contracts.py:59)
  - `PROVIDER_WORLD`, `LOCAL_FIRST_POSE`

### Offline Boundary

Datasets normalize local source data into two pipeline-facing outputs:

- `SequenceManifest`
  - canonical offline source-preparation boundary
  - always carries `sequence_id`
  - may carry `dataset_id`, `dataset_serving`, `video_path` or `rgb_dir`,
    `timestamps_path`, `intrinsics_path`, `rotation_metadata_path`
  - for ADVIO, may also carry `advio: AdvioManifestAssets`
- `PreparedBenchmarkInputs`
  - canonical benchmark-side auxiliary inputs
  - may carry normalized `reference_trajectories`
  - for TUM RGB-D, may also carry `reference_clouds`
  - ADVIO does not prepare point-cloud references
  - TUM RGB-D reference clouds are registered-depth clouds fused through
    ground-truth RGB-camera poses from the same persisted observation index
    consumed by method input preparation (`tum_rgbd`)

The current ADVIO-specific manifest payload DTOs are:

- `AdvioManifestAssets`
  - parsed intrinsics
  - parsed `T_cam_imu`
  - optional selected/raw pose refs before normalized-store publication
  - optional fixpoints ref before normalized-store publication
- `AdvioRawPoseRefs`
  - GT, ARCore, ARKit, and selected provider pose paths when present

### Streaming Boundary

Datasets expose replay-capable runtime sources through:

- [DatasetSequenceSource](./sources.py:19)
  - shared adapter used by dataset services for process-backed replay sessions
- `Observation`
  - canonical source observation emitted by dataset replay
  - may carry `rgb`, `depth_m`, `confidence`, `pointmap_xyz`, `intrinsics`,
    `T_world_camera`, and typed provenance

The replay path is intentionally layered:

- `prml_vslam.sources.replay`
  - generic replay pacing, PyAV-backed video decoding, and image-sequence replay
  - shared observation stream mechanics
- dataset-specific replay adapters
  - ADVIO: timestamped provider-pose serving, frame-mode semantics, optional
    rotation handling
  - TUM RGB-D: RGB/depth/GT association and image-sequence replay

## Output DTOs

The most important dataset-owned DTOs and outputs are:

- `DatasetDownloadRequest`, [DatasetDownloadResult](./contracts.py:136)
  - explicit local download/extract selection and result summary
- [LocalSceneStatus](./contracts.py:146), [DatasetSummary](./contracts.py:157)
  - local completeness and catalog coverage summaries
- [AdvioOfflineSample](./advio/advio_sequence.py:116), [TumRgbdOfflineSample](./tum_rgbd/tum_rgbd_loading.py:25)
  - fully loaded local sample surfaces for app/tests
- [AdvioSequencePaths](./advio/advio_sequence.py:57), [TumRgbdSequencePaths](./tum_rgbd/tum_rgbd_sequence.py:22)
  - resolved local file layout for one sequence
- [AdvioCalibration](./advio/advio_loading.py:17)
  - parsed ADVIO intrinsics and `T_cam_imu`

## Main Entry Points

- [AdvioDatasetService](./advio/advio_service.py:66)
  - summarize the local dataset state
  - inspect scenes
  - download selected full scenes
  - resolve dataset sequence ids for pipeline execution
  - build normalized-store-backed sources for app and pipeline surfaces
- [AdvioSequence](./advio/advio_sequence.py:138)
  - load one offline sample
  - parse native observations for normalized-store ingestion
  - prepare one `SequenceManifest`
  - prepare one `PreparedBenchmarkInputs`
- [TumRgbdDatasetService](./tum_rgbd/tum_rgbd_service.py:14)
  - summarize local TUM RGB-D state
  - download selected TUM RGB-D archives
  - prepare RGB-directory sequence manifests and ground-truth TUM references
- [TumRgbdSequence](./tum_rgbd/tum_rgbd_sequence.py:52)
  - load one local sequence
  - parse native RGB-D observations for normalized-store ingestion
  - prepare one `SequenceManifest`
  - prepare one `PreparedBenchmarkInputs`

## Normalized Store Batch Builds

Dataset-backed sources share one canonical `NormalizedDatasetStore` under
`.data/vslam-datastore/<dataset>/<sequence>/<profile-key>/`. The store persists
source-selected replay payloads once, plus source-owned long-form Core/Motion
statistics and metadata tables. Runtime sampling options such as
`frame_stride` and `target_fps` remain read-time policy and do not create
stride-specific stored payloads.

Batch build TOML groups shared normalize-time settings by dataset and expands
`sequence_ids` into concrete per-sequence source configs before ingestion. The
checked-in benchmark datastore config therefore declares each dataset's common
RGB, frame-selection, and reference-cloud policy once instead of repeating it
for every scene.

Runtime readers first request the exact profile key. If that profile is missing,
they may reuse the only current-schema entry for the same dataset, sequence, and
source id with a warning. Multiple compatible profiles remain ambiguous and
must be resolved by rebuilding or selecting the exact profile.

When a run wants to read a lower cadence than the persisted entry, source
configs keep that read-time policy in `frame_stride` / `target_fps` and carry
the store-build cadence in `normalized_frame_stride` / `normalized_target_fps`.
This keeps benchmark sweeps on exact datastore profiles without making runtime
subsampling a rebuild trigger.

Each new entry writes two queryable CSV tables:

- `stats_long.csv`: one row per persisted sequence, observation-sequence, or
  trajectory statistic, including frame counts, duration, FPS, path length,
  speed, 3D tangent-angle change, curvature proxy, and coarse ego-motion class.
- `metadata_long.csv`: one row per profile, source, and artifact metadata fact
  that app and CLI surfaces can load without re-normalizing the dataset.

A normalized entry stores the common single RGB-D observation sequence directly
under `<entry>/observations/`. Multi-sequence normalized observation layouts are
rejected instead of persisted. Record3D depth maps remain benchmark observation
payloads rather than primary `SequenceManifest` input, but the matching RGB
frames are shared with the source manifest instead of duplicated under
`benchmark/observations/`.

ADVIO normalizes display-oriented replay frames into a PNG sequence under
`<entry>/observations/rgb/`. To avoid the old full-resolution PNG blow-up while
keeping the same file-backed contract as TUM RGB-D and Record3D, ADVIO defaults
to a method-neutral cache raster with maximum width 392 px and dimensions rounded
to multiples of 14; intrinsics are scaled to that stored raster.

ADVIO datastore entries publish RDF fixedpoint/common-start trajectories. Raw
ADVIO poses are first converted with the dataset adapter's
`(x, y, z) -> (z, -y, x)` basis. `NormalizedDatasetStore` then registers GT,
ARCore, and ARKit to ADVIO fixpoints before any local rebasing, crops accepted
providers to their shared time interval, and expresses them in the GT-derived
`advio_fixedpoint_common_start_local` frame. Accepted ARCore/ARKit registered
trajectories are both reference trajectories for baseline lookup and candidate
trajectories for benchmarking. Post-normalization `*_aligned_to_gt.tum` overlays
are diagnostic reference trajectories only and are never benchmark candidates.
Normalized ADVIO manifests keep calibration/intrinsics but set raw pose refs and
fixpoints to `None`; raw ADVIO pose/fixpoint CSV sidecars are invalid under a
normalized datastore entry. The ADVIO normalized profile convention is
`fixedpoint_common_start_local_rdf_v1`. The known legacy local-first-pose
convention and legacy `registered` coordinate status are accepted with a warning
for replay compatibility; missing conventions are treated as rebuild-required
instead of compatible defaults.

New entries use canonical roots only: source inputs under `<entry>/input/`,
reference/candidate trajectories under `<entry>/benchmark/trajectories/`, clouds
under `<entry>/benchmark/reference_clouds/`, and replay payloads under
`<entry>/observations/`. The store schema rejects stale non-canonical entries so
they are rebuilt instead of silently mixed with the current layout.

To build or refresh normalized entries, use the CLI normalization command. Omit
`--sequence` to normalize every offline-ready local sequence with one worker per
CPU by default, or repeat `--sequence` to bound the build:

```bash
prml-vslam dataset normalize --dataset record3d
prml-vslam dataset normalize --dataset record3d --sequence <sequence-id> --workers 4
prml-vslam dataset normalize --dataset record3d --target-fps 5
prml-vslam dataset normalize --dataset record3d --frame-stride 3
```

`--target-fps` and `--frame-stride` are normalize-time sampling controls. They
reduce the frames persisted to the normalized datastore and are therefore part of
the store profile when used. Runtime sampling in pipeline source configs remains
read-time only and does not request a different normalized entry.

The Streamlit Datasets page and `prml-vslam dataset summary` read persisted
entries, issues, and analysis tables; they do not normalize datasets during
display. Raw dataset explorers remain ingestion and inspection surfaces, while
pipeline-ready dataset serving consumes normalized-store artifacts.

## Typical Usage

Load one local sequence:

```python
from pathlib import Path

from prml_vslam.sources.datasets.advio import AdvioSequence, AdvioSequenceConfig

sequence = AdvioSequence(
    config=AdvioSequenceConfig(dataset_root=Path(".data/advio"), sequence_id=15)
)
sample = sequence.load_offline_sample()

print(sample.sequence_name)
print(sample.calibration.intrinsics)
print(sample.ground_truth.timestamps.shape)
```

Open a normalized replay stream:

```python
from prml_vslam.sources.config import AdvioSourceConfig
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.datasets.normalization import (
    normalized_profile_for_dataset,
    normalized_store_for_service,
)
from prml_vslam.sources.datasets.normalized_source import NormalizedDatasetRuntimeSource
from prml_vslam.sources.datasets.advio import AdvioDatasetService
from prml_vslam.utils import PathConfig

path_config = PathConfig()
service = AdvioDatasetService(path_config)
source_config = AdvioSourceConfig(sequence_id="advio-15")
sequence_id = service.resolve_sequence_id(source_config.sequence_id)
source = NormalizedDatasetRuntimeSource(
    label=service.scene(sequence_id).display_name,
    store=normalized_store_for_service(DatasetId.ADVIO, path_config),
    profile=normalized_profile_for_dataset(
        dataset_id=DatasetId.ADVIO,
        service=service,
        source_config=source_config,
    ),
    frame_selection=source_config,
    replay_mode=source_config.replay_mode,
)
stream = source.open_stream(loop=False)

stream.connect()
observation = stream.wait_for_observation()
stream.disconnect()
```

Use the high-level dataset service:

```python
from prml_vslam.sources.datasets.advio import AdvioDatasetService
from prml_vslam.utils import PathConfig

service = AdvioDatasetService(PathConfig())
summary = service.summarize()
statuses = service.local_scene_statuses()
```

## Boundaries

- This package owns dataset normalization and replay preparation, not evaluation policy.
- Simplification in this package must not reintroduce partial modality downloads or drop TUM RGB-D reference-cloud preparation.
- App and pipeline dataset replay must come from `.data/vslam-datastore/<dataset>/`; native dataset readers are parser/ingestion internals.
- Generic replay mechanics stay in `prml_vslam.sources.replay`.
- App pages and pipeline surfaces should prefer `AdvioDatasetService`, `TumRgbdDatasetService`, or the
  corresponding normalized store helpers over rebuilding dataset path, manifest,
  or replay logic directly.
