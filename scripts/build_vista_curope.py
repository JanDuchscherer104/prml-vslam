"""Build the optional CUDA RoPE2D extension for the bundled ViSTA-SLAM checkout."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CUROPE_DIR = PROJECT_ROOT / "external" / "vista-slam" / "vista_slam" / "sta_model" / "pos_embed" / "curope"


def main() -> None:
    """Build ViSTA-SLAM's optional cuRoPE2D extension in-place."""
    cuda_home = _resolve_cuda_home()
    env = os.environ.copy()
    env["CUDA_HOME"] = str(cuda_home)
    env["PATH"] = _prepend_path(cuda_home / "bin", env.get("PATH", ""))
    env["LD_LIBRARY_PATH"] = _prepend_existing_paths(
        (cuda_home / "lib64", cuda_home / "lib"),
        env.get("LD_LIBRARY_PATH", ""),
    )
    _ensure_setup_file()
    subprocess.run(
        [sys.executable, "setup.py", "build_ext", "--inplace"],
        cwd=CUROPE_DIR,
        env=env,
        check=True,
    )


def _resolve_cuda_home() -> Path:
    candidates = [
        os.environ.get("CUDA_HOME"),
        os.environ.get("CONDA_PREFIX"),
        "/usr/local/cuda",
    ]
    for raw_candidate in candidates:
        if not raw_candidate:
            continue
        candidate = Path(raw_candidate).expanduser().resolve()
        if _has_nvcc(candidate):
            return candidate
    raise SystemExit(
        "Could not find CUDA_HOME for building cuRoPE2D. Install the conda CUDA compiler packages "
        "from environment.yml, activate the prml-vslam env, and run this script through `uv run --extra vista`."
    )


def _has_nvcc(cuda_home: Path) -> bool:
    return (cuda_home / "bin" / "nvcc").exists()


def _ensure_setup_file() -> None:
    setup_path = CUROPE_DIR / "setup.py"
    if not setup_path.exists():
        raise SystemExit(f"Missing ViSTA cuRoPE setup file: {setup_path}")


def _prepend_path(path: Path, existing: str) -> str:
    return f"{path}{os.pathsep}{existing}" if existing else str(path)


def _prepend_existing_paths(paths: tuple[Path, ...], existing: str) -> str:
    resolved_paths = [str(path) for path in paths if path.exists()]
    if existing:
        resolved_paths.append(existing)
    return os.pathsep.join(resolved_paths)


if __name__ == "__main__":
    main()
