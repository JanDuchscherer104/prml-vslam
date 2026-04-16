"""Tests for the shared Pydantic base-model split."""

from __future__ import annotations

import tomllib
from enum import Enum
from pathlib import Path

import numpy as np
import pytest

from prml_vslam.utils import BaseConfig, BaseData, FactoryConfig


class RuntimeTarget:
    """Runtime object used to verify default setup behavior."""

    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config


class RuntimeConfig(BaseConfig, FactoryConfig[RuntimeTarget]):
    """Config whose runtime target is constructed via ``target_type``."""

    @property
    def target_type(self) -> type[RuntimeTarget]:
        return RuntimeTarget

    value: int = 7


class DataOnlyConfig(BaseConfig):
    """Config without a runtime target."""

    value: int = 11


class InvalidTargetConfig(BaseConfig, FactoryConfig[object]):
    """Config that exposes an invalid target_type."""

    @property
    def target_type(self) -> type[object]:
        return 42  # type: ignore[return-value]


class PlainPayload(BaseData):
    """Plain validated payload without config helper methods."""

    value: int


class SerializationMode(str, Enum):
    """Enum used to verify serialized primitive conversion."""

    READY = "ready"


class NestedPayload(BaseData):
    """Nested payload used to verify recursive normalization."""

    path: Path
    optional_note: str | None = None


class SerializableConfig(BaseConfig):
    """Config used to lock JSON and TOML serialization behavior."""

    path: Path
    mode: SerializationMode
    array: object
    scalar: object
    payload: NestedPayload
    runtime_type: type[RuntimeTarget]


class TomlConfig(BaseConfig):
    """Config used to verify TOML normalization semantics."""

    path: Path
    mode: SerializationMode
    array: object
    scalar: object
    payload: NestedPayload


def test_setup_target_constructs_runtime_from_target_type() -> None:
    config = RuntimeConfig(value=13)

    target = config.setup_target()

    assert isinstance(target, RuntimeTarget)
    assert target.config is config
    assert target.config.value == 13


def test_data_only_configs_do_not_expose_factory_helpers() -> None:
    config = DataOnlyConfig()

    assert not hasattr(config, "setup_target")


def test_setup_target_raises_for_invalid_target_type() -> None:
    config = InvalidTargetConfig()

    with pytest.raises(TypeError, match="target_type 42"):
        config.setup_target()


def test_base_data_is_distinct_from_config_helpers() -> None:
    payload = PlainPayload(value="7")

    assert payload.value == 7
    assert not isinstance(payload, BaseConfig)
    assert not hasattr(payload, "setup_target")


def test_model_dump_jsonable_preserves_recursive_json_normalization(tmp_path: Path) -> None:
    config = SerializableConfig(
        path=tmp_path / "config.json",
        mode=SerializationMode.READY,
        array=np.array([1, 2, 3]),
        scalar=np.int64(5),
        payload=NestedPayload(path=tmp_path / "nested.txt", optional_note=None),
        runtime_type=RuntimeTarget,
    )

    assert config.model_dump_jsonable() == {
        "path": (tmp_path / "config.json").as_posix(),
        "mode": "ready",
        "array": [1, 2, 3],
        "scalar": 5,
        "payload": {"path": (tmp_path / "nested.txt").as_posix(), "optional_note": None},
        "runtime_type": "RuntimeTarget",
    }


def test_to_toml_preserves_recursive_toml_normalization(tmp_path: Path) -> None:
    config = TomlConfig(
        path=tmp_path / "config.toml",
        mode=SerializationMode.READY,
        array=np.array([1, 2, 3]),
        scalar=np.float32(1.5),
        payload=NestedPayload(path=tmp_path / "nested.txt", optional_note=None),
    )

    assert tomllib.loads(config.to_toml()) == {
        "path": str(tmp_path / "config.toml"),
        "mode": "ready",
        "array": [1, 2, 3],
        "scalar": 1.5,
        "payload": {"path": str(tmp_path / "nested.txt")},
    }
