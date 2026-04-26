"""Source replay behavior seams."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Protocol

from prml_vslam.interfaces import Observation


class ObservationStream(Protocol):
    """Blockingly deliver shared :class:`Observation` values."""

    @abstractmethod
    def connect(self) -> Any:
        """Connect to the source and prepare subsequent blocking observation reads."""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect or release the source and any owned runtime resources."""

    @abstractmethod
    def wait_for_observation(self, timeout_seconds: float | None = None) -> Observation:
        """Wait for and return the next normalized source observation."""


__all__ = ["ObservationStream"]
