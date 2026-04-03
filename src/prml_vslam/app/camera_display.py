"""Shared camera-display helpers for Streamlit pages."""

from __future__ import annotations


def format_camera_intrinsics_latex(*, fx: float, fy: float, cx: float, cy: float) -> str:
    """Build the canonical LaTeX camera-intrinsics matrix display."""
    return (
        "K = \\begin{bmatrix}"
        f"{fx:.3f} & 0.000 & {cx:.3f} \\\\ "
        f"0.000 & {fy:.3f} & {cy:.3f} \\\\ "
        "0.000 & 0.000 & 1.000"
        "\\end{bmatrix}"
    )


__all__ = ["format_camera_intrinsics_latex"]
