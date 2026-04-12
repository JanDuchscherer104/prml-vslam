"""Generic multiprocessing proxy for SLAM sessions."""

from __future__ import annotations

import multiprocessing as mp
import queue
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from prml_vslam.utils import Console

if TYPE_CHECKING:
    from prml_vslam.interfaces import FramePacket
    from prml_vslam.methods.updates import SlamUpdate
    from prml_vslam.pipeline.contracts.artifacts import SlamArtifacts
    from prml_vslam.methods.protocols import SlamSession


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
                update = self._output_queue.get_nowait()
                if update is None:  # Sentinel for errors or unexpected exit
                    break
                updates.append(update)
            except queue.Empty:
                break
        return updates

    def close(self) -> SlamArtifacts:
        """Signal the worker to exit and retrieve final artifacts."""
        self._console.info("Closing multiprocess SLAM worker...")
        self._input_queue.put(None)  # Sentinel for exit
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
                    output_queue.put(update)
            except Exception as exc:
                logger.exception("Error during SLAM step in background worker: %s", exc)
                # We don't break here, try to continue with next frames
                # but we could send a sentinel if it's fatal.

        artifacts = session.close()
        result_pipe.send(artifacts)
    except Exception as exc:
        logger.exception("Fatal error in background worker: %s", exc)
        result_pipe.send(exc)
    finally:
        result_pipe.close()
        input_queue.close()
        output_queue.close()
