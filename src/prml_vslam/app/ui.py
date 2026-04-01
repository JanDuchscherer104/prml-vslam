"""UI helpers for the metrics app."""

from __future__ import annotations

import streamlit as st


def inject_styles() -> None:
    """Inject a compact light-first visual treatment for the metrics app."""
    st.markdown(
        """
        <style>
          :root {
            --prml-surface: #ffffff;
            --prml-muted: #5f6c7b;
            --prml-border: #d6dde6;
            --prml-accent: #1368ce;
            --prml-accent-soft: #edf4ff;
          }

          .stApp {
            background:
              radial-gradient(circle at top right, #f5f9ff 0, #f5f9ff 18rem, transparent 18rem),
              linear-gradient(180deg, #f7fafc 0%, #eef3f8 100%);
          }

          .main .block-container {
            max-width: 76rem;
            padding-top: 2rem;
            padding-bottom: 2rem;
          }

          .prml-panel {
            background: var(--prml-surface);
            border: 1px solid var(--prml-border);
            border-radius: 1rem;
            padding: 1rem 1.1rem;
            box-shadow: 0 16px 36px rgba(15, 23, 42, 0.05);
          }

          .prml-kicker {
            color: var(--prml-accent);
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
          }

          .prml-note {
            color: var(--prml-muted);
            font-size: 0.95rem;
            line-height: 1.5;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


__all__ = ["inject_styles"]
