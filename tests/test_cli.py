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


def test_index_command_is_incremental(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from mide.cli import app
    from mide.rag.embeddings import FakeEmbedder

    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("mide.cli.load_embedder", lambda cfg, profile: FakeEmbedder())
    data = tmp_path / "data"
    data.mkdir()
    (data / "a.txt").write_text("hello world " * 20)
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "sources.yaml").write_text(f"sources:\n  - {data}\n")
    runner = CliRunner()
    first = runner.invoke(app, ["index", "--config-dir", str(cfg)])
    assert first.exit_code == 0, first.output
    assert "1 item(s)" in first.output
    second = runner.invoke(app, ["index", "--config-dir", str(cfg)])
    assert "0 new chunk(s)" in second.output
