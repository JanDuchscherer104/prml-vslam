"""Typed Streamlit session-state adapter for the packaged app."""

from __future__ import annotations

from typing import Any, cast

import streamlit as st

from .models import AppState
from .pipeline_runtime import PipelineDemoRuntimeController
from .services import AdvioPreviewRuntimeController, Record3DStreamRuntimeController


class SessionStateStore:
    """Persist the typed app state and opaque runtimes under dedicated session keys."""

    def __init__(
        self,
        *,
        state_key: str = "_prml_vslam_app_state",
        record3d_runtime_key: str = "_prml_vslam_record3d_runtime",
        advio_runtime_key: str = "_prml_vslam_advio_runtime",
        pipeline_runtime_key: str = "_prml_vslam_pipeline_runtime",
    ) -> None:
        self.state_key = state_key
        self.record3d_runtime_key = record3d_runtime_key
        self.advio_runtime_key = advio_runtime_key
        self.pipeline_runtime_key = pipeline_runtime_key

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
        runtime = st.session_state.get(self.record3d_runtime_key)
        if runtime is None:
            runtime = Record3DStreamRuntimeController()
            st.session_state[self.record3d_runtime_key] = runtime
            return runtime
        if isinstance(runtime, Record3DStreamRuntimeController):
            return runtime
        if self._is_runtime_compatible(runtime):
            return cast(Record3DStreamRuntimeController, runtime)

        self._shutdown_stale_runtime(runtime)
        replacement = Record3DStreamRuntimeController()
        st.session_state[self.record3d_runtime_key] = replacement
        return replacement

    def load_advio_runtime(self) -> AdvioPreviewRuntimeController:
        """Load or create the opaque ADVIO preview runtime controller for this session."""
        runtime = st.session_state.get(self.advio_runtime_key)
        if runtime is None:
            runtime = AdvioPreviewRuntimeController()
            st.session_state[self.advio_runtime_key] = runtime
            return runtime
        if isinstance(runtime, AdvioPreviewRuntimeController):
            return runtime
        if self._is_advio_runtime_compatible(runtime):
            return cast(AdvioPreviewRuntimeController, runtime)

        self._shutdown_stale_runtime(runtime)
        replacement = AdvioPreviewRuntimeController()
        st.session_state[self.advio_runtime_key] = replacement
        return replacement

    def load_pipeline_runtime(self) -> PipelineDemoRuntimeController:
        """Load or create the opaque Pipeline demo runtime controller for this session."""
        runtime = st.session_state.get(self.pipeline_runtime_key)
        if runtime is None:
            runtime = PipelineDemoRuntimeController()
            st.session_state[self.pipeline_runtime_key] = runtime
            return runtime
        if isinstance(runtime, PipelineDemoRuntimeController):
            return runtime
        if self._is_pipeline_runtime_compatible(runtime):
            return cast(PipelineDemoRuntimeController, runtime)

        self._shutdown_stale_runtime(runtime)
        replacement = PipelineDemoRuntimeController()
        st.session_state[self.pipeline_runtime_key] = replacement
        return replacement

    @staticmethod
    def _is_runtime_compatible(runtime: Any) -> bool:
        required_methods = ("snapshot", "stop", "start_usb", "start_wifi")
        return all(callable(getattr(runtime, method_name, None)) for method_name in required_methods)

    @staticmethod
    def _is_advio_runtime_compatible(runtime: Any) -> bool:
        required_methods = ("snapshot", "stop", "start")
        return all(callable(getattr(runtime, method_name, None)) for method_name in required_methods)

    @staticmethod
    def _is_pipeline_runtime_compatible(runtime: Any) -> bool:
        required_methods = ("snapshot", "stop", "start")
        return all(callable(getattr(runtime, method_name, None)) for method_name in required_methods)

    @staticmethod
    def _shutdown_stale_runtime(runtime: Any) -> None:
        stop = getattr(runtime, "stop", None)
        if not callable(stop):
            return
        try:
            stop()
        except Exception:
            return


__all__ = ["SessionStateStore"]
