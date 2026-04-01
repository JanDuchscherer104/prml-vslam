"""Public pipeline surface used by the CLI, runtime, and app layers."""

import importlib

from .contracts import (
    CaptureManifest,
    CaptureMetadataConfig,
    MaterializedWorkspace,
    MethodId,
    PipelineMode,
    RunPlan,
    RunPlanRequest,
    RunPlanStage,
    RunPlanStageId,
    TimestampSource,
)
from .services import PipelinePlannerService, WorkspaceMaterializerService

__all__ = [
    "CaptureManifest",
    "CaptureMetadataConfig",
    "MaterializedWorkspace",
    "MethodId",
    "PipelineMode",
    "PipelinePlannerService",
    "RunPlan",
    "RunPlanRequest",
    "RunPlanStage",
    "RunPlanStageId",
    "TimestampSource",
    "WorkspaceMaterializerService",
]

try:  # pragma: no cover - optional runtime surface missing in some partial checkouts
    _messages = importlib.import_module(f"{__name__}.messages")

    Envelope = _messages.Envelope
    FramePayload = _messages.FramePayload
    MessageKind = _messages.MessageKind
    PosePayload = _messages.PosePayload
    PreviewPayload = _messages.PreviewPayload
    make_envelope = _messages.make_envelope
    pose_from_matrix = _messages.pose_from_matrix
    pose_to_matrix = _messages.pose_to_matrix

    __all__.extend(
        [
            "Envelope",
            "FramePayload",
            "MessageKind",
            "PosePayload",
            "PreviewPayload",
            "make_envelope",
            "pose_from_matrix",
            "pose_to_matrix",
        ]
    )
except ModuleNotFoundError:
    pass

try:  # pragma: no cover - optional runtime surface missing in some partial checkouts
    _session_module = importlib.import_module(f"{__name__}.runtime.session")

    Session = _session_module.Session
    SessionManager = _session_module.SessionManager

    __all__.extend(["Session", "SessionManager"])
except ModuleNotFoundError:
    pass
