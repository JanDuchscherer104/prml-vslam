"""Generate repo-local Open3D stubs with Open3D's pybind11-stubgen workflow."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "typings"
OPEN3D_STUB_ROOT = OUTPUT_ROOT / "open3d"


def main() -> None:
    """Regenerate Open3D `.pyi` files under `typings/open3d`."""
    if OPEN3D_STUB_ROOT.exists():
        shutil.rmtree(OPEN3D_STUB_ROOT)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pybind11_stubgen",
            "-o",
            OUTPUT_ROOT.as_posix(),
            "--root-suffix",
            "",
            "--ignore-all-errors",
            "--numpy-array-remove-parameters",
            "open3d",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    _normalize_generated_stubs()


def _normalize_generated_stubs() -> None:
    for path in OPEN3D_STUB_ROOT.rglob("*.pyi"):
        lines = path.read_text(encoding="utf-8").splitlines()
        normalized_lines = []
        for line in lines:
            if line.strip() == "open3d =":
                continue
            normalized_lines.append(line.split("  # value = ", maxsplit=1)[0])
        path.write_text("\n".join(normalized_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
