"""Repo-wide RGB-D observation source seam.

This protocol lets reconstruction backends consume normalized posed RGB-D
observations without knowing whether the payloads came from a dataset, a SLAM
backend, or a prepared run artifact.
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from prml_vslam.interfaces import RgbdObservation


@runtime_checkable
class RgbdObservationSource(Protocol):
    """Yield normalized posed RGB-D observations for reconstruction consumers.

    Implementations own file or stream access. Consumers can rely on each
    yielded :class:`prml_vslam.interfaces.rgbd.RgbdObservation` having coherent
    RGB/depth/intrinsics raster semantics and a canonical ``T_world_camera``
    pose.
    """

    label: str

    @abstractmethod
    def iter_observations(self) -> Iterator[RgbdObservation]:
        """Return a one-pass iterator over normalized RGB-D observations."""


__all__ = ["RgbdObservationSource"]
