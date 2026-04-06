# Datasets

This package owns repository-local dataset adapters and dataset-facing contracts.
Right now the main implementation target is ADVIO.

## What It Implements

- typed dataset metadata and status models in `advio_models.py`
- local path resolution and catalog lookups in `advio_layout.py` and `advio_sequence.py`
- typed file loading for timestamps, calibration, and trajectories in `advio_loading.py`
- dataset fetch/cache mechanics in `fetch.py` and archive extraction flows in `advio_download.py`
- a high-level app- and pipeline-facing service in `advio_service.py`
- ADVIO replay stream assembly in `advio_replay_adapter.py`

The replay path is layered on purpose:

- `prml_vslam.io.cv2_producer` owns generic video replay and pacing
- `advio_replay_adapter.py` adds ADVIO-specific timestamps, calibration, poses, and optional video-rotation handling
- `advio_sequence.py` exposes the sequence-level entrypoints used by the app and tests

## Main Entry Points

- `AdvioDatasetService`
  - summarize the local dataset state
  - inspect scenes
  - download selected modalities
  - open a replay stream for the app
- `AdvioSequence`
  - load one offline sample
  - open one replay stream
  - export ground-truth and baseline trajectories to TUM
- `load_advio_sequence(...)`
  - convenience entrypoint for one fully loaded local sample

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
print(sample.ground_truth.timestamps_s.shape)
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

## Notes

- This package owns dataset normalization and replay preparation, not evaluation policy.
- Generic replay mechanics stay in `prml_vslam.io`.
- App pages should prefer `AdvioDatasetService` over rebuilding ADVIO path or replay logic directly.
