"""Packaged Streamlit entrypoint for the PRML VSLAM workbench."""

from __future__ import annotations

from typing import Any

import streamlit as st

from prml_vslam.io import Record3DWiFiViewerState, render_record3d_wifi_viewer


def _coerce_matrix_rows(matrix: Any) -> list[list[float]] | None:
    """Normalize supported matrix payloads into row-major numeric rows."""
    if isinstance(matrix, list) and len(matrix) == 9 and all(isinstance(value, int | float) for value in matrix):
        return [
            [float(matrix[0]), float(matrix[1]), float(matrix[2])],
            [float(matrix[3]), float(matrix[4]), float(matrix[5])],
            [float(matrix[6]), float(matrix[7]), float(matrix[8])],
        ]

    if (
        isinstance(matrix, list)
        and len(matrix) == 3
        and all(isinstance(row, list) and len(row) == 3 for row in matrix)
        and all(isinstance(value, int | float) for row in matrix for value in row)
    ):
        return [[float(value) for value in row] for row in matrix]

    return None


def _matrix_to_markdown_latex(name: str, matrix: list[list[float]]) -> str:
    """Render a matrix as Markdown-hosted LaTeX."""
    rows = r" \\ ".join(" & ".join(f"{value:.3f}" for value in row) for row in matrix)
    return rf"$$ {name} = \begin{{bmatrix}} {rows} \end{{bmatrix}} $$"


def _render_intrinsics(viewer_state: Record3DWiFiViewerState) -> None:
    """Render the camera intrinsic matrix when available."""
    matrix_rows = _coerce_matrix_rows(viewer_state.metadata.get("K"))
    if matrix_rows is None:
        return

    st.subheader("Camera Intrinsics")
    st.markdown(_matrix_to_markdown_latex("K", matrix_rows))


def run_app() -> None:
    """Render the Streamlit workbench with the Record3D Wi-Fi viewer."""
    st.set_page_config(page_title="PRML VSLAM Workbench", layout="wide")
    st.title("PRML VSLAM Workbench")
    st.caption("Live inspection surface for Record3D Wi-Fi streaming and future benchmarking tools.")
    st.subheader("Record3D Wi-Fi")
    st.markdown(
        """
        Use the browser-side viewer below to connect to the Record3D Wi-Fi stream from the same local network.
        This path is display-only: it previews the composite RGBD video plus metadata, but it does not feed the
        Python pipeline yet.
        """
    )
    st.markdown(
        """
        Chrome and Safari are the supported browsers for this flow. Record3D allows only one Wi-Fi receiver at a
        time, and the Wi-Fi stream is lower fidelity than the USB Python integration.
        """
    )

    viewer_state = render_record3d_wifi_viewer()
    _render_intrinsics(viewer_state)
