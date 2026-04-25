"""Canonical ViSTA-SLAM backend adapter (offline + streaming)."""

from __future__ import annotations

import json
from pathlib import Path

import cv2

from prml_vslam.interfaces import Observation, ObservationProvenance
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.methods.contracts import SlamUpdate
from prml_vslam.methods.protocols import SlamBackend
from prml_vslam.methods.stage.config import MethodId, SlamBackendConfig, SlamOutputPolicy, VistaSlamBackendConfig
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, ReferenceSource, SequenceManifest
from prml_vslam.utils import Console, PathConfig

from .session import VistaSlamRuntime, create_vista_runtime


class VistaSlamBackend(SlamBackend):
    """ViSTA-SLAM backend implementing offline and streaming contracts."""

    method_id: MethodId = MethodId.VISTA

    def __init__(
        self,
        config: VistaSlamBackendConfig,
        path_config: PathConfig | None = None,
    ) -> None:
        self._cfg = config
        self._path_config = path_config or PathConfig()
        self._console = Console(__name__).child(self.__class__.__name__)
        self._streaming_runtime: VistaSlamRuntime | None = None

    def start_streaming(
        self,
        sequence_manifest: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> None:
        """Load upstream OnlineSLAM and retain backend-owned streaming state."""
        del sequence_manifest, benchmark_inputs, baseline_source, backend_config
        self._streaming_runtime = create_vista_runtime(
            config=self._cfg,
            path_config=self._path_config,
            console=self._console,
            output_policy=output_policy,
            artifact_root=artifact_root,
            live_mode=True,
        )

    def step_streaming(self, frame: Observation) -> None:
        """Consume one streaming frame through the active ViSTA runtime."""
        self._require_streaming_runtime().step(frame)

    def drain_streaming_updates(self) -> list[SlamUpdate]:
        """Retrieve pending ViSTA live updates without exposing runtime state."""
        return self._require_streaming_runtime().drain_updates()

    def finish_streaming(self) -> SlamArtifacts:
        """Finalize the active ViSTA streaming runtime and clear it."""
        runtime = self._require_streaming_runtime()
        artifacts = runtime.finish()
        self._streaming_runtime = None
        return artifacts

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
        runtime = create_vista_runtime(
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
            runtime.step(
                Observation(
                    seq=seq,
                    timestamp_ns=timestamp_ns,
                    rgb=rgb,
                    provenance=ObservationProvenance(source_id="vista_offline"),
                )
            )
        return runtime.finish()

    def _require_streaming_runtime(self) -> VistaSlamRuntime:
        if self._streaming_runtime is None:
            raise RuntimeError("ViSTA-SLAM streaming backend has not been started.")
        return self._streaming_runtime


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
