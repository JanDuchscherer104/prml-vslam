# Datasets

This README is the implementation guide for the current dataset package in `prml_vslam.datasets`.

Use [../REQUIREMENTS.md](../REQUIREMENTS.md) for top-level ownership rules. Use this file for the current code surfaces and typical usage patterns.

## Current Implementation

This package owns repository-local dataset adapters and dataset-facing contracts. The implemented targets are ADVIO
and TUM RGB-D.

Current simplification work must preserve the full supported dataset surface. In particular:

- all currently supported modalities remain in scope
- ADVIO Tango poses and Tango point-cloud payload support remain in scope
- dataset-provided reference cloud preparation remains in scope
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

- `prml_vslam.io.cv2_producer` owns generic video replay and pacing
- `advio_replay_adapter.py` adds ADVIO-specific timestamps, calibration, poses, and optional video-rotation handling
- `advio_sequence.py` exposes the sequence-level entry points used by the app and tests

The TUM RGB-D stack mirrors the same service shape where practical:

- typed metadata plus dataset-contract specializations in `tum_rgbd/tum_rgbd_models.py`
- ViSTA-compatible scene catalog and local path resolution in `tum_rgbd/tum_rgbd_layout.py`
- TUM timestamp-list parsing, RGB/depth/pose association, and Freiburg intrinsics in
  `tum_rgbd/tum_rgbd_loading.py`
- TGZ download/extraction flows in `tum_rgbd/tum_rgbd_download.py`
- sequence manifest and benchmark input preparation in `tum_rgbd/tum_rgbd_sequence.py`
- image-sequence loop preview in `tum_rgbd/tum_rgbd_replay_adapter.py`

Package-local guides:

- [ADVIO guide](./advio/README.md)
- [TUM RGB-D guide](./tum_rgbd/README.md)

## Stage Boundaries

The dataset layer feeds the current pipeline/app/runtime stack through a small
set of typed boundaries. Those boundaries are the current source of truth for
what downstream code is allowed to rely on.

### Request Boundary

Upstream of the dataset package, pipeline requests use:

- [DatasetSourceSpec](../pipeline/contracts/request.py:57)
  - selects `dataset_id` and `sequence_id`
  - carries shared frame sampling via [FrameSelectionConfig](./contracts.py:115)
  - for ADVIO, may also carry `dataset_serving`

Dataset-serving semantics currently live in `prml_vslam.datasets.contracts`:

- [AdvioServingConfig](./contracts.py:75)
  - selected ADVIO pose provider
  - selected ADVIO pose-frame mode
- [AdvioPoseSource](./contracts.py:33)
  - `GROUND_TRUTH`, `ARCORE`, `ARKIT`, `TANGO_RAW`, `TANGO_AREA_LEARNING`
- [AdvioPoseFrameMode](./contracts.py:59)
  - `PROVIDER_WORLD`, `REFERENCE_WORLD`, `LOCAL_FIRST_POSE`

### Offline Boundary

Datasets normalize local source data into two pipeline-facing outputs:

- [SequenceManifest](../pipeline/contracts/sequence.py:11)
  - canonical offline ingest boundary
  - always carries `sequence_id`
  - may carry `dataset_id`, `dataset_serving`, `video_path` or `rgb_dir`,
    `timestamps_path`, `intrinsics_path`, `rotation_metadata_path`
  - for ADVIO, may also carry `advio: AdvioManifestAssets`
- [PreparedBenchmarkInputs](../benchmark/contracts.py:98)
  - canonical benchmark-side auxiliary inputs
  - may carry normalized `reference_trajectories`
  - for ADVIO, may also carry `reference_clouds` and
    `reference_point_cloud_sequences`

The current ADVIO-specific manifest payload DTOs are:

- [AdvioManifestAssets](./contracts.py:103)
  - parsed intrinsics
  - parsed `T_cam_imu`
  - selected/raw pose refs
  - fixpoints ref
  - Tango point-cloud index/payload-root refs
- [AdvioRawPoseRefs](./contracts.py:92)
  - GT, ARCore, ARKit, Tango raw, Tango area-learning, and selected provider
    pose paths when present

### Streaming Boundary

Datasets expose replay-capable runtime sources through:

- [DatasetSequenceSource](./sources.py:19)
  - shared adapter used by dataset services for process-backed replay sessions
- [FramePacket](../interfaces/runtime.py:68)
  - canonical runtime packet emitted by dataset replay
  - may carry `rgb`, `depth`, `confidence`, `pointmap`, `intrinsics`, `pose`,
    and typed provenance

The replay path is intentionally layered:

- `prml_vslam.io.cv2_producer`
  - generic OpenCV-backed video replay and pacing
  - shared optional payload injection (`depth`, `confidence`, `pointmap`)
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
  - download selected modalities
  - resolve dataset sequence ids for pipeline execution
  - prepare normalized sequence manifests and benchmark inputs
  - open a replay stream for the app or pipeline surfaces
- [AdvioSequence](./advio/advio_sequence.py:138)
  - load one offline sample
  - open one replay stream
  - prepare one `SequenceManifest`
  - prepare one `PreparedBenchmarkInputs`
- [TumRgbdDatasetService](./tum_rgbd/tum_rgbd_service.py:14)
  - summarize local TUM RGB-D state
  - download selected TUM RGB-D archives
  - prepare RGB-directory sequence manifests and ground-truth TUM references
- [TumRgbdSequence](./tum_rgbd/tum_rgbd_sequence.py:52)
  - load one local sequence
  - open one RGB-D image-sequence replay stream
  - prepare one `SequenceManifest`
  - prepare one `PreparedBenchmarkInputs`

## Typical Usage

Load one local sequence:

```python
from pathlib import Path

from prml_vslam.datasets.advio import AdvioSequence, AdvioSequenceConfig

sequence = AdvioSequence(
    config=AdvioSequenceConfig(dataset_root=Path(".data/advio"), sequence_id=15)
)
sample = sequence.load_offline_sample()

print(sample.sequence_name)
print(sample.calibration.intrinsics)
print(sample.ground_truth.timestamps.shape)
```

Open a replay stream:

```python
from pathlib import Path

from prml_vslam.datasets.advio import (
    AdvioPoseFrameMode,
    AdvioPoseSource,
    AdvioSequence,
    AdvioSequenceConfig,
    AdvioServingConfig,
)
from prml_vslam.io import Cv2ReplayMode

sequence = AdvioSequence(
    config=AdvioSequenceConfig(dataset_root=Path(".data/advio"), sequence_id=15)
)
stream = sequence.open_stream(
    dataset_serving=AdvioServingConfig(
        pose_source=AdvioPoseSource.GROUND_TRUTH,
        pose_frame_mode=AdvioPoseFrameMode.REFERENCE_WORLD,
    ),
    replay_mode=Cv2ReplayMode.REALTIME,
    respect_video_rotation=True,
)

stream.connect()
packet = stream.wait_for_packet()
stream.disconnect()
```

Use the high-level dataset service:

```python
from prml_vslam.datasets.advio import AdvioDatasetService
from prml_vslam.utils import PathConfig

service = AdvioDatasetService(PathConfig())
summary = service.summarize()
statuses = service.local_scene_statuses()
```

## Boundaries

- This package owns dataset normalization and replay preparation, not evaluation policy.
- Simplification in this package must not drop supported modalities, ADVIO Tango support, or repo-owned reference-cloud preparation.
- Generic replay mechanics stay in `prml_vslam.io`.
- App pages and pipeline surfaces should prefer `AdvioDatasetService`, `TumRgbdDatasetService`, or the
  corresponding sequence classes over rebuilding dataset path, manifest, or
  replay logic directly.
