"""CLI smoke tests."""

from __future__ import annotations

from typer.testing import CliRunner

from prml_vslam.main import Record3DStreamConfig, app

runner = CliRunner()


def test_info_command_runs() -> None:
    result = runner.invoke(app, ["info"])

    assert result.exit_code == 0
    assert "prml-vslam" in result.stdout


def test_record3d_devices_command_runs(monkeypatch) -> None:
    class FakeDevice:
        def __init__(self, product_id: int, udid: str) -> None:
            self.product_id = product_id
            self.udid = udid

        def model_dump(self, *, mode: str) -> dict[str, object]:
            return {"product_id": self.product_id, "udid": self.udid, "mode": mode}

    class FakeSession:
        def list_devices(self) -> list[FakeDevice]:
            return [FakeDevice(product_id=42, udid="device-42")]

    monkeypatch.setattr(Record3DStreamConfig, "setup_target", lambda self: FakeSession())

    result = runner.invoke(app, ["record3d-devices"])

    assert result.exit_code == 0
    assert "device-42" in result.stdout
