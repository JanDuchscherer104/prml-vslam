"""Generic stage runtime DTOs for the pipeline refactor target.

These contracts describe terminal stage results, live runtime status, and
neutral visualization descriptors. They intentionally stay SDK-free and carry
only generic orchestration metadata; stage-specific semantic payloads remain
owned by their domain packages.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field, SerializeAsAny

from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.interfaces.camera import CameraIntrinsics
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.contracts.transport import TransportModel
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.utils import BaseData

JsonScalar = str | int | float | bool | None


class VisualizationIntent(StrEnum):
    """Name the neutral visualization action requested from observer sinks."""

    RGB_IMAGE = "rgb_image"
    DEPTH_IMAGE = "depth_image"
    POINT_CLOUD = "point_cloud"
    TRAJECTORY = "trajectory"
    POSE_TRANSFORM = "pose_transform"
    PINHOLE_CAMERA = "pinhole_camera"
    GROUND_PLANE = "ground_plane"
    MESH = "mesh"
    CLEAR = "clear"


class StageRuntimeStatus(TransportModel):
    """Expose queryable live status for one stage runtime.

    This DTO is the live status counterpart to durable
    :class:`prml_vslam.pipeline.contracts.events.StageOutcome`. Runtimes and
    proxies update it for queue depth, progress, latency, throughput, and
    resource assignment; summaries and manifests still derive terminal truth
    from stage outcomes. Runtime timestamps use nanoseconds so callers can
    choose monotonic or wall-clock semantics according to the emitting runtime.
    """

    model_config = ConfigDict(frozen=True)

    stage_key: StageKey
    """Stage whose runtime produced this status."""

    lifecycle_state: StageStatus = StageStatus.QUEUED
    """Current stage lifecycle state using the existing stage-status vocabulary."""

    progress_message: str = ""
    """Human-readable progress detail for operator-facing projections."""

    completed_steps: int | None = Field(default=None, ge=0)
    """Completed progress units when the runtime can measure bounded work."""

    total_steps: int | None = Field(default=None, ge=0)
    """Total progress units when the runtime can measure bounded work."""

    progress_unit: str | None = None
    """Name of the progress unit, such as ``frames`` or ``stages``."""

    queue_depth: int | None = Field(default=None, ge=0)
    """Measured runtime-owned queue or credit depth, when one exists."""

    backlog_count: int | None = Field(default=None, ge=0)
    """Measured unprocessed backlog count, when distinct from queue depth."""

    submitted_count: int = Field(default=0, ge=0)
    """Number of work items submitted to the runtime or proxy."""

    completed_count: int = Field(default=0, ge=0)
    """Number of submitted work items completed by the runtime or proxy."""

    failed_count: int = Field(default=0, ge=0)
    """Number of submitted work items that failed."""

    in_flight_count: int = Field(default=0, ge=0)
    """Number of submitted work items still in progress."""

    processed_items: int = Field(default=0, ge=0)
    """Domain-neutral count of items processed by the runtime."""

    fps: float | None = Field(default=None, ge=0.0)
    """Frame rate when the stage processes frame-like items."""

    throughput: float | None = Field(default=None, ge=0.0)
    """Generic throughput value for non-frame item streams."""

    throughput_unit: str | None = None
    """Unit label for :attr:`throughput`."""

    latency_ms: float | None = Field(default=None, ge=0.0)
    """Runtime-measured latency in milliseconds."""

    last_warning: str | None = None
    """Most recent non-fatal warning reported by the runtime."""

    last_error: str | None = None
    """Most recent error reported by the runtime."""

    executor_id: str | None = None
    """Runtime or proxy identity useful for diagnostics."""

    resource_assignment: dict[str, JsonScalar] = Field(default_factory=dict)
    """Substrate-neutral resource assignment details exposed to observers."""

    updated_at_ns: int = Field(default=0, ge=0)
    """Status update timestamp in nanoseconds."""


class VisualizationItem(TransportModel):
    """Describe one neutral sink-facing visualization item.

    The item carries semantic slots and small metadata only. It must not include
    bulk arrays, Rerun entity paths, timelines, archetypes, styling, or SDK
    command objects.
    """

    model_config = ConfigDict(frozen=True)

    intent: VisualizationIntent
    """Requested visualization action."""

    role: str = ""
    """Stage- or domain-owned role label for the item."""

    payload_refs: dict[str, TransientPayloadRef] = Field(default_factory=dict)
    """Named live payload references, keyed by semantic slot."""

    artifact_refs: dict[str, ArtifactRef] = Field(default_factory=dict)
    """Named durable artifact references, keyed by semantic slot."""

    pose: FrameTransform | None = None
    """Optional pose or transform associated with the item."""

    intrinsics: CameraIntrinsics | None = None
    """Optional pinhole intrinsics for image-like payloads."""

    frame_index: int | None = Field(default=None, ge=0)
    """Source or model frame index associated with the item."""

    keyframe_index: int | None = Field(default=None, ge=0)
    """Backend keyframe index associated with the item."""

    space: str = ""
    """Coordinate or raster space hint such as ``world`` or ``camera_local``."""

    metadata: dict[str, JsonScalar] = Field(default_factory=dict)
    """Small scalar metadata for sink policy decisions."""


class StageRuntimeUpdate(TransportModel):
    """Live observer update emitted by a running stage runtime.

    Updates are immutable, best-effort observer records. They can carry
    domain-owned semantic events, neutral visualization descriptors, and a
    status snapshot, but downstream stages must not depend on them for terminal
    inputs. Cross-stage handoff remains :class:`StageResult`.
    """

    model_config = ConfigDict(frozen=True)

    stage_key: StageKey
    """Stage whose runtime produced this update."""

    timestamp_ns: int = Field(ge=0)
    """Update timestamp in nanoseconds."""

    semantic_events: list[SerializeAsAny[BaseData]] = Field(default_factory=list)
    """Domain-owned semantic event DTOs carried without a pipeline wrapper."""

    visualizations: list[VisualizationItem] = Field(default_factory=list)
    """Neutral visualization descriptors for observer sinks."""

    runtime_status: StageRuntimeStatus | None = None
    """Optional status snapshot associated with this update."""


class StageResult(TransportModel):
    """Canonical terminal handoff bundle for one completed stage.

    Store this in :class:`prml_vslam.pipeline.runner.StageResultStore` after a
    runtime finishes. The payload is an in-memory domain object used by later
    stages, while :attr:`outcome` is the durable subset written into events,
    manifests, and summaries. Do not persist full ``StageResult`` objects as
    scientific provenance.
    """

    model_config = ConfigDict(frozen=True)

    stage_key: StageKey
    """Stage that produced the result."""

    payload: SerializeAsAny[BaseData] | None = None
    """Domain-owned payload retained in runtime state for downstream stages."""

    outcome: StageOutcome
    """Durable/provenance subset of the terminal stage result."""

    final_runtime_status: StageRuntimeStatus
    """Final live status snapshot for the stage runtime."""


__all__ = [
    "StageResult",
    "StageRuntimeStatus",
    "StageRuntimeUpdate",
    "VisualizationIntent",
    "VisualizationItem",
]
