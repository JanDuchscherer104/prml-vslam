"""Pipeline orchestration.

**Stages**
- DataProvider: can be streaming or offline dataset; must provide RGB; can provide additional camera poses,
    and depth depth maps
- SLAMMethod: Performs SLAM in streaming or batched mode
- SceneRepr: (Optional) create 3DGS representation from SLAM output, here we can use any method from NerfStudio.
- EVAL: (Optional) Performs benchmarking (trajectory, PC, 3DGS, performance, ...)
"""

from .contracts import (
    AlignmentMode,
    CaptureManifest,
    CaptureMetadataConfig,
    DenseArtifactMetadata,
    InsightTone,
    MaterializedWorkspace,
    MethodId,
    PipelineMode,
    RunPlan,
    RunPlanInsight,
    RunPlanRequest,
    RunPlanStage,
    RunPlanStageId,
    TimestampSource,
    TrajectoryArtifactMetadata,
    WorkspaceArtifact,
)
from .messages import (
    Envelope,
    FramePayload,
    MessageKind,
    PosePayload,
    PreviewPayload,
    make_envelope,
    pose_from_matrix,
    pose_to_matrix,
)
from .runtime.session import Session, SessionManager
from .services import PipelinePlannerService, WorkspaceMaterializerService

__all__ = [
    "AlignmentMode",
    "CaptureManifest",
    "CaptureMetadataConfig",
    "DenseArtifactMetadata",
    "Envelope",
    "FramePayload",
    "InsightTone",
    "MaterializedWorkspace",
    "MessageKind",
    "MethodId",
    "PipelineMode",
    "PipelinePlannerService",
    "PosePayload",
    "PreviewPayload",
    "RunPlan",
    "RunPlanInsight",
    "RunPlanRequest",
    "RunPlanStage",
    "RunPlanStageId",
    "Session",
    "SessionManager",
    "TimestampSource",
    "TrajectoryArtifactMetadata",
    "WorkspaceArtifact",
    "WorkspaceMaterializerService",
    "make_envelope",
    "pose_from_matrix",
    "pose_to_matrix",
]
