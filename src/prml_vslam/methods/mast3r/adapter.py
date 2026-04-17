"""MASt3R-SLAM backend adapter (stub — implementation pending)."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.methods.contracts import MethodId
from prml_vslam.methods.protocols import SlamBackend
from prml_vslam.utils import Console, PathConfig

from .config import Mast3rSlamBackendConfig


class Mast3rSlamBackend(SlamBackend):
    """MASt3R-SLAM backend — stub. Full adapter implementation is pending."""

    method_id: MethodId = MethodId.MAST3R

    def __init__(
        self,
        config: Mast3rSlamBackendConfig,
        path_config: PathConfig | None = None,
    ) -> None:
        self._cfg = config
        self._path_config = path_config or PathConfig()
        self._console = Console(__name__).child(self.__class__.__name__)

    def run_sequence(self, *args, **kwargs):
        raise NotImplementedError(
            "MASt3R-SLAM offline run is not implemented yet — adapter stub only."
        )

    def start_session(self, *args, **kwargs):
        raise NotImplementedError(
            "MASt3R-SLAM streaming session is not implemented yet — adapter stub only."
        )


__all__ = ["Mast3rSlamBackend"]