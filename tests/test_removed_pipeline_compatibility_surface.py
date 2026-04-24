"""Regression checks for removed pipeline compatibility surfaces."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCAN_ROOTS = ("src/prml_vslam", "docs", ".configs")
_SUFFIXES = {".py", ".md", ".toml", ".mmd", ".svg"}
_REMOVED_TOKENS = (
    "Run" + "Request",
    "Source" + "Spec",
    "Stage" + "Runtime" + "Proxy",
    "Stage" + "Binding",
    "STAGE_" + "BINDINGS",
    "stage_" + "binding_for",
    "evaluate." + "efficiency",
    "methods." + "config_" + "contracts",
    "methods." + "options",
    "methods." + "descriptors",
    "Backend" + "Descriptor",
    "Backend" + "Capabilities",
    "Mast3r" + "Slam" + "Backend" + "Options",
    "Vista" + "Slam" + "Backend" + "Options",
    "Slam" + "Frame" + "Input",
    "Source" + "Runtime" + "Config" + "Input",
    "Pipeline" + "Telemetry" + "Sample",
    "Open3d" + "Tsdf" + "Reconstruction" + "Config",
    "class " + "Alignment" + "Config",
    "Pose" + "Estimated",
    "Keyframe" + "Accepted",
    "Map" + "Stats" + "Updated",
    "Backend" + "Warning",
    "Backend" + "Error",
    "Session" + "Closed",
)
_REMOVED_PATH_FRAGMENTS = (
    "pipeline.stages." + "source",
    "pipeline.stages." + "slam",
    "pipeline.stages." + "ground_alignment",
    "pipeline.stages." + "trajectory_eval",
    "pipeline.stages." + "reconstruction",
    "pipeline.stages." + "cloud_eval",
    "pipeline.sinks." + "rerun",
)


def test_removed_pipeline_compatibility_names_stay_deleted() -> None:
    violations: list[str] = []
    for relative_root in _SCAN_ROOTS:
        for path in (_ROOT / relative_root).rglob("*"):
            if not path.is_file() or path.suffix not in _SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for token in (*_REMOVED_TOKENS, *_REMOVED_PATH_FRAGMENTS):
                if token in text:
                    violations.append(f"{path.relative_to(_ROOT)}: {token}")

    assert violations == []
