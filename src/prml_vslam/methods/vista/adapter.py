"""Canonical ViSTA-SLAM backend adapter for offline and streaming execution.

This module contains the primary bridge from the repository's method contract
into the upstream ViSTA runtime. It keeps the top-level adapter thin and
delegates preprocessing, session management, and artifact normalization to the
rest of the :mod:`prml_vslam.methods.vista` package.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2

from prml_vslam.benchmark import PreparedBenchmarkInputs, ReferenceSource
from prml_vslam.interfaces import FramePacket
from prml_vslam.methods.config_contracts import MethodId, SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.configs import VistaSlamBackendConfig
from prml_vslam.methods.protocols import SlamBackend, SlamSession
from prml_vslam.methods.session_init import SlamSessionInit
from prml_vslam.pipeline.contracts.artifacts import SlamArtifacts
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.utils import Console, PathConfig

from .session import create_vista_session


class VistaSlamBackend(SlamBackend):
    """Adapt the upstream ViSTA runtime to the repository's method contract."""

    method_id: MethodId = MethodId.VISTA

    def __init__(
        self,
        config: VistaSlamBackendConfig,
        path_config: PathConfig | None = None,
    ) -> None:
        self._cfg = config
        self._path_config = path_config or PathConfig()
        self._console = Console(__name__).child(self.__class__.__name__)

    def start_session(
        self,
        session_init: SlamSessionInit,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamSession:
        """Load upstream OnlineSLAM and return a ready in-process session."""
        del session_init, backend_config
        return create_vista_session(
            config=self._cfg,
            path_config=self._path_config,
            console=self._console,
            output_policy=output_policy,
            artifact_root=artifact_root,
            live_mode=True,
        )

    def run_sequence(
        self,
        sequence: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamArtifacts:
        """Run ViSTA-SLAM over a normalized offline manifest and persist artifacts."""
        del benchmark_inputs, baseline_source
        image_paths, timestamps_ns = _load_offline_frame_inputs(
            sequence=sequence,
            max_frames=backend_config.max_frames,
        )
        session = create_vista_session(
            config=self._cfg,
            path_config=self._path_config,
            console=self._console,
            artifact_root=artifact_root,
            output_policy=output_policy,
            live_mode=False,
        )
        self._console.info("Running ViSTA-SLAM on %d frames …", len(image_paths))
        for seq, (image_path, timestamp_ns) in enumerate(zip(image_paths, timestamps_ns, strict=True)):
            bgr = cv2.imread(str(image_path))
            if bgr is None:
                raise RuntimeError(f"Failed to read input frame '{image_path}'.")
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            session.step(FramePacket(seq=seq, timestamp_ns=timestamp_ns, rgb=rgb))
        return session.close()


def _load_offline_frame_inputs(
    *,
    sequence: SequenceManifest,
    max_frames: int | None,
) -> tuple[list[Path], list[int]]:
    """Load normalized offline RGB paths plus timestamps for ViSTA execution."""
    if sequence.rgb_dir is None or not sequence.rgb_dir.exists():
        raise RuntimeError(
            "ViSTA offline execution requires a normalized `SequenceManifest.rgb_dir`. "
            "Materialize the offline manifest through pipeline ingest before invoking the backend."
        )
    if sequence.timestamps_path is None or not sequence.timestamps_path.exists():
        raise RuntimeError(
            "ViSTA offline execution requires a normalized `SequenceManifest.timestamps_path`. "
            "Materialize the offline manifest through pipeline ingest before invoking the backend."
        )
    image_paths = sorted(sequence.rgb_dir.glob("*.png"))
    if not image_paths:
        raise RuntimeError(f"Normalized ViSTA input directory '{sequence.rgb_dir}' does not contain any PNG frames.")
    payload = json.loads(sequence.timestamps_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("timestamps_ns"), list):
        raise RuntimeError(
            "Expected normalized ViSTA timestamps JSON with a `timestamps_ns` list at "
            f"'{sequence.timestamps_path}', got: {type(payload).__name__}."
        )
    timestamps_ns = [int(timestamp_ns) for timestamp_ns in payload["timestamps_ns"]]
    if max_frames is not None:
        image_paths = image_paths[:max_frames]
        timestamps_ns = timestamps_ns[:max_frames]
    if len(timestamps_ns) != len(image_paths):
        raise RuntimeError(
            "Normalized ViSTA offline inputs are inconsistent: "
            f"{len(image_paths)} PNG frames in '{sequence.rgb_dir}' but {len(timestamps_ns)} timestamps in "
            f"'{sequence.timestamps_path}'."
        )
    return image_paths, timestamps_ns


__all__ = ["VistaSlamBackend"]
