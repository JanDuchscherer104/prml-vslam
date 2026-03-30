"""Mock ViSTA-SLAM backend for development and testing.

Produces a synthetic circular trajectory to exercise the pipeline
without requiring the real ViSTA-SLAM installation.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from pytransform3d import rotations as pr
from pytransform3d import transformations as pt

from prml_vslam.pipeline.methods.base import ArtifactAccumulator, SlamOutput


class MockVistaBackend:
    """Deterministic mock that generates a circular trajectory.

    Satisfies the :class:`SlamBackend` protocol.
    """

    def __init__(self, *, radius: float = 2.0, angular_speed: float = 0.1) -> None:
        self.radius = radius
        self.angular_speed = angular_speed
        self._acc = ArtifactAccumulator()

    def step(self, frame_index: int, ts_ns: int = 0) -> SlamOutput:
        r = self.radius
        theta = frame_index * self.angular_speed
        ts_s = ts_ns / 1e9

        # Circular path in XZ plane, camera looking inward
        position = np.array([r * np.cos(theta), 0.0, r * np.sin(theta)])
        rotation = pr.active_matrix_from_angle(1, -theta)  # rotate around Y axis
        pose = pt.transform_from(rotation, position)

        self._acc.record(pose, ts_s)

        preview = list(self._acc.trajectory) if frame_index % 10 == 0 else None
        return SlamOutput(
            pose=pose,
            timestamp_s=ts_s,
            is_keyframe=(frame_index % 5 == 0),
            preview_trajectory=preview,
        )

    def export_artifacts(self, artifact_root: Path) -> None:
        self._acc.export(artifact_root)
