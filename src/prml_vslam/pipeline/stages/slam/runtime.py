"""SLAM stage runtime implementing the target runtime protocols.

`SlamStageRuntime` is the pipeline-facing adapter around method-owned SLAM
backends. It preserves the current backend/session behavior while emitting
target `StageResult`, `StageRuntimeStatus`, and `StageRuntimeUpdate` values.
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from prml_vslam.interfaces.ingest import SequenceManifest
from prml_vslam.interfaces.slam import SlamArtifacts, SlamUpdate
from prml_vslam.interfaces.visualization import VisualizationArtifacts
from prml_vslam.methods.factory import BackendFactory, BackendFactoryProtocol
from prml_vslam.methods.protocols import OfflineSlamBackend, SlamSession, StreamingSlamBackend
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.pipeline.ray_runtime.common import (
    backend_config_payload,
    slam_artifacts_map,
    visualization_artifact_map,
)
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus, StageRuntimeUpdate
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.pipeline.stages.slam.contracts import SlamFrameInput, SlamOfflineInput, SlamStreamingStartInput
from prml_vslam.pipeline.stages.slam.visualization import (
    DEPTH_REF,
    IMAGE_REF,
    POINTMAP_REF,
    PREVIEW_REF,
    SlamVisualizationAdapter,
)
from prml_vslam.utils import Console, RunArtifactPaths
from prml_vslam.visualization.rerun import collect_native_visualization_artifacts

_FPS_WINDOW = 20


@dataclass(frozen=True, slots=True)
class LegacySlamUpdate:
    """Compatibility payload for old backend event and handle routing."""

    update: SlamUpdate
    payloads: dict[str, np.ndarray]


class _TransientPayloadStore:
    """In-memory run-scoped payload store for live SLAM observer payloads."""

    def __init__(self) -> None:
        self._payloads: dict[str, np.ndarray] = {}

    def put(
        self,
        payload: np.ndarray | None,
        *,
        payload_kind: str,
        media_type: str,
        metadata: dict[str, str | int | float | bool | None] | None = None,
    ) -> TransientPayloadRef | None:
        """Store one optional array and return transport-safe metadata."""
        if payload is None:
            return None
        array = np.asarray(payload)
        handle_id = uuid.uuid4().hex
        self._payloads[handle_id] = array
        return TransientPayloadRef(
            handle_id=handle_id,
            payload_kind=payload_kind,
            media_type=media_type,
            shape=tuple(int(dim) for dim in array.shape),
            dtype=str(array.dtype),
            size_bytes=int(array.nbytes),
            metadata={} if metadata is None else metadata,
        )

    def read(self, ref: TransientPayloadRef) -> np.ndarray | None:
        """Return a stored payload by transient ref, if still retained."""
        payload = self._payloads.get(ref.handle_id)
        return None if payload is None else np.asarray(payload)


class SlamStageRuntime:
    """Pipeline-facing runtime for offline and streaming SLAM execution."""

    def __init__(
        self,
        *,
        backend_factory: BackendFactoryProtocol | None = None,
        visualization_adapter: SlamVisualizationAdapter | None = None,
    ) -> None:
        self._backend_factory = BackendFactory() if backend_factory is None else backend_factory
        self._visualization_adapter = (
            SlamVisualizationAdapter() if visualization_adapter is None else visualization_adapter
        )
        self._console = Console(__name__).child(self.__class__.__name__)
        self._payload_store = _TransientPayloadStore()
        self._session: SlamSession | None = None
        self._streaming_input: SlamStreamingStartInput | None = None
        self._pending_updates: list[StageRuntimeUpdate] = []
        self._legacy_updates: list[LegacySlamUpdate] = []
        self._last_visualization_artifacts: VisualizationArtifacts | None = None
        self._lifecycle_state = StageStatus.QUEUED
        self._processed_frames = 0
        self._accepted_keyframes = 0
        self._failed_frames = 0
        self._last_warning: str | None = None
        self._last_error: str | None = None
        self._frame_timestamps = deque(maxlen=_FPS_WINDOW)
        self._stopped = False

    def status(self) -> StageRuntimeStatus:
        """Return the latest queryable SLAM runtime status."""
        return StageRuntimeStatus(
            stage_key=StageKey.SLAM,
            lifecycle_state=self._lifecycle_state,
            progress_message=self._progress_message(),
            completed_steps=self._processed_frames,
            progress_unit="frames",
            failed_count=self._failed_frames,
            processed_items=self._processed_frames,
            fps=_rolling_fps(self._frame_timestamps),
            last_warning=self._last_warning,
            last_error=self._last_error,
            updated_at_ns=time.time_ns(),
        )

    def stop(self) -> None:
        """Request streaming runtime stop."""
        self._stopped = True
        if self._lifecycle_state is StageStatus.RUNNING:
            self._lifecycle_state = StageStatus.STOPPED

    def run_offline(self, input_payload: SlamOfflineInput) -> StageResult:
        """Run the selected backend over one bounded normalized sequence."""
        self._lifecycle_state = StageStatus.RUNNING
        try:
            backend = self._backend_factory.build(
                input_payload.request.slam.backend, path_config=input_payload.path_config
            )
            if not isinstance(backend, OfflineSlamBackend):
                raise RuntimeError(
                    f"Backend '{input_payload.request.slam.backend.method_id.value}' does not support offline execution."
                )
            slam = backend.run_sequence(
                input_payload.sequence_manifest,
                input_payload.benchmark_inputs,
                input_payload.request.benchmark.trajectory.baseline_source,
                backend_config=backend_config_payload(input_payload.request),
                output_policy=input_payload.request.slam.outputs,
                artifact_root=input_payload.plan.artifact_root,
            )
            result = self._stage_result(
                request=input_payload.request,
                artifact_root=input_payload.plan.artifact_root,
                sequence_manifest=input_payload.sequence_manifest,
                slam=slam,
                status=StageStatus.COMPLETED,
            )
            self._lifecycle_state = StageStatus.COMPLETED
            return result
        except Exception as exc:
            self._last_error = str(exc)
            self._lifecycle_state = StageStatus.FAILED
            raise

    def start_streaming(self, input_payload: SlamStreamingStartInput) -> None:
        """Start one incremental SLAM backend session."""
        backend = self._backend_factory.build(input_payload.request.slam.backend, path_config=input_payload.path_config)
        if not isinstance(backend, StreamingSlamBackend):
            raise RuntimeError(
                f"Backend '{input_payload.request.slam.backend.method_id.value}' does not support streaming execution."
            )
        self._session = backend.start_session(
            session_init=input_payload.session_init,
            backend_config=backend_config_payload(input_payload.request),
            output_policy=input_payload.request.slam.outputs,
            artifact_root=input_payload.plan.artifact_root,
        )
        self._streaming_input = input_payload
        self._lifecycle_state = StageStatus.RUNNING
        self._stopped = False

    def submit_stream_item(self, item: SlamFrameInput) -> None:
        """Submit one frame to the active streaming backend session."""
        if self._session is None:
            raise RuntimeError("SLAM streaming runtime has not been started.")
        if self._stopped:
            return
        try:
            self._session.step(item.frame)
            self._processed_frames += 1
            self._frame_timestamps.append(time.monotonic())
            self._drain_backend_updates()
        except Exception as exc:
            self._failed_frames += 1
            self._last_error = str(exc)
            self._lifecycle_state = StageStatus.FAILED
            raise

    def drain_runtime_updates(self, max_items: int | None = None) -> list[StageRuntimeUpdate]:
        """Return pending live SLAM updates without blocking."""
        if max_items is None:
            updates = self._pending_updates
            self._pending_updates = []
            return updates
        updates = self._pending_updates[:max_items]
        self._pending_updates = self._pending_updates[max_items:]
        return updates

    def drain_legacy_updates(self) -> list[LegacySlamUpdate]:
        """Return compatibility updates for old backend-notice routing."""
        # TODO(pipeline-refactor/WP-10): Delete after BackendNoticeReceived and
        # ArrayHandle/PreviewHandle routing are removed from the streaming path.
        updates = self._legacy_updates
        self._legacy_updates = []
        return updates

    def read_payload(self, ref: TransientPayloadRef) -> np.ndarray | None:
        """Resolve one runtime-owned live payload by transient reference."""
        return self._payload_store.read(ref)

    @property
    def last_visualization_artifacts(self) -> VisualizationArtifacts | None:
        """Return visualization artifacts collected by the last terminal run."""
        return self._last_visualization_artifacts

    @property
    def session_for_migration(self) -> SlamSession | None:
        """Return the active method session for legacy actor compatibility."""
        # TODO(pipeline-refactor/WP-10): Remove after streaming tests and
        # compatibility actors no longer inspect method session state directly.
        return self._session

    def finish_streaming(self) -> StageResult:
        """Finalize streaming SLAM and return terminal artifacts."""
        if self._session is None or self._streaming_input is None:
            raise RuntimeError("SLAM streaming runtime has not been started.")
        self._lifecycle_state = StageStatus.RUNNING
        try:
            slam = self._session.close()
            result = self._stage_result(
                request=self._streaming_input.request,
                artifact_root=self._streaming_input.plan.artifact_root,
                sequence_manifest=self._streaming_input.session_init.sequence_manifest,
                slam=slam,
                status=StageStatus.COMPLETED if not self._stopped else StageStatus.STOPPED,
            )
            self._lifecycle_state = result.outcome.status
            return result
        except Exception as exc:
            self._last_error = str(exc)
            self._lifecycle_state = StageStatus.FAILED
            raise

    def _drain_backend_updates(self) -> None:
        if self._session is None:
            return
        for update in self._session.try_get_updates():
            if update.is_keyframe:
                self._accepted_keyframes += 1
            if update.backend_warnings:
                self._last_warning = update.backend_warnings[-1]
            payload_refs = self._payload_refs_for(update)
            visualizations = self._visualization_adapter.build_items(update, payload_refs)
            runtime_update = StageRuntimeUpdate(
                stage_key=StageKey.SLAM,
                timestamp_ns=time.time_ns(),
                semantic_events=[_semantic_update(update)],
                visualizations=visualizations,
                runtime_status=self.status(),
            )
            self._pending_updates.append(runtime_update)
            self._legacy_updates.append(
                LegacySlamUpdate(
                    update=update,
                    payloads={ref_name: np.asarray(payload) for ref_name, payload in _payload_arrays(update).items()},
                )
            )

    def _payload_refs_for(self, update: SlamUpdate) -> dict[str, TransientPayloadRef]:
        refs: dict[str, TransientPayloadRef] = {}
        for name, payload, payload_kind, media_type in (
            (IMAGE_REF, update.image_rgb, "image", "image/rgb"),
            (DEPTH_REF, update.depth_map, "depth", "application/vnd.prml.depth+numpy"),
            (PREVIEW_REF, update.preview_rgb, "image", "image/rgb"),
            (POINTMAP_REF, update.pointmap, "point_cloud", "application/vnd.prml.pointmap+numpy"),
        ):
            ref = self._payload_store.put(
                None if payload is None else np.asarray(payload),
                payload_kind=payload_kind,
                media_type=media_type,
                metadata={"slot": name},
            )
            if ref is not None:
                refs[name] = ref
        return refs

    def _stage_result(
        self,
        *,
        request: RunRequest,
        artifact_root: Path,
        sequence_manifest: SequenceManifest,
        slam: SlamArtifacts,
        status: StageStatus,
    ) -> StageResult:
        run_paths = RunArtifactPaths.build(artifact_root)
        visualization_artifacts = collect_native_visualization_artifacts(
            native_output_dir=run_paths.native_output_dir,
            preserve_native_rerun=request.visualization.preserve_native_rerun,
        )
        self._last_visualization_artifacts = visualization_artifacts
        outcome = StageOutcome(
            stage_key=StageKey.SLAM,
            status=status,
            config_hash=stable_hash(request.slam),
            input_fingerprint=stable_hash(sequence_manifest),
            artifacts=slam_artifacts_map(slam) | visualization_artifact_map(visualization_artifacts),
            error_message=self._last_error or "",
        )
        return StageResult(
            stage_key=StageKey.SLAM,
            payload=slam,
            outcome=outcome,
            final_runtime_status=self.status().model_copy(update={"lifecycle_state": status}),
        )

    def _progress_message(self) -> str:
        if self._accepted_keyframes:
            return f"processed {self._processed_frames} frames, accepted {self._accepted_keyframes} keyframes"
        if self._processed_frames:
            return f"processed {self._processed_frames} frames"
        return ""


def _semantic_update(update: SlamUpdate) -> SlamUpdate:
    """Return a semantic-only update with bulk arrays removed."""
    return update.model_copy(
        update={
            "image_rgb": None,
            "depth_map": None,
            "preview_rgb": None,
            "pointmap": None,
        }
    )


def _payload_arrays(update: SlamUpdate) -> dict[str, np.ndarray]:
    payloads: dict[str, np.ndarray] = {}
    for name, payload in (
        (IMAGE_REF, update.image_rgb),
        (DEPTH_REF, update.depth_map),
        (PREVIEW_REF, update.preview_rgb),
        (POINTMAP_REF, update.pointmap),
    ):
        if payload is not None:
            payloads[name] = np.asarray(payload)
    return payloads


def payload_bindings_for_updates(
    runtime: SlamStageRuntime,
    updates: Iterable[StageRuntimeUpdate],
) -> list[tuple[str, np.ndarray]]:
    """Materialize transient payload refs for current Rerun sidecar routing."""
    # TODO(pipeline-refactor/WP-08): Replace materialized payload bindings with
    # the canonical TransientPayloadRef resolver once observer routing owns it.
    bindings: dict[str, np.ndarray] = {}
    for update in updates:
        for item in update.visualizations:
            for ref in item.payload_refs.values():
                payload = runtime.read_payload(ref)
                if payload is not None:
                    bindings[ref.handle_id] = payload
    return list(bindings.items())


def _rolling_fps(timestamps: deque[float]) -> float:
    if len(timestamps) < 2:
        return 0.0
    elapsed = timestamps[-1] - timestamps[0]
    return 0.0 if elapsed <= 0.0 else (len(timestamps) - 1) / elapsed


__all__ = [
    "LegacySlamUpdate",
    "SlamStageRuntime",
    "payload_bindings_for_updates",
]
