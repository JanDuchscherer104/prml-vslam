"""Import smoke tests for the scaffold package."""

from __future__ import annotations

from pydantic import Field


def test_package_imports() -> None:
    import prml_vslam
    import prml_vslam.app
    import prml_vslam.eval
    import prml_vslam.io
    import prml_vslam.methods
    import prml_vslam.pipeline
    import prml_vslam.utils
    from prml_vslam.utils import BaseConfig, get_console

    assert prml_vslam.__version__

    class SmokeConfig(BaseConfig[int]):
        @property
        def target(self) -> int:
            return 42

        some_field: int = 42
        another_field: dict[str, int] = Field(default_factory=lambda: {"a": 42, "b": 37})

    config = SmokeConfig()
    config.inspect()

    console = get_console()
    console.log(config)
