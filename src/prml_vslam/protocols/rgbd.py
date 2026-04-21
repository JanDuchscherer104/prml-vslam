"""Repo-wide RGB-D observation source seam."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from prml_vslam.interfaces import RgbdObservation


@runtime_checkable
class RgbdObservationSource(Protocol):
    """Yield normalized posed RGB-D observations for reconstruction consumers."""

    label: str

    @abstractmethod
    def iter_observations(self) -> Iterator[RgbdObservation]:
        """Return a one-pass iterator over normalized RGB-D observations."""


__all__ = ["RgbdObservationSource"]
