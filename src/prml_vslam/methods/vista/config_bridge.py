"""Bridge canonical repo inputs into ViSTA-SLAM CLI arguments."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.methods.contracts import SlamBackendConfig, SlamOutputPolicy
from prml_vslam.pipeline.contracts.sequence import SequenceManifest


def build_vista_command(
    *,
    python_executable: str,
    repo_dir: Path,
    sequence_manifest: SequenceManifest,
    backend_config: SlamBackendConfig,
    output_policy: SlamOutputPolicy,
    output_dir: Path,
) -> list[str]:
    """Build the thin offline ViSTA invocation from canonical repo inputs."""
    if sequence_manifest.rgb_dir is None:
        raise ValueError("ViSTA-SLAM offline execution requires `sequence_manifest.rgb_dir`.")
    command = [
        python_executable,
        str((repo_dir / "run.py").resolve()),
        "--input_dir",
        str(sequence_manifest.rgb_dir),
        "--output_dir",
        str(output_dir),
    ]
    if backend_config.config_path is not None:
        command.extend(["--config", str(backend_config.config_path)])
    if backend_config.max_frames is not None:
        command.extend(["--max_frames", str(backend_config.max_frames)])
    if not output_policy.emit_dense_points:
        command.append("--disable_dense_export")
    if not output_policy.emit_sparse_points:
        command.append("--disable_sparse_export")
    return command


__all__ = ["build_vista_command"]
