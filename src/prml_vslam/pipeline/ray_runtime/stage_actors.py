"""Ray actors that execute individual pipeline stages and streaming I/O."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import TYPE_CHECKING

import numpy as np
import ray

from prml_vslam.interfaces import CameraIntrinsics, FramePacketProvenance, FrameTransform
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.slam import SlamArtifacts, SlamSessionInit
from prml_vslam.pipeline.contracts.events import FramePacketSummary, StageOutcome, StageStatus
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.pipeline.ray_runtime.common import (
    DEFAULT_MAX_FRAMES_IN_FLIGHT,
    FPS_WINDOW,
    put_array_handle,
    rolling_fps,
    slam_artifacts_map,
    visualization_artifact_map,
)
from prml_vslam.pipeline.stages.slam import SlamFrameInput, SlamOfflineInput, SlamStageRuntime, SlamStreamingStartInput
from prml_vslam.protocols.source import StreamingSequenceSource
from prml_vslam.utils import Console, PathConfig, RunArtifactPaths

if TYPE_CHECKING:
    from prml_vslam.pipeline.ray_runtime.stage_program import StageCompletionPayload


# TODO(pipeline-refactor/WP-10): Delete this SLAM actor after RuntimeManager
# deploys SlamStageRuntime through StageRuntimeProxy.
@ray.remote(num_cpus=2, max_restarts=0, max_task_retries=0)
class OfflineSlamStageActor:
    """Run one offline SLAM stage."""

    def run(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        sequence_manifest: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        path_config: PathConfig,
    ) -> StageCompletionPayload:
        # TODO(pipeline-refactor/WP-10): Delete this StageCompletionPayload
        # actor wrapper after the coordinator invokes SlamStageRuntime through
        # RuntimeManager/StageRuntimeProxy and consumes StageResult directly.
        from prml_vslam.pipeline.ray_runtime.stage_program import StageCompletionPayload

        console = Console(__name__).child(self.__class__.__name__)
        console.info(
            "Starting offline SLAM with backend '%s' at artifact root '%s'.",
            request.slam.backend.method_id.value,
            plan.artifact_root,
        )
        runtime = SlamStageRuntime()
        result = runtime.run_offline(
            SlamOfflineInput(
                request=request,
                plan=plan,
                path_config=path_config,
                sequence_manifest=sequence_manifest,
                benchmark_inputs=benchmark_inputs,
            )
        )
        console.info(
            "Finished offline SLAM with backend '%s'; visualization artifacts %s.",
            request.slam.backend.method_id.value,
            "collected" if runtime.last_visualization_artifacts is not None else "not collected",
        )
        return StageCompletionPayload(
            outcome=result.outcome,
            slam=result.payload if isinstance(result.payload, SlamArtifacts) else None,
            visualization=runtime.last_visualization_artifacts,
        )


@ray.remote(num_cpus=1, max_restarts=0, max_task_retries=0)
class PacketSourceActor:
    """Read packets from one streaming source with coordinator-owned credits."""

    def __init__(self, *, coordinator_name: str, namespace: str, frame_timeout_seconds: float = 5.0) -> None:
        self._console = Console(__name__).child(self.__class__.__name__).child(coordinator_name)
        self._coordinator = ray.get_actor(coordinator_name, namespace=namespace)
        self._frame_timeout_seconds = frame_timeout_seconds
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._credits = 0
        self._credits_cv = threading.Condition()
        self._received_frames = 0
        self._packet_timestamps = deque(maxlen=FPS_WINDOW)

    def start_stream(
        self,
        *,
        source: StreamingSequenceSource,
        initial_credits: int = DEFAULT_MAX_FRAMES_IN_FLIGHT,
        loop: bool = False,
    ) -> None:
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("Packet source actor is already running.")
        self._console.info(
            "Starting packet stream for source '%s' with loop=%s, initial_credits=%d, timeout=%s.",
            getattr(source, "label", source.__class__.__name__),
            loop,
            initial_credits,
            self._frame_timeout_seconds,
        )
        self._stop_event.clear()
        self._credits = initial_credits
        self._thread = threading.Thread(target=self._run_source, args=(source, loop), daemon=True)
        self._thread.start()

    def grant_credit(self, count: int = 1) -> None:
        with self._credits_cv:
            self._credits += count
            self._credits_cv.notify_all()

    def stop(self) -> None:
        self._stop_event.set()
        with self._credits_cv:
            self._credits_cv.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                self._console.warning("Timed out waiting for packet source worker thread to stop.")

    def _run_source(self, source: StreamingSequenceSource, loop: bool) -> None:
        stream = source.open_stream(loop=loop)
        try:
            stream.connect()
            while not self._stop_event.is_set():
                with self._credits_cv:
                    while self._credits <= 0 and not self._stop_event.is_set():
                        self._credits_cv.wait(timeout=0.1)
                    if self._stop_event.is_set():
                        self._console.debug("Stop requested while waiting for packet credits.")
                        break
                    self._credits -= 1
                packet = stream.wait_for_packet(timeout_seconds=self._frame_timeout_seconds)
                self._received_frames += 1
                self._packet_timestamps.append(time.monotonic())
                frame_handle, frame_ref = put_array_handle(packet.rgb)
                depth_ref = None if packet.depth is None else ray.put(np.asarray(packet.depth))
                confidence_ref = None if packet.confidence is None else ray.put(np.asarray(packet.confidence))
                self._coordinator.on_packet.remote(
                    packet=FramePacketSummary(
                        seq=packet.seq,
                        timestamp_ns=packet.timestamp_ns,
                        provenance=packet.provenance.model_copy(deep=True),
                    ),
                    frame_handle=frame_handle,
                    frame_ref=frame_ref,
                    depth_ref=depth_ref,
                    confidence_ref=confidence_ref,
                    intrinsics=packet.intrinsics,
                    pose=packet.pose,
                    provenance=packet.provenance.model_copy(deep=True),
                    received_frames=self._received_frames,
                    measured_fps=rolling_fps(self._packet_timestamps),
                )
        except EOFError:
            self._console.debug("Streaming source reached EOF.")
            self._coordinator.on_source_eof.remote()
        except Exception as exc:  # pragma: no cover - exercised via integration tests
            self._console.error("Streaming source raised an unexpected exception: %s", exc)
            self._coordinator.on_source_error.remote(str(exc))
        finally:
            try:
                stream.disconnect()
            except Exception:
                pass


# TODO(pipeline-refactor/WP-10): Delete this SLAM actor after RuntimeManager
# deploys SlamStageRuntime through StageRuntimeProxy.
@ray.remote(num_cpus=2, max_restarts=0, max_task_retries=0)
class StreamingSlamStageActor:
    """Ordered streaming SLAM stage with internal session state."""

    def __init__(self, *, coordinator_name: str, namespace: str) -> None:
        self._console = Console(__name__).child(self.__class__.__name__).child(coordinator_name)
        self._coordinator = ray.get_actor(coordinator_name, namespace=namespace)
        self._session = None
        self._runtime: SlamStageRuntime | None = None

    def start_stage(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        path_config: PathConfig,
        session_init: SlamSessionInit,
    ) -> None:
        # TODO(pipeline-refactor/WP-10): Delete this actor start wrapper after
        # SlamStageRuntime is deployed directly behind StageRuntimeProxy.
        self._console.info(
            "Starting streaming SLAM actor with backend '%s' at artifact root '%s'.",
            request.slam.backend.method_id.value,
            plan.artifact_root,
        )
        self._runtime = SlamStageRuntime()
        self._runtime.start_streaming(
            SlamStreamingStartInput(
                request=request,
                plan=plan,
                path_config=path_config,
                session_init=session_init,
            )
        )
        self._session = self._runtime.session_for_migration

    def push_frame(
        self,
        *,
        packet: FramePacketSummary,
        frame_ref: ray.ObjectRef | np.ndarray | None,
        depth_ref: ray.ObjectRef | np.ndarray | None,
        confidence_ref: ray.ObjectRef | np.ndarray | None,
        intrinsics: CameraIntrinsics | None,
        pose: FrameTransform | None,
        provenance: FramePacketProvenance,
    ) -> None:
        # TODO(pipeline-refactor/WP-10): Delete this push_frame compatibility
        # wrapper after the coordinator submits SlamFrameInput through the
        # target StreamingStageRuntime protocol.
        if self._runtime is None:
            raise RuntimeError("Streaming SLAM actor has not been started.")
        from prml_vslam.interfaces import FramePacket

        self._runtime.submit_stream_item(
            SlamFrameInput(
                frame=FramePacket(
                    seq=packet.seq,
                    timestamp_ns=packet.timestamp_ns,
                    rgb=self._resolve_payload(frame_ref),
                    depth=self._resolve_payload(depth_ref),
                    confidence=self._resolve_payload(confidence_ref),
                    intrinsics=intrinsics,
                    pose=pose,
                    provenance=provenance,
                )
            )
        )
        runtime_updates = self._runtime.drain_runtime_updates()
        self._coordinator.grant_slam_source_credit.remote(credit_count=1)
        if runtime_updates:
            self._coordinator.on_slam_runtime_updates.remote(
                updates=runtime_updates,
            )
        # Keep the coordinator credit/finalization handshake on the legacy
        # callback until the dedicated runtime-update credit API lands.
        self._coordinator.on_slam_notices.remote(
            notices=[],
            bindings=[],
            released_credits=1,
            grant_source_credit=False,
            project_to_snapshot=False,
        )

    @staticmethod
    def _resolve_payload(ref: ray.ObjectRef | np.ndarray | None) -> np.ndarray | None:
        if ref is None:
            return None
        if isinstance(ref, np.ndarray):
            return np.asarray(ref)
        return np.asarray(ray.get(ref))

    def read_payload(self, handle_id: str) -> np.ndarray | None:
        """Resolve one runtime-owned transient payload for observer sidecars."""
        if self._runtime is None:
            return None
        return self._runtime.read_payload_by_id(handle_id)

    def close_stage(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        sequence_manifest: SequenceManifest,
    ) -> StageCompletionPayload:
        # TODO(pipeline-refactor/WP-10): Delete this StageCompletionPayload
        # close wrapper after finish_streaming() returns StageResult directly
        # to the coordinator/runtime runner.
        from prml_vslam.pipeline.ray_runtime.stage_program import StageCompletionPayload

        if self._runtime is None and self._session is None:
            raise RuntimeError("Streaming SLAM actor has not been started.")
        self._console.info("Closing streaming SLAM stage.")
        if self._runtime is not None:
            result = self._runtime.finish_streaming()
            slam = result.payload if isinstance(result.payload, SlamArtifacts) else None
            visualization = self._runtime.last_visualization_artifacts
            outcome = result.outcome
        else:
            # TODO(pipeline-refactor/WP-10): Remove this fallback after tests and
            # callers construct StreamingSlamStageActor through start_stage().
            slam = self._session.close()
            run_paths = RunArtifactPaths.build(plan.artifact_root)
            from prml_vslam.visualization.rerun import collect_native_visualization_artifacts

            visualization = collect_native_visualization_artifacts(
                native_output_dir=run_paths.native_output_dir,
                preserve_native_rerun=request.visualization.preserve_native_rerun,
            )
            outcome = StageOutcome(
                stage_key=StageKey.SLAM,
                status=StageStatus.COMPLETED,
                config_hash=stable_hash(request.slam),
                input_fingerprint=stable_hash(sequence_manifest),
                artifacts=slam_artifacts_map(slam) | visualization_artifact_map(visualization),
            )
        self._console.info(
            "Finished streaming SLAM close; visualization artifacts %s.",
            "collected" if visualization is not None else "not collected",
        )
        return StageCompletionPayload(
            outcome=outcome,
            slam=slam,
            visualization=visualization,
        )


__all__ = [
    "OfflineSlamStageActor",
    "PacketSourceActor",
    "StreamingSlamStageActor",
]
