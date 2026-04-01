"""Pipeline orchestration.

**Stages**
- DataProvider: can be streaming or offline dataset; must provide RGB; can provide additional camera poses,
    and depth depth maps
- SLAMMethod: Performs SLAM in streaming or batched mode
- SceneRepr: (Optional) create 3DGS representation from SLAM output, here we can use any method from NerfStudio.
- EVAL: (Optional) Performs benchmarking (trajectory, PC, 3DGS, performance, ...)
"""

from .contracts import MethodId, RunPlan, RunPlanRequest, RunPlanStage, RunPlanStageId
from .services import PipelinePlannerService

__all__ = [
    "MethodId",
    "PipelinePlannerService",
    "RunPlan",
    "RunPlanRequest",
    "RunPlanStage",
    "RunPlanStageId",
]
