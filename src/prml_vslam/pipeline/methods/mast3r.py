"""Mock MASt3R-SLAM backend for development and testing.

Produces a synthetic forward-walking trajectory and incremental dense
map updates to exercise the pipeline without requiring the real
MASt3R-SLAM installation.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from pytransform3d import transformations as pt

from prml_vslam.pipeline.methods.base import ArtifactAccumulator, SlamOutput


class MockMast3rBackend:
    """Deterministic mock that generates a forward trajectory with dense updates.

    Satisfies the :class:`SlamBackend` protocol.
    """

    def __init__(self, *, step_size: float = 0.05, dense_update_interval: int = 5) -> None:
        self.step_size = step_size
        self.dense_update_interval = dense_update_interval
        self._acc = ArtifactAccumulator()

    def step(self, frame_index: int, ts_ns: int = 0) -> SlamOutput:
        ts_s = ts_ns / 1e9
        tz = frame_index * self.step_size

        pose = pt.transform_from(np.eye(3), np.array([0.0, 0.0, tz]))
        self._acc.record(pose, ts_s)

        map_points = (
            np.array([[0.0, 0.0, tz]]) if (frame_index > 0 and frame_index % self.dense_update_interval == 0) else None
        )
        preview = list(self._acc.trajectory) if frame_index % 10 == 0 else None

        return SlamOutput(
            pose=pose,
            timestamp_s=ts_s,
            is_keyframe=(frame_index % 3 == 0),
            map_points=map_points,
            num_map_points=len(self._acc.trajectory) * 10,
            preview_trajectory=preview,
        )

    def export_artifacts(self, artifact_root: Path) -> None:
        self._acc.export(artifact_root)
