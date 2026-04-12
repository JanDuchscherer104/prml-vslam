#!/usr/bin/env python3
"""Generate a comprehensive Rerun Blueprint (.rbl) for ViSTA-SLAM data.

Usage:
    uv run scripts/vista_rerun_viewer.py
"""

import sys
from pathlib import Path

try:
    import rerun as rr
    import rerun.blueprint as rrb
except ImportError:
    print("Error: The rerun-sdk is not installed. Please install it using `uv pip install rerun-sdk`.")
    sys.exit(1)

def build_blueprint() -> rrb.Blueprint:
    """Build a comprehensive blueprint to visualize all ViSTA-SLAM data."""
    # We create a layout that handles both the canonical prml-vslam output (camera/) 
    # and the native ViSTA output (world/est/).
    return rrb.Blueprint(
        rrb.Horizontal(
            rrb.Spatial3DView(
                origin="/",
                name="Global 3D Map",
            ),
            rrb.Vertical(
                rrb.Spatial2DView(origin="camera/preview", name="Preview (Wrapper)"),
                rrb.Spatial2DView(origin="world/est/cam_0", name="Preview (Native)"),
            ),
        ),
        rrb.TimePanel(state="expanded"),
    )

def main() -> None:
    blueprint_path = Path(".configs/visualization/vista_blueprint.rbl")
    blueprint_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating Rerun blueprint at '{blueprint_path.resolve()}'...")
    rr.init("prml-vslam")
    blueprint = build_blueprint()

    # Save the blueprint to disk
    rr.save(blueprint_path, default_blueprint=blueprint)

    print("\nBlueprint generated successfully!")
    print("To view your data with this configuration, run the Rerun CLI with both files:")
    print(f"\n    uv run rerun .artifacts/vista-full-tuning/vista/visualization/viewer_recording.rrd {blueprint_path}\n")
    print("Or to view the native ViSTA-SLAM output:")
    print(f"    uv run rerun .artifacts/vista-full-tuning/vista/native/rerun_recording.rrd {blueprint_path}\n")


if __name__ == "__main__":
    main()