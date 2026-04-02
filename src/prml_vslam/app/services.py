"""Reusable services for the packaged Streamlit app."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any

import numpy as np

from prml_vslam.io.record3d import (
    Record3DConnectionError,
    Record3DDevice,
    Record3DPacketStream,
    Record3DStreamConfig,
    Record3DStreamSnapshot,
    Record3DStreamState,
    Record3DTimeoutError,
    Record3DTransportId,
    Record3DUSBPacketStreamConfig,
)
from prml_vslam.io.record3d_wifi import Record3DWiFiStreamConfig
from prml_vslam.pipeline.contracts import MethodId
from prml_vslam.utils import Console
from prml_vslam.utils.path_config import PathConfig

from .models import (
    DatasetId,
    DiscoveredRun,
    ErrorSeries,
    EvaluationArtifact,
    EvaluationControls,
    MetricStats,
    PoseRelationId,
    SelectionSnapshot,
    TrajectorySeries,
)


class MetricsAppService:
    """Discover benchmark artifacts and evaluate trajectory pairs with `evo`."""

    def __init__(self, path_config: PathConfig) -> None:
        self.path_config = path_config

    def dataset_root(self, dataset: DatasetId) -> Path:
        """Return the repo-owned root for the selected dataset."""
        match dataset:
            case DatasetId.ADVIO:
                return self.path_config.resolve_repo_path("data/advio")
            case _:
                raise NotImplementedError(f"Unsupported dataset: {dataset!r}")

    def list_sequences(self, dataset: DatasetId) -> list[str]:
        """List locally available sequence slugs for the selected dataset."""
        root = self.dataset_root(dataset)
        if not root.exists():
            return []
        return sorted(
            path.name for path in root.iterdir() if path.is_dir() and path.name.startswith(f"{dataset.value}-")
        )

    def discover_runs(self, dataset: DatasetId, sequence_slug: str | None) -> list[DiscoveredRun]:
        """Return all runs under the artifacts root that match `sequence_slug`."""
        if sequence_slug is None:
            return []
        runs: list[DiscoveredRun] = []
        for trajectory_path in sorted(self.path_config.artifacts_dir.glob("**/slam/trajectory.tum")):
            run_root = trajectory_path.parent.parent
            relative_parts = run_root.relative_to(self.path_config.artifacts_dir).parts
            if sequence_slug not in relative_parts and sequence_slug not in run_root.name:
                continue
            method = self._infer_method(relative_parts)
            runs.append(
                DiscoveredRun(
                    artifact_root=run_root,
                    estimate_path=trajectory_path,
                    method=method,
                    label=self._format_run_label(
                        sequence_slug=sequence_slug, relative_parts=relative_parts, method=method
                    ),
                )
            )
        return runs

    def resolve_selection(
        self,
        *,
        dataset: DatasetId,
        sequence_slug: str | None,
        run_root: Path | None,
    ) -> SelectionSnapshot | None:
        """Resolve the current selector state into concrete dataset and run paths."""
        if sequence_slug is None:
            return None
        runs = self.discover_runs(dataset, sequence_slug)
        if not runs:
            return None
        selected_run = next((run for run in runs if run.artifact_root == run_root), runs[0])
        return SelectionSnapshot(
            dataset=dataset,
            sequence_slug=sequence_slug,
            dataset_root=self.dataset_root(dataset),
            reference_path=self.reference_path(dataset=dataset, sequence_slug=sequence_slug),
            run=selected_run,
        )

    def reference_path(self, *, dataset: DatasetId, sequence_slug: str) -> Path | None:
        """Return the repo-owned TUM reference trajectory for the selection when present."""
        sequence_root = self.dataset_root(dataset) / sequence_slug
        candidates = (
            sequence_root / "ground-truth" / "ground_truth.tum",
            sequence_root / "ground_truth.tum",
            sequence_root / "evaluation" / "ground_truth.tum",
        )
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def load_evaluation(
        self,
        *,
        selection: SelectionSnapshot,
        controls: EvaluationControls,
    ) -> EvaluationArtifact | None:
        """Load the persisted native `evo` result for the selected controls when present."""
        _, _, file_interface, _ = _load_evo_modules()
        result_path = self.result_path(selection.run.artifact_root, controls)
        if not result_path.exists() or selection.reference_path is None:
            return None
        result = file_interface.load_res_file(result_path, load_trajectories=True)
        return self._build_evaluation_artifact(
            result_path=result_path,
            selection=selection,
            controls=controls,
            info=result.info,
            stats=result.stats,
            np_arrays=result.np_arrays,
            trajectories=result.trajectories,
        )

    def compute_evaluation(
        self,
        *,
        selection: SelectionSnapshot,
        controls: EvaluationControls,
    ) -> EvaluationArtifact:
        """Compute APE explicitly with `evo`, persist it, and return the loaded result."""
        ape, sync, file_interface, _ = _load_evo_modules()
        if selection.reference_path is None:
            msg = "The selected dataset slice is missing a TUM reference trajectory."
            raise FileNotFoundError(msg)
        reference = file_interface.read_tum_trajectory_file(selection.reference_path)
        estimate = file_interface.read_tum_trajectory_file(selection.run.estimate_path)
        associated_ref, associated_est = sync.associate_trajectories(
            reference,
            estimate,
            max_diff=controls.max_diff_s,
        )
        result = ape(
            associated_ref,
            associated_est,
            self._to_evo_pose_relation(controls.pose_relation),
            align=controls.align,
            correct_scale=controls.correct_scale,
        )
        result_path = self.result_path(selection.run.artifact_root, controls)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        file_interface.save_res_file(result_path, result, confirm_overwrite=False)
        loaded = self.load_evaluation(selection=selection, controls=controls)
        if loaded is None:
            msg = f"Expected persisted evo result at '{result_path}', but it could not be loaded."
            raise FileNotFoundError(msg)
        return loaded

    @staticmethod
    def result_path(run_root: Path, controls: EvaluationControls) -> Path:
        """Return the deterministic persisted `evo` result path for the controls."""
        align_flag = "align" if controls.align else "no-align"
        scale_flag = "scale" if controls.correct_scale else "no-scale"
        diff_token = str(controls.max_diff_s).replace(".", "p")
        filename = f"evo_ape__{controls.pose_relation.value}__{align_flag}__{scale_flag}__diff-{diff_token}.zip"
        return run_root / "evaluation" / filename

    @staticmethod
    def _to_evo_pose_relation(pose_relation: PoseRelationId) -> object:
        _, _, _, pose_relation_enum = _load_evo_modules()
        return {
            PoseRelationId.TRANSLATION_PART: pose_relation_enum.translation_part,
            PoseRelationId.FULL_TRANSFORMATION: pose_relation_enum.full_transformation,
            PoseRelationId.ROTATION_ANGLE_DEG: pose_relation_enum.rotation_angle_deg,
            PoseRelationId.ROTATION_ANGLE_RAD: pose_relation_enum.rotation_angle_rad,
        }[pose_relation]

    @staticmethod
    def _infer_method(relative_parts: tuple[str, ...]) -> MethodId | None:
        for part in reversed(relative_parts):
            if part in MethodId._value2member_map_:
                return MethodId(part)
        return None

    @staticmethod
    def _format_run_label(
        *,
        sequence_slug: str,
        relative_parts: tuple[str, ...],
        method: MethodId | None,
    ) -> str:
        hidden_tokens = {sequence_slug, "slam"}
        if method is not None:
            hidden_tokens.add(method.value)
        visible_parts = [part for part in relative_parts if part not in hidden_tokens]
        method_label = method.value.replace("_", " ").upper() if method is not None else relative_parts[-1]
        if visible_parts:
            return f"{method_label} · {' / '.join(visible_parts)}"
        return method_label

    @staticmethod
    def _build_evaluation_artifact(
        *,
        result_path: Path,
        selection: SelectionSnapshot,
        controls: EvaluationControls,
        info: dict[str, object],
        stats: dict[str, object],
        np_arrays: dict[str, np.ndarray],
        trajectories: dict[str, object],
    ) -> EvaluationArtifact:
        reference_trajectory = trajectories.get("reference")
        estimate_trajectory = trajectories.get("estimate")
        trajectory_series: list[TrajectorySeries] = []
        matched_pairs = 0

        for name, trajectory in (("Reference", reference_trajectory), ("Estimate", estimate_trajectory)):
            if trajectory is None:
                continue
            positions_xyz = np.asarray(trajectory.positions_xyz, dtype=np.float64)
            timestamps_s = np.asarray(trajectory.timestamps, dtype=np.float64)
            matched_pairs = max(matched_pairs, int(len(timestamps_s)))
            trajectory_series.append(
                TrajectorySeries(
                    name=name,
                    positions_xyz=positions_xyz,
                    timestamps_s=timestamps_s,
                )
            )

        error_array = np.asarray(np_arrays.get("error_array", np.array([], dtype=np.float64)), dtype=np.float64)
        timestamp_array = np.asarray(np_arrays.get("timestamps", np.array([], dtype=np.float64)), dtype=np.float64)
        error_series = None
        if error_array.size and timestamp_array.size and error_array.size == timestamp_array.size:
            error_series = ErrorSeries(
                timestamps_s=timestamp_array,
                values=error_array,
            )

        return EvaluationArtifact(
            path=result_path,
            controls=controls,
            title=str(info.get("title", "Absolute Pose Error")),
            matched_pairs=matched_pairs,
            stats=MetricStats(
                rmse=float(stats["rmse"]),
                mean=float(stats["mean"]),
                median=float(stats["median"]),
                std=float(stats["std"]),
                min=float(stats["min"]),
                max=float(stats["max"]),
                sse=float(stats["sse"]),
            ),
            reference_path=selection.reference_path or Path(),
            estimate_path=selection.run.estimate_path,
            trajectories=trajectory_series,
            error_series=error_series,
        )


class Record3DAppService:
    """App-facing discovery helpers for Record3D transports."""

    def list_usb_devices(self) -> list[Record3DDevice]:
        """List USB-connected Record3D devices visible to the current machine."""
        stream = Record3DUSBPacketStreamConfig().setup_target()
        if stream is None:
            raise Record3DConnectionError("Failed to initialize the USB Record3D packet stream.")
        return stream.list_devices()


class Record3DStreamRuntimeController:
    """Own the live Record3D reader thread for one Streamlit browser session."""

    def __init__(
        self,
        *,
        frame_timeout_seconds: float = 0.5,
        fps_window_size: int = 30,
        trajectory_window_size: int = 512,
        usb_stream_factory: Callable[[int, float], Record3DPacketStream] | None = None,
        wifi_stream_factory: Callable[[str, float], Record3DPacketStream] | None = None,
    ) -> None:
        self.frame_timeout_seconds = frame_timeout_seconds
        self.fps_window_size = fps_window_size
        self.trajectory_window_size = trajectory_window_size
        self.usb_stream_factory = usb_stream_factory or self._default_usb_stream_factory
        self.wifi_stream_factory = wifi_stream_factory or self._default_wifi_stream_factory
        self.console = Console(__name__).child(self.__class__.__name__)
        self._lock = Lock()
        self._snapshot = Record3DStreamSnapshot()
        self._active_stream: Record3DPacketStream | None = None
        self._active_stop_event: Event | None = None
        self._worker_thread: Thread | None = None

    def snapshot(self) -> Record3DStreamSnapshot:
        """Return a copy of the latest live-stream snapshot."""
        with self._lock:
            return self._snapshot.model_copy(deep=True)

    def start_usb(self, *, device_index: int) -> None:
        """Start a USB-backed live Record3D reader thread."""
        self._start_worker(
            transport=Record3DTransportId.USB,
            source_descriptor=f"USB device #{device_index}",
            stream_factory=lambda: self.usb_stream_factory(device_index, self.frame_timeout_seconds),
        )

    def start_wifi(self, *, device_address: str) -> None:
        """Start a Wi-Fi-backed live Record3D reader thread."""
        self._start_worker(
            transport=Record3DTransportId.WIFI,
            source_descriptor=device_address,
            stream_factory=lambda: self.wifi_stream_factory(device_address, self.frame_timeout_seconds),
        )

    def stop(self) -> None:
        """Stop the active reader thread and clear the live snapshot."""
        with self._lock:
            worker = self._worker_thread
            stream = self._active_stream
            stop_event = self._active_stop_event

        if stop_event is not None:
            stop_event.set()
        if stream is not None:
            stream.disconnect()
        if worker is not None:
            worker.join(timeout=2.0)
            if worker.is_alive():
                raise RuntimeError("Timed out stopping the Record3D runtime worker thread.")

        with self._lock:
            self._active_stream = None
            self._active_stop_event = None
            self._worker_thread = None
            self._snapshot = Record3DStreamSnapshot()

    def _start_worker(
        self,
        *,
        transport: Record3DTransportId,
        source_descriptor: str,
        stream_factory: Callable[[], Record3DPacketStream],
    ) -> None:
        self.stop()
        stop_event = Event()
        worker = Thread(
            target=self._run_stream_worker,
            kwargs={
                "transport": transport,
                "source_descriptor": source_descriptor,
                "stop_event": stop_event,
                "stream_factory": stream_factory,
            },
            name=f"Record3D-{transport.value}-worker",
            daemon=True,
        )
        with self._lock:
            self._active_stop_event = stop_event
            self._worker_thread = worker
            self._snapshot = Record3DStreamSnapshot(
                transport=transport,
                state=Record3DStreamState.CONNECTING,
                source_label=source_descriptor,
            )
        worker.start()

    def _run_stream_worker(
        self,
        *,
        transport: Record3DTransportId,
        source_descriptor: str,
        stop_event: Event,
        stream_factory: Callable[[], Record3DPacketStream],
    ) -> None:
        frames_received = 0
        arrival_times: deque[float] = deque(maxlen=self.fps_window_size)
        trajectory_positions: deque[np.ndarray] = deque(maxlen=self.trajectory_window_size)
        trajectory_timestamps: deque[float] = deque(maxlen=self.trajectory_window_size)
        stream: Record3DPacketStream | None = None

        try:
            stream = stream_factory()
            with self._lock:
                self._active_stream = stream
            connected_target = stream.connect()
            source_label = self._format_source_label(
                transport=transport,
                source_descriptor=source_descriptor,
                connected_target=connected_target,
            )
            self._update_snapshot(
                transport=transport,
                state=Record3DStreamState.STREAMING,
                source_label=source_label,
                error_message="",
            )

            while not stop_event.is_set():
                try:
                    packet = stream.wait_for_packet(timeout_seconds=self.frame_timeout_seconds)
                except Record3DTimeoutError:
                    continue
                frames_received += 1
                arrival_times.append(packet.arrival_timestamp_s)
                camera_position = self._extract_camera_position(packet)
                if camera_position is not None:
                    trajectory_positions.append(camera_position)
                    trajectory_timestamps.append(packet.arrival_timestamp_s)
                self._update_snapshot(
                    transport=transport,
                    state=Record3DStreamState.STREAMING,
                    source_label=source_label,
                    latest_packet=packet,
                    received_frames=frames_received,
                    measured_fps=self._measure_fps(arrival_times),
                    trajectory_positions_xyz=self._to_positions_array(trajectory_positions),
                    trajectory_timestamps_s=np.asarray(tuple(trajectory_timestamps), dtype=np.float64),
                    error_message="",
                )
        except Exception as exc:
            if not stop_event.is_set():
                self._update_snapshot(
                    transport=transport,
                    state=Record3DStreamState.FAILED,
                    source_label=source_descriptor,
                    error_message=str(exc),
                )
        finally:
            if stream is not None:
                stream.disconnect()
            with self._lock:
                if self._active_stop_event is stop_event:
                    self._active_stream = None
                    self._active_stop_event = None
                    self._worker_thread = None
                if stop_event.is_set():
                    self._snapshot = Record3DStreamSnapshot()
                elif self._snapshot.state is Record3DStreamState.STREAMING:
                    self._snapshot = self._snapshot.model_copy(
                        update={
                            "state": Record3DStreamState.DISCONNECTED,
                            "latest_packet": None,
                            "received_frames": 0,
                            "measured_fps": 0.0,
                        }
                    )

    def _update_snapshot(
        self,
        *,
        transport: Record3DTransportId,
        state: Record3DStreamState,
        source_label: str,
        latest_packet: Any | None = None,
        received_frames: int = 0,
        measured_fps: float = 0.0,
        trajectory_positions_xyz: np.ndarray | None = None,
        trajectory_timestamps_s: np.ndarray | None = None,
        error_message: str = "",
    ) -> None:
        with self._lock:
            self._snapshot = Record3DStreamSnapshot(
                transport=transport,
                state=state,
                source_label=source_label,
                latest_packet=latest_packet,
                received_frames=received_frames,
                measured_fps=measured_fps,
                trajectory_positions_xyz=(
                    np.empty((0, 3), dtype=np.float64)
                    if trajectory_positions_xyz is None
                    else trajectory_positions_xyz
                ),
                trajectory_timestamps_s=(
                    np.empty((0,), dtype=np.float64) if trajectory_timestamps_s is None else trajectory_timestamps_s
                ),
                error_message=error_message,
            )

    @staticmethod
    def _default_usb_stream_factory(device_index: int, frame_timeout_seconds: float) -> Record3DPacketStream:
        stream = Record3DUSBPacketStreamConfig(
            stream=Record3DStreamConfig(
                device_index=device_index,
                frame_timeout_seconds=frame_timeout_seconds,
            )
        ).setup_target()
        if stream is None:
            raise Record3DConnectionError("Failed to initialize the USB Record3D packet stream.")
        return stream

    @staticmethod
    def _default_wifi_stream_factory(device_address: str, frame_timeout_seconds: float) -> Record3DPacketStream:
        stream = Record3DWiFiStreamConfig(
            device_address=device_address,
            frame_timeout_seconds=max(1.0, frame_timeout_seconds),
            signaling_timeout_seconds=10.0,
            setup_timeout_seconds=12.0,
        ).setup_target()
        if stream is None:
            raise Record3DConnectionError("Failed to initialize the Record3D Wi-Fi stream.")
        return stream

    @staticmethod
    def _format_source_label(
        *,
        transport: Record3DTransportId,
        source_descriptor: str,
        connected_target: Any,
    ) -> str:
        if transport is Record3DTransportId.USB and isinstance(connected_target, Record3DDevice):
            return f"{connected_target.udid} ({connected_target.product_id})"
        if hasattr(connected_target, "device_address"):
            return str(connected_target.device_address)
        return source_descriptor

    @staticmethod
    def _measure_fps(arrival_times: deque[float]) -> float:
        if len(arrival_times) < 2:
            return 0.0
        elapsed = arrival_times[-1] - arrival_times[0]
        if elapsed <= 0.0:
            return 0.0
        return float((len(arrival_times) - 1) / elapsed)

    @staticmethod
    def _extract_camera_position(packet: Any) -> np.ndarray | None:
        camera_pose = getattr(packet, "metadata", {}).get("camera_pose")
        if not isinstance(camera_pose, dict):
            return None
        try:
            position = np.array(
                [
                    float(camera_pose["tx"]),
                    float(camera_pose["ty"]),
                    float(camera_pose["tz"]),
                ],
                dtype=np.float64,
            )
        except (KeyError, TypeError, ValueError):
            return None
        if not np.all(np.isfinite(position)):
            return None
        return position

    @staticmethod
    def _to_positions_array(positions: deque[np.ndarray]) -> np.ndarray:
        if not positions:
            return np.empty((0, 3), dtype=np.float64)
        return np.vstack(tuple(positions)).astype(np.float64, copy=False)


def _load_evo_modules() -> tuple[Any, Any, Any, Any]:
    try:
        from evo.common_ape_rpe import ape
        from evo.core import sync
        from evo.core.metrics import PoseRelation
        from evo.tools import file_interface
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The optional `evo` dependency is required for trajectory evaluation. Install it with "
            "`uv sync --extra eval`."
        ) from exc
    return ape, sync, file_interface, PoseRelation


__all__ = [
    "MetricsAppService",
    "Record3DAppService",
    "Record3DStreamRuntimeController",
]
