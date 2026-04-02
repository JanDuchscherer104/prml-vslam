"""Typed Streamlit session-state adapter for the packaged app."""

from __future__ import annotations

from typing import Any, cast

import streamlit as st

from .models import AppState
from .services import Record3DStreamRuntimeController


class SessionStateStore:
    """Persist the typed app state and opaque runtimes under dedicated session keys."""

    def __init__(
        self,
        *,
        state_key: str = "_prml_vslam_app_state",
        record3d_runtime_key: str = "_prml_vslam_record3d_runtime",
    ) -> None:
        self.state_key = state_key
        self.record3d_runtime_key = record3d_runtime_key

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

    @staticmethod
    def _is_runtime_compatible(runtime: Any) -> bool:
        required_methods = ("snapshot", "stop", "start_usb", "start_wifi")
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
