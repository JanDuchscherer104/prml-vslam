"""ADVIO coordinate-basis normalization helpers.

ADVIO replay and benchmark surfaces use the iPhone/Pixel pose providers. Their
raw trajectories use a Y-up basis where the X/Z plane is horizontal; repository
boundaries expose them as RDF (`x` right, `y` down, `z` forward).
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from evo.tools import file_interface
from numpy.typing import NDArray

from prml_vslam.interfaces import FrameTransform
from prml_vslam.interfaces.geometry import JsonScalar
from prml_vslam.sources.contracts import ReferenceSource
from prml_vslam.sources.datasets.contracts import AdvioPoseSource
from prml_vslam.utils import BaseData


class AdvioRawCoordinateBasis(StrEnum):
    """Raw coordinate bases used by official ADVIO provider artifacts."""

    APPLE_Y_UP = "apple_y_up_xz_floor"


APPLE_Y_UP_TO_RDF: NDArray[np.float64] = np.asarray(
    [
        [0.0, 0.0, 1.0],
        [0.0, -1.0, 0.0],
        [1.0, 0.0, 0.0],
    ],
    dtype=np.float64,
)


class AdvioBasisMetadata(BaseData):
    """Persist basis conversion details for normalized ADVIO artifacts."""

    raw_coordinate_basis: AdvioRawCoordinateBasis
    rdf_basis_transform: list[list[float]]
    target_frame: str
    native_frame: str


def basis_for_pose_source(source: AdvioPoseSource | ReferenceSource) -> AdvioRawCoordinateBasis:
    """Return the raw ADVIO basis used by one provider source."""
    del source
    return AdvioRawCoordinateBasis.APPLE_Y_UP


def rdf_basis_matrix(basis: AdvioRawCoordinateBasis) -> NDArray[np.float64]:
    """Return the 3x3 raw-to-RDF basis matrix for one ADVIO raw basis."""
    match basis:
        case AdvioRawCoordinateBasis.APPLE_Y_UP:
            return APPLE_Y_UP_TO_RDF.copy()


def advio_basis_metadata(
    *,
    source: AdvioPoseSource | ReferenceSource,
    target_frame: str,
    native_frame: str,
) -> AdvioBasisMetadata:
    """Build side metadata describing one ADVIO raw-to-RDF conversion."""
    basis = basis_for_pose_source(source)
    return AdvioBasisMetadata(
        raw_coordinate_basis=basis,
        rdf_basis_transform=rdf_basis_matrix(basis).tolist(),
        target_frame=target_frame,
        native_frame=native_frame,
    )


def advio_basis_provenance(
    *,
    source: AdvioPoseSource | ReferenceSource,
    target_frame: str,
    native_frame: str,
) -> dict[str, JsonScalar]:
    """Return scalar provenance fields suitable for runtime DTO metadata."""
    metadata = advio_basis_metadata(source=source, target_frame=target_frame, native_frame=native_frame)
    return {
        "raw_coordinate_basis": metadata.raw_coordinate_basis.value,
        "rdf_basis_transform": _flatten_matrix(metadata.rdf_basis_transform),
        "target_frame": metadata.target_frame,
        "native_frame": metadata.native_frame,
    }


def transform_advio_trajectory_to_rdf(
    trajectory: PoseTrajectory3D,
    source: AdvioPoseSource | ReferenceSource,
) -> PoseTrajectory3D:
    """Convert one raw ADVIO trajectory into canonical RDF pose matrices."""
    basis = rdf_basis_matrix(basis_for_pose_source(source))
    basis_inv = np.linalg.inv(basis)
    poses_rdf = [basis @ np.asarray(pose, dtype=np.float64)[:3, :3] @ basis_inv for pose in trajectory.poses_se3]
    translations_rdf = np.asarray(trajectory.positions_xyz, dtype=np.float64) @ basis.T
    orientations_quat_wxyz = np.asarray(
        [
            FrameTransform.from_matrix(_pose_matrix(rotation, translation)).quaternion_xyzw()[[3, 0, 1, 2]]
            for rotation, translation in zip(poses_rdf, translations_rdf, strict=True)
        ],
        dtype=np.float64,
    )
    return PoseTrajectory3D(
        positions_xyz=translations_rdf,
        orientations_quat_wxyz=orientations_quat_wxyz,
        timestamps=np.asarray(trajectory.timestamps, dtype=np.float64),
    )


def write_advio_rdf_tum(
    *,
    trajectory: PoseTrajectory3D,
    source: AdvioPoseSource | ReferenceSource,
    target_path: Path,
) -> Path:
    """Write a raw ADVIO trajectory as a normalized RDF TUM artifact."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    file_interface.write_tum_trajectory_file(target_path, transform_advio_trajectory_to_rdf(trajectory, source))
    return target_path.resolve()


def _pose_matrix(rotation: NDArray[np.float64], translation: NDArray[np.float64]) -> NDArray[np.float64]:
    pose = np.eye(4, dtype=np.float64)
    pose[:3, :3] = rotation
    pose[:3, 3] = translation
    return pose


def _flatten_matrix(matrix: list[list[float]]) -> str:
    return ",".join(f"{value:.12g}" for row in matrix for value in row)
