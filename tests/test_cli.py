"""CLI smoke tests."""

from __future__ import annotations

from typer.testing import CliRunner

from prml_vslam.main import app

runner = CliRunner()


def test_info_command_runs() -> None:
    result = runner.invoke(app, ["info"])

    assert result.exit_code == 0
    assert "prml-vslam" in result.stdout
