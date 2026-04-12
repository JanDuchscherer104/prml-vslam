# Datasets

This README is the implementation guide for the current dataset package in `prml_vslam.datasets`.

Use [../REQUIREMENTS.md](../REQUIREMENTS.md) for top-level ownership rules. Use this file for the current code surfaces and typical usage patterns.

## Current Implementation

This package owns repository-local dataset adapters and dataset-facing contracts. The main implemented target today is ADVIO.

The current ADVIO stack includes:

- typed dataset metadata and status models in `advio_models.py`
- local path resolution and catalog lookups in `advio_layout.py` and `advio_sequence.py`
- typed file loading for timestamps, calibration, and trajectories in `advio_loading.py`
- dataset fetch and cache mechanics in `fetch.py` plus archive extraction flows in `advio_download.py`
- a high-level app- and pipeline-facing service in `advio_service.py`
- ADVIO replay stream assembly in `advio_replay_adapter.py`
- offline benchmark-input preparation, including typed reference trajectories, in `advio_sequence.py` and
  `advio_service.py`
- explicit frame-graph helpers in `frame_graph.py`

The replay path is layered on purpose:

- `prml_vslam.io.cv2_producer` owns generic video replay and pacing
- `advio_replay_adapter.py` adds ADVIO-specific timestamps, calibration, poses, and optional video-rotation handling
- `advio_sequence.py` exposes the sequence-level entry points used by the app and tests

## Main Entry Points

- `AdvioDatasetService`
  - summarize the local dataset state
  - inspect scenes
  - download selected modalities
  - resolve dataset sequence ids for pipeline execution
  - prepare normalized sequence manifests and benchmark inputs
  - open a replay stream for the app or pipeline surfaces
- `AdvioSequence`
  - load one offline sample
  - open one replay stream
  - export ground-truth and baseline trajectories to TUM
- `load_advio_sequence(...)`
  - convenience entry point for one fully loaded local sample

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

from prml_vslam.datasets.advio import AdvioPoseSource, AdvioSequence, AdvioSequenceConfig
from prml_vslam.io import Cv2ReplayMode

sequence = AdvioSequence(
    config=AdvioSequenceConfig(dataset_root=Path(".data/advio"), sequence_id=15)
)
stream = sequence.open_stream(
    pose_source=AdvioPoseSource.GROUND_TRUTH,
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
- Generic replay mechanics stay in `prml_vslam.io`.
- App pages and pipeline surfaces should prefer `AdvioDatasetService` or `AdvioSequence` over rebuilding ADVIO path or replay logic directly.
