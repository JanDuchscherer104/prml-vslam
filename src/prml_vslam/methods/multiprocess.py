"""Generic multiprocessing proxy for SLAM sessions."""

from __future__ import annotations

import multiprocessing as mp
import queue
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from prml_vslam.utils import Console

if TYPE_CHECKING:
    from prml_vslam.interfaces import FramePacket
    from prml_vslam.methods.protocols import SlamSession
    from prml_vslam.methods.updates import SlamUpdate
    from prml_vslam.pipeline.contracts.artifacts import SlamArtifacts


@dataclass(slots=True)
class _UpdateMessage:
    update: SlamUpdate


@dataclass(slots=True)
class _WorkerErrorMessage:
    error_message: str


@dataclass(slots=True)
class _DoneMessage:
    pass


_WORKER_CLOSE_TIMEOUT_SECONDS = 30.0
_WORKER_POLL_INTERVAL_SECONDS = 0.05


class MultiprocessSlamSession:
    """Proxy that runs a synchronous SLAM session in a separate background process."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], SlamSession],
        console: Console,
    ) -> None:
        self._console = console.child("MultiprocessSlamSession")
        ctx = mp.get_context("spawn")
        # Bound the input queue so that if the SLAM backend falls behind,
        # the producer blocks (backpressure), keeping the pipeline in sync.
        self._input_queue: mp.Queue = ctx.Queue(maxsize=2)
        self._output_queue: mp.Queue = ctx.Queue()
        self._result_pipe_parent, result_pipe_child = ctx.Pipe(duplex=False)
        self._pending_updates: list[SlamUpdate] = []
        self._worker_error: RuntimeError | None = None
        self._result: SlamArtifacts | None = None

        self._process = ctx.Process(
            target=_session_worker,
            args=(session_factory, self._input_queue, self._output_queue, result_pipe_child),
            daemon=True,
        )
        self._process.start()
        self._console.info("Multiprocess SLAM worker started (PID: %d) using 'spawn' context.", self._process.pid)

    def step(self, frame: FramePacket) -> None:
        """Push one frame to the background worker, blocking if the queue is full (backpressure)."""
        while True:
            self._poll_worker_state()
            self._raise_worker_error()
            if not self._process.is_alive():
                self._worker_error = RuntimeError("SLAM worker exited before accepting a frame.")
                self._raise_worker_error()
            try:
                self._input_queue.put(frame, timeout=_WORKER_POLL_INTERVAL_SECONDS)
                return
            except queue.Full:
                continue

    def try_get_updates(self) -> list[SlamUpdate]:
        """Poll the output queue for any completed updates."""
        self._poll_worker_state()
        self._raise_worker_error()
        updates = self._pending_updates
        self._pending_updates = []
        return updates

    def close(self) -> SlamArtifacts:
        """Signal the worker to exit and retrieve final artifacts."""
        self._console.info("Closing multiprocess SLAM worker...")
        self._poll_worker_state()
        self._raise_worker_error()
        self._send_shutdown_sentinel()
        self._wait_for_worker_exit()
        self._poll_worker_state(result_timeout_seconds=1.0)
        self._raise_worker_error()
        if self._result is not None:
            return self._result

        raise RuntimeError("Failed to retrieve artifacts from the background worker.")

    def _send_shutdown_sentinel(self) -> None:
        deadline = time.monotonic() + _WORKER_CLOSE_TIMEOUT_SECONDS
        while True:
            self._poll_worker_state()
            self._raise_worker_error()
            if not self._process.is_alive():
                return
            try:
                self._input_queue.put(None, timeout=_WORKER_POLL_INTERVAL_SECONDS)
                return
            except queue.Full as exc:
                if time.monotonic() >= deadline:
                    self._console.error("SLAM worker input queue stayed full during shutdown; terminating worker.")
                    self._terminate_worker_process()
                    raise RuntimeError(
                        "Failed to shut down the SLAM worker because its input queue stayed full."
                    ) from exc

    def _wait_for_worker_exit(self) -> None:
        deadline = time.monotonic() + _WORKER_CLOSE_TIMEOUT_SECONDS
        while self._process.is_alive():
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                self._console.error("Worker process did not exit gracefully; terminating.")
                self._terminate_worker_process()
                return
            self._process.join(timeout=min(_WORKER_POLL_INTERVAL_SECONDS, remaining))
            self._poll_worker_state()
            self._raise_worker_error()

    def _poll_worker_state(self, *, result_timeout_seconds: float = 0.0) -> None:
        self._drain_output_messages()
        self._poll_result_pipe(timeout_seconds=result_timeout_seconds)

    def _drain_output_messages(self) -> None:
        while True:
            try:
                message = self._output_queue.get_nowait()
            except (queue.Empty, OSError, ValueError):
                return
            if isinstance(message, _UpdateMessage):
                self._pending_updates.append(message.update)
            elif isinstance(message, _WorkerErrorMessage):
                self._worker_error = RuntimeError(message.error_message)

    def _poll_result_pipe(self, *, timeout_seconds: float) -> None:
        if self._result is not None or self._worker_error is not None:
            return
        try:
            has_result = self._result_pipe_parent.poll(timeout_seconds)
        except (EOFError, OSError):
            return
        if not has_result:
            return
        try:
            result = self._result_pipe_parent.recv()
        except EOFError:
            return
        if isinstance(result, Exception):
            self._worker_error = result if isinstance(result, RuntimeError) else RuntimeError(str(result))
            return
        self._result = result

    def _raise_worker_error(self) -> None:
        if self._worker_error is None:
            return
        if self._process.is_alive():
            self._terminate_worker_process()
        raise self._worker_error

    def _terminate_worker_process(self) -> None:
        if self._process.is_alive():
            self._process.terminate()
        self._process.join()


def _session_worker(
    session_factory: Callable[[], SlamSession],
    input_queue: mp.Queue,
    output_queue: mp.Queue,
    result_pipe: mp.connection.Connection,
) -> None:
    """Continuous loop running inside the background process."""
    session = None
    # We use a basic console since we don't have the parent's configured one easily.
    # But since it's a child process of the same terminal, print() or logging works.
    import logging  # noqa: PLC0415

    logger = logging.getLogger("prml_vslam.multiprocess_worker")

    try:
        session = session_factory()
        while True:
            packet = input_queue.get()
            if packet is None:  # Sentinel for exit
                break

            try:
                session.step(packet)
                for update in session.try_get_updates():
                    output_queue.put(_UpdateMessage(update=update))
            except Exception as exc:
                logger.exception("Error during SLAM step in background worker: %s", exc)
                output_queue.put(_WorkerErrorMessage(error_message=str(exc)))
                result_pipe.send(RuntimeError(str(exc)))
                return

        artifacts = session.close()
        for update in session.try_get_updates():
            output_queue.put(_UpdateMessage(update=update))
        result_pipe.send(artifacts)
        output_queue.put(_DoneMessage())
    except Exception as exc:
        logger.exception("Fatal error in background worker: %s", exc)
        output_queue.put(_WorkerErrorMessage(error_message=str(exc)))
        result_pipe.send(exc)
    finally:
        result_pipe.close()
        input_queue.close()
        output_queue.close()
