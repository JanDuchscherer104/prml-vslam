"""Ray actors that execute individual pipeline stages and streaming I/O."""

from __future__ import annotations

import threading
import time
from collections import deque

import numpy as np
import ray

from prml_vslam.benchmark import PreparedBenchmarkInputs
from prml_vslam.interfaces import CameraIntrinsics, FramePacketProvenance, FrameTransform
from prml_vslam.methods.events import BackendEvent, translate_slam_update
from prml_vslam.methods.factory import BackendFactory
from prml_vslam.methods.protocols import OfflineSlamBackend, StreamingSlamBackend
from prml_vslam.methods.session_init import SlamSessionInit
from prml_vslam.pipeline.contracts.events import FramePacketSummary, StageOutcome, StageStatus
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.pipeline.ray_runtime.common import (
    DEFAULT_MAX_FRAMES_IN_FLIGHT,
    FPS_WINDOW,
    HandlePayload,
    SlamStageResult,
    backend_config_payload,
    put_array_handle,
    put_preview_handle,
    rolling_fps,
    slam_artifacts_map,
    visualization_artifact_map,
)
from prml_vslam.protocols.source import StreamingSequenceSource
from prml_vslam.utils import Console, PathConfig, RunArtifactPaths


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
    ) -> SlamStageResult:
        console = Console(__name__).child(self.__class__.__name__)
        console.info(
            "Starting offline SLAM with backend '%s' at artifact root '%s'.",
            request.slam.backend.kind,
            plan.artifact_root,
        )
        backend = BackendFactory().build(request.slam.backend, path_config=path_config)
        if not isinstance(backend, OfflineSlamBackend):
            raise RuntimeError(f"Backend '{request.slam.backend.kind}' does not support offline execution.")
        slam = backend.run_sequence(
            sequence_manifest,
            benchmark_inputs,
            request.benchmark.trajectory.baseline_source,
            backend_config=backend_config_payload(request),
            output_policy=request.slam.outputs,
            artifact_root=plan.artifact_root,
        )
        run_paths = RunArtifactPaths.build(plan.artifact_root)
        from prml_vslam.visualization.rerun import collect_native_visualization_artifacts

        visualization = collect_native_visualization_artifacts(
            native_output_dir=run_paths.native_output_dir,
            preserve_native_rerun=request.visualization.preserve_native_rerun,
        )
        console.info(
            "Finished offline SLAM with backend '%s'; visualization artifacts %s.",
            request.slam.backend.kind,
            "collected" if visualization is not None else "not collected",
        )
        return SlamStageResult(
            outcome=StageOutcome(
                stage_key=StageKey.SLAM,
                status=StageStatus.COMPLETED,
                config_hash=stable_hash(request.slam),
                input_fingerprint=stable_hash(sequence_manifest),
                artifacts=slam_artifacts_map(slam) | visualization_artifact_map(visualization),
            ),
            slam=slam,
            visualization=visualization,
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
                    rerun_bindings=(
                        []
                        if packet.rgb is None
                        else [(frame_handle.handle_id, np.asarray(packet.rgb))]
                        if frame_handle is not None
                        else []
                    ),
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


@ray.remote(num_cpus=2, max_restarts=0, max_task_retries=0)
class StreamingSlamStageActor:
    """Ordered streaming SLAM stage with internal session state."""

    def __init__(self, *, coordinator_name: str, namespace: str) -> None:
        self._console = Console(__name__).child(self.__class__.__name__).child(coordinator_name)
        self._coordinator = ray.get_actor(coordinator_name, namespace=namespace)
        self._session = None
        self._accepted_keyframes = 0
        self._keyframe_timestamps = deque(maxlen=FPS_WINDOW)
        self._logged_first_notice = False

    def start_stage(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        path_config: PathConfig,
        session_init: SlamSessionInit,
    ) -> None:
        self._console.info(
            "Starting streaming SLAM actor with backend '%s' at artifact root '%s'.",
            request.slam.backend.kind,
            plan.artifact_root,
        )
        backend = BackendFactory().build(request.slam.backend, path_config=path_config)
        if not isinstance(backend, StreamingSlamBackend):
            raise RuntimeError(f"Backend '{request.slam.backend.kind}' does not support streaming execution.")
        self._session = backend.start_session(
            session_init=session_init,
            backend_config=backend_config_payload(request),
            output_policy=request.slam.outputs,
            artifact_root=plan.artifact_root,
        )

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
        if self._session is None:
            raise RuntimeError("Streaming SLAM actor has not been started.")
        from prml_vslam.interfaces import FramePacket

        rgb = self._resolve_payload(frame_ref)
        depth = self._resolve_payload(depth_ref)
        confidence = self._resolve_payload(confidence_ref)
        self._session.step(
            FramePacket(
                seq=packet.seq,
                timestamp_ns=packet.timestamp_ns,
                rgb=rgb,
                depth=depth,
                confidence=confidence,
                intrinsics=intrinsics,
                pose=pose,
                provenance=provenance,
            )
        )
        notices: list[BackendEvent] = []
        bindings: list[tuple[str, HandlePayload]] = []
        rerun_bindings: list[tuple[str, np.ndarray]] = []
        now = time.monotonic()
        for update in self._session.try_get_updates():
            preview_handle, preview_ref = put_preview_handle(update.preview_rgb)
            image_handle, image_ref = put_array_handle(update.image_rgb)
            depth_handle, depth_payload_ref = put_array_handle(update.depth_map)
            pointmap_handle, pointmap_payload_ref = put_array_handle(update.pointmap)
            for handle, ref in (
                (preview_handle, preview_ref),
                (image_handle, image_ref),
                (depth_handle, depth_payload_ref),
                (pointmap_handle, pointmap_payload_ref),
            ):
                if handle is not None and ref is not None:
                    bindings.append((handle.handle_id, ref))
            for handle, payload in (
                (preview_handle, update.preview_rgb),
                (image_handle, update.image_rgb),
                (depth_handle, update.depth_map),
                (pointmap_handle, update.pointmap),
            ):
                if handle is not None and payload is not None:
                    rerun_bindings.append((handle.handle_id, np.asarray(payload)))
            if update.is_keyframe:
                self._accepted_keyframes += 1
                self._keyframe_timestamps.append(now)
                if self._accepted_keyframes == 1:
                    self._console.debug("Accepted first streaming keyframe.")
            notices.extend(
                translate_slam_update(
                    update=update,
                    accepted_keyframes=self._accepted_keyframes,
                    backend_fps=rolling_fps(self._keyframe_timestamps),
                    preview_handle=preview_handle,
                    image_handle=image_handle,
                    depth_handle=depth_handle,
                    pointmap_handle=pointmap_handle,
                )
            )
        if notices and not self._logged_first_notice:
            self._console.debug("Translated first backend notice batch with %d notices.", len(notices))
            self._logged_first_notice = True
        self._coordinator.on_slam_notices.remote(
            notices=notices,
            bindings=bindings,
            rerun_bindings=rerun_bindings,
            released_credits=1,
        )

    @staticmethod
    def _resolve_payload(ref: ray.ObjectRef | np.ndarray | None) -> np.ndarray | None:
        if ref is None:
            return None
        if isinstance(ref, np.ndarray):
            return np.asarray(ref)
        return np.asarray(ray.get(ref))

    def close_stage(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        sequence_manifest: SequenceManifest,
    ) -> SlamStageResult:
        if self._session is None:
            raise RuntimeError("Streaming SLAM actor has not been started.")
        self._console.info("Closing streaming SLAM stage.")
        slam = self._session.close()
        run_paths = RunArtifactPaths.build(plan.artifact_root)
        from prml_vslam.visualization.rerun import collect_native_visualization_artifacts

        visualization = collect_native_visualization_artifacts(
            native_output_dir=run_paths.native_output_dir,
            preserve_native_rerun=request.visualization.preserve_native_rerun,
        )
        self._console.info(
            "Finished streaming SLAM close; visualization artifacts %s.",
            "collected" if visualization is not None else "not collected",
        )
        return SlamStageResult(
            outcome=StageOutcome(
                stage_key=StageKey.SLAM,
                status=StageStatus.COMPLETED,
                config_hash=stable_hash(request.slam),
                input_fingerprint=stable_hash(sequence_manifest),
                artifacts=slam_artifacts_map(slam) | visualization_artifact_map(visualization),
            ),
            slam=slam,
            visualization=visualization,
        )


__all__ = [
    "OfflineSlamStageActor",
    "PacketSourceActor",
    "StreamingSlamStageActor",
]
