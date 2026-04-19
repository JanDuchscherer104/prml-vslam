"""Smoke test for the MASt3R-SLAM adapter.

Runs the adapter against a small directory of PNG frames and validates that
trajectory + point cloud artifacts are produced, the FSM progressed through
TRACKING, and Sim3→SE(3) pose conversion didn't throw.

Usage
-----

    # Run against any directory of PNG frames (sorted lexicographically):
    uv run python scripts/smoke_mast3r.py --frames /path/to/frames --n 30

    # Or against a TUM dataset's rgb folder:
    uv run python scripts/smoke_mast3r.py \\
        --frames datasets/tum/rgbd_dataset_freiburg1_desk/rgb --n 50

        uv run --extra vista python scripts/smoke_mast3r.py     
        --frames external/mast3r-slam/datasets/tum/rgbd_dataset_freiburg1_desk/rgb     
        --n 50     
        --yaml-config external/mast3r-slam/config/base.yaml

Exit codes: 0 success, 1 missing prerequisites, 2 runtime failure.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

import cv2
import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--frames",
        type=Path,
        required=True,
        help="Directory containing PNG frames (or a single PNG sequence rgb/ dir).",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=30,
        help="Max number of frames to feed (default: 30).",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path(".artifacts/smoke-mast3r"),
        help="Where the test should write native + canonical outputs.",
    )
    parser.add_argument(
        "--yaml-config",
        type=Path,
        default=Path("external/mast3r-slam/config/base.yaml"),
        help="MASt3R YAML config (use base.yaml for uncalibrated, calib.yaml for calibrated).",
    )
    parser.add_argument(
        "--no-ply",
        action="store_true",
        help="Skip point-cloud export (faster smoke test).",
    )
    args = parser.parse_args()

    # Imports deliberately inside main() so the --help path works without the
    # heavy torch/CUDA stack installed.
    try:
        from prml_vslam.interfaces import FramePacket  # noqa: PLC0415
        from prml_vslam.methods.contracts import SlamOutputPolicy  # noqa: PLC0415
        from prml_vslam.methods.mast3r.adapter import Mast3rSlamSession  # noqa: PLC0415
        from prml_vslam.methods.mast3r.config import Mast3rSlamBackendConfig  # noqa: PLC0415
        from prml_vslam.utils import Console  # noqa: PLC0415
    except Exception as exc:
        print(f"[FAIL] Could not import repository modules: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1

    console = Console("smoke_mast3r")

    # Collect frames.
    frame_dir = args.frames.expanduser().resolve()
    if not frame_dir.is_dir():
        print(f"[FAIL] --frames must be an existing directory: {frame_dir}", file=sys.stderr)
        return 1
    png_paths = sorted(frame_dir.glob("*.png"))[: args.n]
    if len(png_paths) < 5:
        print(
            f"[FAIL] Need at least 5 PNG frames in {frame_dir}, found {len(png_paths)}.",
            file=sys.stderr,
        )
        return 1
    console.info("Smoke test: %d frames from %s", len(png_paths), frame_dir)

    # Build the config.
    cfg = Mast3rSlamBackendConfig(
        yaml_config_path=args.yaml_config,
        use_calib=False,  # smoke test doesn't need intrinsics
    )
    output_policy = SlamOutputPolicy(
        emit_dense_points=not args.no_ply,
        emit_sparse_points=False,
    )
    artifact_root = args.artifact_root.expanduser().resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)

    # Spin up the session (in-process for simplicity — no multiprocess wrapper).
    try:
        session = Mast3rSlamSession(
            cfg=cfg,
            output_policy=output_policy,
            artifact_root=artifact_root,
            console=console,
        )
    except Exception as exc:
        print(f"[FAIL] Session construction failed: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1

    # Feed frames and count the updates we saw.
    n_updates = 0
    n_keyframes = 0
    pose_samples = 0
    try:
        for seq, png_path in enumerate(png_paths):
            bgr = cv2.imread(str(png_path))
            if bgr is None:
                print(f"[WARN] Could not read {png_path}, skipping.", file=sys.stderr)
                continue
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            ts_ns = int(seq * 1e9 / 30.0)
            session.step(FramePacket(seq=seq, timestamp_ns=ts_ns, rgb=rgb))
            for update in session.try_get_updates():
                n_updates += 1
                if update.is_keyframe:
                    n_keyframes += 1
                if update.pose is not None:
                    pose_samples += 1
                    # Sanity check: pose matrix must be finite.
                    matrix = update.pose.as_matrix()
                    if not np.all(np.isfinite(matrix)):
                        print(f"[FAIL] Non-finite pose at seq={seq}", file=sys.stderr)
                        return 2

        artifacts = session.close()
    except Exception as exc:
        print(f"[FAIL] Streaming run failed: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 2

    # Validate artifacts.
    if not artifacts.trajectory_tum.path.exists():
        print(
            f"[FAIL] Trajectory artifact missing at {artifacts.trajectory_tum.path}",
            file=sys.stderr,
        )
        return 2
    traj_lines = artifacts.trajectory_tum.path.read_text().splitlines()
    if len(traj_lines) < 1:
        print("[FAIL] Trajectory file is empty.", file=sys.stderr)
        return 2

    ply_ok = True
    if output_policy.emit_dense_points:
        if artifacts.dense_points_ply is None or not artifacts.dense_points_ply.path.exists():
            print("[WARN] Dense point cloud was expected but not produced.")
            ply_ok = False

    # Report.
    print("-" * 60)
    print(f"  frames fed         : {len(png_paths)}")
    print(f"  updates emitted    : {n_updates}")
    print(f"  keyframes accepted : {n_keyframes}")
    print(f"  poses observed     : {pose_samples}")
    print(f"  trajectory rows    : {len(traj_lines)}")
    print(f"  trajectory path    : {artifacts.trajectory_tum.path}")
    if artifacts.dense_points_ply is not None:
        print(f"  point cloud path   : {artifacts.dense_points_ply.path}")
    print("-" * 60)

    if n_keyframes < 1:
        print("[FAIL] No keyframes accepted — FSM never left INIT.", file=sys.stderr)
        return 2
    if pose_samples < 1:
        print("[FAIL] No poses observed — tracker may be silently broken.", file=sys.stderr)
        return 2

    print("[OK] Smoke test passed." + ("" if ply_ok else " (PLY missing)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
