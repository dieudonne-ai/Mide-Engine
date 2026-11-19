from typer.testing import CliRunner

from mide import __version__
from mide.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_doctor_ok() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_auto_no_sources(tmp_path):
    from typer.testing import CliRunner

    from mide.cli import app

    cfg = tmp_path / "cfg"
    cfg.mkdir()
    result = CliRunner().invoke(app, ["auto", "--config-dir", str(cfg)])
    assert result.exit_code == 0
    assert "No authorized sources" in result.output


def test_ui_help_shows_install_extra() -> None:
    # Rich markup must not swallow the "[ui]" extra in the install hint.
    result = runner.invoke(app, ["ui", "--help"], env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "mide-engine[ui]" in result.output
    assert "\\[ui]" not in result.output
