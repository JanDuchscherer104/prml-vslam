"""Registry of stage-owned runtime specs."""

from __future__ import annotations

from prml_vslam.alignment.stage.spec import GROUND_ALIGNMENT_STAGE_SPEC
from prml_vslam.eval.stage_cloud.spec import CLOUD_EVALUATION_STAGE_SPEC
from prml_vslam.eval.stage_trajectory.spec import TRAJECTORY_EVALUATION_STAGE_SPEC
from prml_vslam.methods.stage.spec import SLAM_STAGE_SPEC
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.spec import StageRuntimeSpec
from prml_vslam.pipeline.stages.summary.spec import SUMMARY_STAGE_SPEC
from prml_vslam.reconstruction.stage.spec import RECONSTRUCTION_STAGE_SPEC
from prml_vslam.sources.stage.spec import SOURCE_STAGE_SPEC

STAGE_RUNTIME_SPECS: dict[StageKey, StageRuntimeSpec] = {
    StageKey.SOURCE: SOURCE_STAGE_SPEC,
    StageKey.SLAM: SLAM_STAGE_SPEC,
    StageKey.GRAVITY_ALIGNMENT: GROUND_ALIGNMENT_STAGE_SPEC,
    StageKey.TRAJECTORY_EVALUATION: TRAJECTORY_EVALUATION_STAGE_SPEC,
    StageKey.RECONSTRUCTION: RECONSTRUCTION_STAGE_SPEC,
    StageKey.CLOUD_EVALUATION: CLOUD_EVALUATION_STAGE_SPEC,
    StageKey.SUMMARY: SUMMARY_STAGE_SPEC,
}


def stage_runtime_spec_for(stage_key: StageKey) -> StageRuntimeSpec:
    """Return the registered runtime spec for ``stage_key``."""
    try:
        return STAGE_RUNTIME_SPECS[stage_key]
    except KeyError as exc:
        raise RuntimeError(f"No runtime spec registered for stage '{stage_key.value}'.") from exc


__all__ = ["STAGE_RUNTIME_SPECS", "stage_runtime_spec_for"]
