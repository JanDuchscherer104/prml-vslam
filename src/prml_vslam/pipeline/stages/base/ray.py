"""Ray-specific helpers for future stage runtime deployment.

This module intentionally exposes no helper API in WP-03. Ray option
translation and task-ref tracking should be added here when a Ray-hosted
``StageRuntimeProxy`` actually uses them, keeping Ray details out of generic
runtime contracts.
"""

from __future__ import annotations

__all__: list[str] = []
