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
    assert "Aucune source autorisée. Utilisez `mide sources add`." in result.output


def test_no_sources_hint_follows_language(tmp_path) -> None:
    # scan / index / auto answer in the configured language when no source is authorized.
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    args = ["--config-dir", str(cfg)]
    for command in ("scan", "index", "auto"):
        result = runner.invoke(app, [command, *args])
        assert result.exit_code == 0, command
        assert "Aucune source autorisée. Utilisez `mide sources add`." in result.output, command
    (cfg / "default.yaml").write_text("language: en\n", encoding="utf-8")
    for command in ("scan", "index", "auto"):
        result = runner.invoke(app, [command, *args])
        assert result.exit_code == 0, command
        assert "No authorized sources. Use `mide sources add`." in result.output, command


def test_ui_help_shows_install_extra() -> None:
    # Rich markup must not swallow the "[ui]" extra in the install hint.
    result = runner.invoke(app, ["ui", "--help"], env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "mide-engine[ui]" in result.output
    assert "\\[ui]" not in result.output


def test_auto_without_rag_extra_still_retrains(tmp_path, monkeypatch) -> None:
    # Without sentence-transformers, `mide auto` skips indexing but still retrains.
    from mide import cli
    from mide.rag.embeddings import EmbeddingError

    data = tmp_path / "data"
    data.mkdir()
    (data / "sales.csv").write_text("x,amount\n1,2\n2,4\n", encoding="utf-8")
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    assert runner.invoke(app, ["sources", "add", str(data), "--config-dir", str(cfg)]).exit_code == 0

    def no_embedder(_cfg):
        raise EmbeddingError("sentence-transformers is not installed.")

    calls: list[dict] = []
    monkeypatch.setattr(cli, "_get_embedder", no_embedder)
    monkeypatch.setattr(cli, "retrain_if_changed", lambda datasets, *a, **k: calls.append(datasets) or [])
    result = runner.invoke(app, ["auto", "--config-dir", str(cfg)])
    assert result.exit_code == 0, result.output
    assert "Index: skipped (sentence-transformers is not installed)." in result.output
    assert len(calls) == 1 and any("sales.csv" in key for key in calls[0])
    assert "No trained models" in result.output
