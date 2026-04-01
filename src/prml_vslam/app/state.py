"""Typed Streamlit session-state adapter for the PRML VSLAM app."""

from __future__ import annotations

from typing import Any

import streamlit as st

from .models import AppState


class SessionStateStore:
    """Persist a typed app state under one Streamlit session key."""

    def __init__(self, key: str = "_prml_vslam_metrics_app") -> None:
        self.key = key

    def load(self) -> AppState:
        """Load the current app state from Streamlit session storage."""
        raw_state = st.session_state.get(self.key)
        state = AppState.model_validate(raw_state) if raw_state is not None else AppState()
        self.save(state)
        return state

    def save(self, state: AppState) -> None:
        """Persist the app state as JSON-friendly data."""
        st.session_state[self.key] = state.model_dump(mode="json")

    def debug_snapshot(self, state: AppState) -> dict[str, Any]:
        """Return a compact debug payload for the current session state."""
        return {
            "typed_state": state.model_dump(mode="json"),
            "raw_session_state_keys": sorted(str(key) for key in st.session_state.keys()),
        }


__all__ = ["SessionStateStore"]
