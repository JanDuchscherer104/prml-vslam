"""Typed Streamlit session-state adapter for the packaged app."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

import streamlit as st

from prml_vslam.pipeline.run_service import RunService
from prml_vslam.utils import PathConfig

from .models import AppState
from .services import AdvioPreviewRuntimeController, Record3DStreamRuntimeController

RuntimeT = TypeVar("RuntimeT")


class SessionStateStore:
    """Persist the typed app state and opaque runtimes under dedicated session keys."""

    def __init__(
        self,
        *,
        state_key: str = "_prml_vslam_app_state",
        record3d_runtime_key: str = "_prml_vslam_record3d_runtime",
        advio_runtime_key: str = "_prml_vslam_advio_runtime",
        run_service_key: str = "_prml_vslam_pipeline_runtime",
    ) -> None:
        self.state_key = state_key
        self.record3d_runtime_key = record3d_runtime_key
        self.advio_runtime_key = advio_runtime_key
        self.run_service_key = run_service_key

    def load(self) -> AppState:
        """Load the current typed app state from Streamlit session storage."""
        payload = st.session_state.get(self.state_key)
        if payload is None:
            state = AppState()
            self.save(state)
            return state
        if isinstance(payload, AppState):
            return payload
        if hasattr(payload, "model_dump") and callable(payload.model_dump):
            return AppState.model_validate(payload.model_dump(mode="json"))
        return AppState.model_validate(payload)

    def save(self, state: AppState) -> None:
        """Persist the JSON-friendly app state."""
        st.session_state[self.state_key] = state.model_dump(mode="json")

    def load_record3d_runtime(self) -> Record3DStreamRuntimeController:
        """Load or create the opaque Record3D runtime controller for this session."""
        return self._load_runtime(
            session_key=self.record3d_runtime_key,
            runtime_type=Record3DStreamRuntimeController,
            required_methods=("snapshot", "stop", "start_usb", "start_wifi"),
            factory=Record3DStreamRuntimeController,
        )

    def load_advio_runtime(self) -> AdvioPreviewRuntimeController:
        """Load or create the opaque ADVIO preview runtime controller for this session."""
        return self._load_runtime(
            session_key=self.advio_runtime_key,
            runtime_type=AdvioPreviewRuntimeController,
            required_methods=("snapshot", "stop", "start"),
            factory=AdvioPreviewRuntimeController,
        )

    def load_run_service(self, *, path_config: PathConfig | None = None) -> RunService:
        """Load or create the opaque pipeline run facade for this session."""
        return self._load_runtime(
            session_key=self.run_service_key,
            runtime_type=RunService,
            required_methods=("snapshot", "stop_run", "start_run"),
            factory=lambda: RunService(path_config=path_config),
        )

    def _load_runtime(
        self,
        *,
        session_key: str,
        runtime_type: type[RuntimeT],
        required_methods: tuple[str, ...],
        factory: Callable[[], RuntimeT],
    ) -> RuntimeT:
        """Return one stored runtime or replace a stale session object."""
        runtime = st.session_state.get(session_key)
        if runtime is None:
            return self._store_runtime(session_key=session_key, runtime=factory())
        if isinstance(runtime, runtime_type):
            return runtime
        if self._has_runtime_methods(runtime, required_methods):
            return cast(RuntimeT, runtime)

        self._shutdown_stale_runtime(runtime)
        return self._store_runtime(session_key=session_key, runtime=factory())

    @staticmethod
    def _has_runtime_methods(runtime: Any, required_methods: tuple[str, ...]) -> bool:
        return all(callable(getattr(runtime, method_name, None)) for method_name in required_methods)

    @staticmethod
    def _store_runtime(*, session_key: str, runtime: RuntimeT) -> RuntimeT:
        st.session_state[session_key] = runtime
        return runtime

    @staticmethod
    def _shutdown_stale_runtime(runtime: Any) -> None:
        stop = getattr(runtime, "stop_run", None)
        if not callable(stop):
            stop = getattr(runtime, "stop", None)
        if not callable(stop):
            return
        try:
            stop()
        except Exception:
            return


def save_model_updates(store: SessionStateStore, state: AppState, model: Any, **updates: object) -> bool:
    """Persist model updates only when at least one value changed."""
    if all(getattr(model, key) == value for key, value in updates.items()):
        return False
    for key, value in updates.items():
        setattr(model, key, value)
    store.save(state)
    return True


__all__ = ["SessionStateStore", "save_model_updates"]
