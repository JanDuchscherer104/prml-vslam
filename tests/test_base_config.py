"""Tests for the shared Pydantic base-model split."""

from __future__ import annotations

import pytest

from prml_vslam.app.models import AppState
from prml_vslam.eval.interfaces import EvaluationControls, MetricStats
from prml_vslam.pipeline.contracts import RunPlan, RunRequest
from prml_vslam.utils import BaseConfig, BaseData


class RuntimeTarget:
    """Runtime object used to verify default setup behavior."""

    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config


class RuntimeConfig(BaseConfig):
    """Config whose runtime target is constructed via ``target_type``."""

    @property
    def target_type(self) -> type[RuntimeTarget]:
        return RuntimeTarget

    value: int = 7


class DataOnlyConfig(BaseConfig):
    """Config without a runtime target."""

    value: int = 11


class InvalidTargetConfig(BaseConfig):
    """Config that exposes an invalid target_type."""

    @property
    def target_type(self) -> type[object]:
        return 42  # type: ignore[return-value]


class PlainPayload(BaseData):
    """Plain validated payload without config helper methods."""

    value: int


def test_setup_target_constructs_runtime_from_target_type() -> None:
    config = RuntimeConfig(value=13)

    target = config.setup_target()

    assert isinstance(target, RuntimeTarget)
    assert target.config is config
    assert target.config.value == 13


def test_setup_target_returns_none_for_data_only_configs() -> None:
    config = DataOnlyConfig()

    assert config.setup_target() is None


def test_setup_target_raises_for_invalid_target_type() -> None:
    config = InvalidTargetConfig()

    with pytest.raises(TypeError, match="target_type 42"):
        config.setup_target()


def test_base_data_is_distinct_from_config_helpers() -> None:
    payload = PlainPayload(value="7")

    assert payload.value == 7
    assert not isinstance(payload, BaseConfig)
    assert not hasattr(payload, "setup_target")


def test_repo_models_separate_config_and_data_bases() -> None:
    assert issubclass(EvaluationControls, BaseConfig)
    assert issubclass(RunRequest, BaseConfig)
    assert not issubclass(AppState, BaseConfig)
    assert not issubclass(MetricStats, BaseConfig)
    assert not issubclass(RunPlan, BaseConfig)
    assert issubclass(AppState, BaseData)
    assert issubclass(MetricStats, BaseData)
    assert issubclass(RunPlan, BaseData)
