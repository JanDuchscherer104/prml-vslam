#!/usr/bin/env python3
"""Generate the committed Rerun blueprint for ViSTA-SLAM data.

Usage:
    uv run scripts/vista_rerun_viewer.py
"""

import sys
from pathlib import Path

try:
    import rerun as rr

    from prml_vslam.visualization.rerun import build_default_blueprint
except ImportError:
    print("Error: The rerun-sdk is not installed. Please install it using `uv pip install rerun-sdk`.")
    sys.exit(1)


def main() -> None:
    blueprint_path = Path(".configs/visualization/vista_blueprint.rbl")
    blueprint_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating Rerun blueprint at '{blueprint_path.resolve()}'...")
    rr.init("prml-vslam-blueprint")
    blueprint = build_default_blueprint()

    rr.save(blueprint_path, default_blueprint=blueprint)

    print("\nBlueprint generated successfully!")
    print("To view repo-owned Rerun data with this configuration, run:")
    print(
        f"\n    uv run rerun .artifacts/vista-full-tuning/vista/visualization/viewer_recording.rrd {blueprint_path}\n"
    )


if __name__ == "__main__":
    main()
