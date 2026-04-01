"""Typed Streamlit session-state adapter for the metrics app."""

from __future__ import annotations

import streamlit as st

from .models import AppState


class SessionStateStore:
    """Persist the typed app state under one dedicated Streamlit session key."""

    def __init__(self, key: str = "_prml_vslam_metrics_state") -> None:
        self.key = key

    def load(self) -> AppState:
        """Load the current typed app state from Streamlit session storage."""
        payload = st.session_state.get(self.key)
        if payload is None:
            state = AppState()
            self.save(state)
            return state
        if isinstance(payload, AppState):
            return payload
        return AppState.model_validate(payload)

    def save(self, state: AppState) -> None:
        """Persist the app state as JSON-friendly data."""
        st.session_state[self.key] = state.model_dump(mode="json")


__all__ = ["SessionStateStore"]
