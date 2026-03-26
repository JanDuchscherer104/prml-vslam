"""Tests for the config-as-factory helpers."""

from __future__ import annotations

import pytest

from prml_vslam.utils import BaseConfig


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
