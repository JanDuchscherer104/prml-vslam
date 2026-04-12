"""Dataset-edge frame-graph helpers."""

from __future__ import annotations

from pytransform3d.transform_manager import TransformManager

from prml_vslam.interfaces import FrameTransform


class StaticFrameGraph:
    """Thin wrapper around `pytransform3d.TransformManager` for static frame composition."""

    def __init__(self) -> None:
        self._manager = TransformManager(strict_check=False)

    def add_transform(self, transform: FrameTransform) -> None:
        """Register one static transform."""
        self._manager.add_transform(transform.source_frame, transform.target_frame, transform.as_matrix())

    def compose(self, *, target_frame: str, source_frame: str) -> FrameTransform:
        """Resolve one composed transform back into the repo-owned transform DTO."""
        matrix = self._manager.get_transform(source_frame, target_frame)
        return FrameTransform.from_matrix(matrix, target_frame=target_frame, source_frame=source_frame)


__all__ = ["StaticFrameGraph"]
