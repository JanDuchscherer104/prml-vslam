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
    from prml_vslam.io import Record3DWiFiViewerState, render_record3d_wifi_viewer
    from prml_vslam.utils import BaseConfig, get_console

    assert prml_vslam.__version__
    assert Record3DWiFiViewerState().connection_state == "idle"
    assert callable(render_record3d_wifi_viewer)

    class SmokeConfig(BaseConfig):
        @property
        def target_type(self) -> type[SmokeTarget]:
            return SmokeTarget

        some_field: int = 42
        another_field: dict[str, int] = Field(default_factory=lambda: {"a": 42, "b": 37})

    class SmokeTarget:
        def __init__(self, config: SmokeConfig) -> None:
            self.config = config

    config = SmokeConfig()
    config.inspect()
    target = config.setup_target()

    console = get_console()
    console.plog(config)
    assert isinstance(target, SmokeTarget)
