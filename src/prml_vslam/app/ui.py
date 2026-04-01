"""Reusable UI helpers for the PRML VSLAM Streamlit app."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st


def inject_styles() -> None:
    """Apply the shared light-first app styles."""
    st.markdown(
        """
        <style>
          :root {
            --app-bg: #f5f7fa;
            --card-bg: #ffffff;
            --card-border: #dbe4ea;
            --text-strong: #16202a;
            --text-muted: #5a6875;
            --accent: #2563eb;
          }

          .stApp {
            background:
              radial-gradient(circle at top right, rgba(37, 99, 235, 0.06), transparent 30%),
              linear-gradient(180deg, #fbfcfe 0%, var(--app-bg) 100%);
          }

          .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1240px;
          }

          .app-shell {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 1rem 1.2rem;
            margin-bottom: 1rem;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.05);
          }

          .app-kicker {
            color: var(--accent);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.25rem;
          }

          .app-title {
            color: var(--text-strong);
            font-size: 1.85rem;
            font-weight: 700;
            line-height: 1.1;
            margin: 0;
          }

          .app-copy {
            color: var(--text-muted);
            margin-top: 0.45rem;
            margin-bottom: 0;
          }

          .path-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 0.75rem;
            margin-top: 0.5rem;
          }

          .path-card {
            background: rgba(248, 250, 252, 0.95);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            padding: 0.8rem 0.9rem;
          }

          .path-card strong {
            display: block;
            color: var(--text-strong);
            font-size: 0.88rem;
            margin-bottom: 0.25rem;
          }

          .path-card code {
            color: var(--text-muted);
            font-size: 0.8rem;
            word-break: break-all;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(*, title: str, kicker: str, copy: str) -> None:
    """Render the shared compact page header."""
    st.markdown(
        f"""
        <section class="app-shell">
          <div class="app-kicker">{kicker}</div>
          <h1 class="app-title">{title}</h1>
          <p class="app-copy">{copy}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_path_cards(rows: list[tuple[str, Path]]) -> None:
    """Render a compact path summary grid."""
    cards = "".join(
        f"<div class='path-card'><strong>{label}</strong><code>{path.as_posix()}</code></div>" for label, path in rows
    )
    st.markdown(f"<div class='path-grid'>{cards}</div>", unsafe_allow_html=True)


def render_key_value_rows(rows: list[dict[str, Any]]) -> None:
    """Render a compact key-value table."""
    st.dataframe(
        [{key: _format_table_value(value) for key, value in row.items()} for row in rows],
        width="stretch",
        hide_index=True,
    )


def _format_table_value(value: Any) -> str:
    """Return a stable string representation for display tables."""
    if value is None:
        return "n/a"
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list | tuple | dict):
        return json.dumps(value)
    return str(value)


__all__ = ["inject_styles", "render_header", "render_key_value_rows", "render_path_cards"]
