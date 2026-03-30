"""Streamlit workbench tests."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


def _find_text_input(at: AppTest, label: str):
    for widget in at.text_input:
        if widget.label == label:
            return widget
    raise AssertionError(f"Could not find text input with label {label!r}")


def _find_button(at: AppTest, label: str):
    for widget in at.button:
        if widget.label == label:
            return widget
    raise AssertionError(f"Could not find button with label {label!r}")


def test_streamlit_workbench_renders_main_sections() -> None:
    at = AppTest.from_file("streamlit_app.py")

    at.run()

    assert any("PRML VSLAM Workbench" in markdown.value for markdown in at.markdown)
    assert any("Batch-first planning" in markdown.value for markdown in at.markdown)
    assert any("Materialize workspace" == button.label for button in at.button)


def test_streamlit_workbench_materializes_a_workspace(tmp_path: Path) -> None:
    at = AppTest.from_file("streamlit_app.py")

    at.run()
    _find_text_input(at, "Experiment name").set_value("Studio Sweep").run()
    _find_text_input(at, "Video path").set_value("captures/studio.mp4").run()
    _find_text_input(at, "Output directory").set_value(str(tmp_path / "artifacts")).run()
    _find_button(at, "Materialize workspace").click().run()

    artifact_root = tmp_path / "artifacts" / "studio-sweep" / "batch" / "vista_slam"
    assert (artifact_root / "input" / "capture_manifest.json").exists()
    assert any("Materialized workspace" in success.value for success in at.success)
