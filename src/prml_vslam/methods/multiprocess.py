"""Generic multiprocessing proxy for SLAM sessions."""

from __future__ import annotations

import multiprocessing as mp
import queue
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from prml_vslam.utils import Console

if TYPE_CHECKING:
    from prml_vslam.interfaces import FramePacket
    from prml_vslam.methods.protocols import SlamSession
    from prml_vslam.methods.updates import SlamUpdate
    from prml_vslam.pipeline.contracts.artifacts import SlamArtifacts


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

        self._process = ctx.Process(
            target=_session_worker,
            args=(session_factory, self._input_queue, self._output_queue, result_pipe_child),
            daemon=True,
        )
        self._process.start()
        self._console.info("Multiprocess SLAM worker started (PID: %d) using 'spawn' context.", self._process.pid)

    def step(self, frame: FramePacket) -> None:
        """Push one frame to the background worker, blocking if the queue is full (backpressure)."""
        # Block until there is space in the queue.
        # This causes the upstream ingestion loop to wait, naturally slowing down
        # the entire pipeline to the speed of the SLAM backend without dropping frames.
        self._input_queue.put(frame)

    def try_get_updates(self) -> list[SlamUpdate]:
        """Poll the output queue for any completed updates."""
        updates = []
        while True:
            try:
                message = self._output_queue.get_nowait()
                match message:
                    case WorkerUpdate(update=update):
                        updates.append(update)
                    case WorkerError(error_message=error_message):
                        raise RuntimeError(error_message)
                    case WorkerDone():
                        break
                    case _:
                        raise RuntimeError(f"Unexpected worker message type: {type(message).__name__}")
            except queue.Empty:
                break
        return updates

    def close(self) -> SlamArtifacts:
        """Signal the worker to exit and retrieve final artifacts."""
        self._console.info("Closing multiprocess SLAM worker...")
        try:
            self._input_queue.put(None, timeout=1.0)
        except queue.Full:
            self._console.error("Worker input queue is full during close; terminating worker process.")
            self._process.terminate()
        self._process.join(timeout=30.0)
        if self._process.is_alive():
            self._console.error("Worker process did not exit gracefully; terminating.")
            self._process.terminate()
            self._process.join()

        if self._result_pipe_parent.poll(timeout=1.0):
            artifacts = self._result_pipe_parent.recv()
            if isinstance(artifacts, Exception):
                raise artifacts
            return artifacts

        raise RuntimeError("Failed to retrieve artifacts from the background worker.")


@dataclass(slots=True)
class WorkerUpdate:
    """One successful incremental update emitted by the worker."""

    update: SlamUpdate


@dataclass(slots=True)
class WorkerError:
    """One frame-level worker failure that should fail the parent session."""

    error_message: str


@dataclass(slots=True)
class WorkerDone:
    """Terminal worker marker after session close."""


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
                    output_queue.put(WorkerUpdate(update=update))
            except Exception as exc:
                logger.exception("Error during SLAM step in background worker: %s", exc)
                output_queue.put(WorkerError(error_message=str(exc)))
                raise

        artifacts = session.close()
        output_queue.put(WorkerDone())
        result_pipe.send(artifacts)
    except Exception as exc:
        logger.exception("Fatal error in background worker: %s", exc)
        result_pipe.send(exc)
    finally:
        result_pipe.close()
        input_queue.close()
        output_queue.close()
