"""Trajectory-alignment contracts shared by evaluation and visualization.

Trajectory alignment is a comparison artifact, not a trajectory metric result.
This module keeps alignment metadata separate from trajectory metric manifests
so stages can reuse alignment provenance without depending on metric DTOs.
"""

from __future__ import annotations

from pydantic import Field

from prml_vslam.utils import BaseData


class TrajectoryAlignmentArtifact(BaseData):
    """Persist an explicit trajectory alignment used for diagnostics or metrics."""

    source_frame: str
    """Frame of the estimate trajectory before alignment."""

    target_frame: str
    """Frame of the reference trajectory after alignment."""

    scale: float
    """Similarity scale applied to source positions."""

    rotation: list[list[float]]
    """Row-major 3x3 rotation matrix mapping source vectors into target frame."""

    translation: list[float]
    """Translation vector in target-frame meters."""

    matched_pairs: int
    """Number of associated pose pairs used to derive the transform."""

    rms_error_m: float
    """RMS positional residual after alignment, in meters."""

    reference_source: str
    """Reference trajectory source identifier used for the alignment."""

    sync_max_diff_s: float
    """Maximum timestamp association difference used for alignment."""

    method_id: str | None = None
    """Estimated trajectory method identifier, when known."""

    method_label: str | None = None
    """Human-readable estimated trajectory label, when known."""

    cloud_input_present: bool = False
    """Whether a dense cloud was available for optional downstream transform."""

    cloud_warning_reasons: list[str] = Field(default_factory=list)
    """Non-fatal reasons attached to cloud transform gating."""

    cloud_rejection_reasons: list[str] = Field(default_factory=list)
    """Fatal reasons that prevented cloud transform materialization."""

    cloud_gate_min_matched_pairs: int = 20
    """Minimum matched pose count expected before applying alignment to a cloud."""

    cloud_gate_max_rms_error_m: float = 2.0
    """Maximum alignment RMS error allowed before cloud transform warnings."""

    cloud_gate_max_up_axis_tilt_deg: float = 15.0
    """Maximum allowed up-axis tilt before cloud transform warnings."""

    up_axis_tilt_deg: float | None = None
    """Measured tilt between source and target up axes, when derivable."""


__all__ = [
    "TrajectoryAlignmentArtifact",
]
