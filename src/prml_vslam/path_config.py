"""Application and dataset path configuration for PRML VSLAM.

This module provides the typed path contract used by the Streamlit app and any
other repo surface that needs machine-local defaults for dataset and artifact
locations.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Self

from pydantic import model_validator

from prml_vslam.utils import BaseConfig


def _default_repo_root() -> Path:
    """Return the repository root inferred from this module path."""
    return Path(__file__).resolve().parents[2]


class PathConfig(BaseConfig):
    """Typed path owner for repo-local datasets and artifacts."""

    repo_root: Path = _default_repo_root()
    """Repository root used to derive default local paths."""

    data_root: Path = _default_repo_root() / "data"
    """Default root that stores repo-local datasets."""

    artifacts_root: Path = _default_repo_root() / "artifacts"
    """Default root that stores repo-owned pipeline and evaluation artifacts."""

    advio_root: Path = _default_repo_root() / "data" / "advio"
    """Default root that stores extracted ADVIO sequences and calibration files."""

    @model_validator(mode="before")
    @classmethod
    def derive_defaults(cls, data: Any) -> Any:
        """Derive related paths from ``repo_root`` unless set explicitly."""
        if data is None:
            data = {}
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        repo_root = Path(payload.get("repo_root", _default_repo_root())).expanduser()
        data_root = Path(payload.get("data_root", repo_root / "data")).expanduser()
        artifacts_root = Path(payload.get("artifacts_root", repo_root / "artifacts")).expanduser()
        advio_root = Path(payload.get("advio_root", data_root / "advio")).expanduser()

        payload["repo_root"] = repo_root
        payload["data_root"] = data_root
        payload["artifacts_root"] = artifacts_root
        payload["advio_root"] = advio_root
        return payload

    @classmethod
    def load(cls) -> Self:
        """Load paths from environment variables with repo-local fallbacks."""
        payload: dict[str, Path] = {}
        for field_name in ("repo_root", "data_root", "artifacts_root", "advio_root"):
            env_name = f"PRML_VSLAM_{field_name.upper()}"
            raw_value = os.getenv(env_name)
            if raw_value:
                payload[field_name] = Path(raw_value).expanduser()
        return cls.model_validate(payload)


__all__ = ["PathConfig"]
