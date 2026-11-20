"""Tests for the connector interface, authorization and `mide sources`."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mide.cli import app
from mide.connectors.base import (
    BaseConnector,
    SourceNotAuthorizedError,
    ensure_authorized,
    is_authorized,
)
from mide.connectors.sources import add_source, list_sources, remove_source

runner = CliRunner()


class DummyConnector(BaseConnector):
    def discover(self) -> list[str]:
        return [self.source]

    def read(self, item: str) -> str:
        return "data"

    def metadata(self, item: str) -> dict:
        return {"name": item}


def test_file_outside_sources_is_refused(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "secret.csv"
    outside.write_text("a,b\n1,2\n")
    assert not is_authorized(outside, [str(allowed)])
    with pytest.raises(SourceNotAuthorizedError):
        ensure_authorized(outside, [str(allowed)])
    with pytest.raises(SourceNotAuthorizedError):
        DummyConnector(str(outside), [str(allowed)])


def test_file_inside_authorized_folder_is_accepted(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    f = allowed / "sales.csv"
    f.write_text("x")
    conn = DummyConnector(str(f), [str(allowed)])
    assert conn.read(str(f)) == "data"


def test_dotdot_and_symlink_escape_refused(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    (tmp_path / "other.txt").write_text("x")
    assert not is_authorized(allowed / ".." / "other.txt", [str(allowed)])
    link = allowed / "link.txt"
    link.symlink_to(tmp_path / "other.txt")
    assert not is_authorized(link, [str(allowed)])


def test_sibling_prefix_folder_not_authorized(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data2").mkdir()
    assert not is_authorized(tmp_path / "data2", [str(tmp_path / "data")])


def test_sql_url_must_match_exactly() -> None:
    url = "sqlite:///tmp/x.db"
    assert is_authorized(url, [url])
    assert not is_authorized("sqlite:///tmp/y.db", [url])


def test_add_list_remove(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg"
    data = tmp_path / "data"
    data.mkdir()
    assert list_sources(cfg) == []
    value = add_source(str(data), cfg)
    add_source(str(data), cfg)  # idempotent
    assert list_sources(cfg) == [value]
    assert remove_source(str(data), cfg)
    assert not remove_source(str(data), cfg)
    assert list_sources(cfg) == []


def test_add_rejects_missing_path_and_inline_password(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        add_source(str(tmp_path / "nope"), tmp_path)
    with pytest.raises(ValueError):
        add_source("postgresql://user:secret@host/db", tmp_path)
    add_source("postgresql://user@host/db", tmp_path)
    assert list_sources(tmp_path) == ["postgresql://user@host/db"]


def test_add_rejects_missing_sqlite_database_without_creating_it(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    missing = tmp_path / "typo.db"
    with pytest.raises(FileNotFoundError):
        add_source(f"sqlite:///{missing}", cfg)
    assert not missing.exists()
    assert list_sources(cfg) == []
    for language, expected in (("fr", "le chemin n'existe pas"), ("en", "path does not exist")):
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        res = runner.invoke(app, ["sources", "add", f"sqlite:///{missing}", "--config-dir", str(cfg)])
        assert res.exit_code == 1 and expected in res.output
    assert not missing.exists()
    missing.touch()
    assert add_source(f"sqlite:///{missing}", cfg) == f"sqlite:///{missing}"


def test_cli_sources_roundtrip(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg"
    data = tmp_path / "data"
    data.mkdir()
    args = ["--config-dir", str(cfg)]
    assert "Aucune source autorisée." in runner.invoke(app, ["sources", "list", *args]).output
    res = runner.invoke(app, ["sources", "add", str(data), *args])
    assert res.exit_code == 0
    assert str(data.resolve()) in runner.invoke(app, ["sources", "list", *args]).output
    assert runner.invoke(app, ["sources", "remove", str(data), *args]).exit_code == 0
    assert runner.invoke(app, ["sources", "remove", str(data), *args]).exit_code == 1
    assert runner.invoke(app, ["sources", "add", str(tmp_path / "x"), *args]).exit_code == 1


def test_cli_sources_remove_unknown_lists_sources(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg"
    data = tmp_path / "data"
    data.mkdir()
    args = ["--config-dir", str(cfg)]
    res = runner.invoke(app, ["sources", "remove", str(tmp_path / "nope"), *args])
    assert res.exit_code == 1
    assert "Aucune source autorisée." in res.output
    runner.invoke(app, ["sources", "add", str(data), *args])
    res = runner.invoke(app, ["sources", "remove", str(tmp_path / "nope"), *args])
    assert res.exit_code == 1
    assert f"Sources autorisées\u00a0: {data.resolve()}" in res.output
    assert list_sources(cfg) == [str(data.resolve())]


def test_cli_sources_messages_follow_language(tmp_path: Path) -> None:
    # Consent messages follow `language`: French by default, English when configured.
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    data = tmp_path / "data"
    data.mkdir()
    args = ["--config-dir", str(cfg)]
    res = runner.invoke(app, ["sources", "add", str(data), *args])
    assert f"Source ajoutée\u00a0: {data.resolve()}" in res.output
    res = runner.invoke(app, ["sources", "add", str(tmp_path / "x"), *args])
    assert res.exit_code == 1
    assert "le chemin n'existe pas" in res.output
    res = runner.invoke(app, ["sources", "add", "postgresql://u:secret@h/db", *args])
    assert res.exit_code == 1
    assert "ne mettez pas de mot de passe" in res.output and "${DB_PASSWORD}" in res.output
    assert "Source retirée" in runner.invoke(app, ["sources", "remove", str(data), *args]).output

    (cfg / "default.yaml").write_text("language: en\n", encoding="utf-8")
    assert "No authorized sources." in runner.invoke(app, ["sources", "list", *args]).output
    res = runner.invoke(app, ["sources", "add", str(data), *args])
    assert f"Source added: {data.resolve()}" in res.output
    res = runner.invoke(app, ["sources", "remove", str(tmp_path / "nope"), *args])
    assert res.exit_code == 1
    assert f"Error: source not listed: {tmp_path / 'nope'}. Authorized sources: {data.resolve()}" in res.output
    res = runner.invoke(app, ["sources", "add", str(tmp_path / "x"), *args])
    assert "Error: path does not exist" in res.output
    assert "Source removed" in runner.invoke(app, ["sources", "remove", str(data), *args]).output


def test_cli_sources_add_refuses_path_inside_authorized_folder(tmp_path: Path) -> None:
    # A file (or sub-folder) of an authorized folder is not added a second time.
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    data = tmp_path / "data"
    (data / "sub").mkdir(parents=True)
    (data / "sales.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    args = ["--config-dir", str(cfg)]
    runner.invoke(app, ["sources", "add", str(data), *args])
    for inner in (data / "sales.csv", data / "sub"):
        res = runner.invoke(app, ["sources", "add", str(inner), *args])
        assert res.exit_code == 0, res.output
        expected = f"Déjà autorisé par le dossier {data.resolve()}\u00a0: {inner.resolve()} n'a pas été ajouté."
        assert expected in res.output
    assert list_sources(cfg) == [str(data.resolve())]
    (cfg / "default.yaml").write_text("language: en\n", encoding="utf-8")
    res = runner.invoke(app, ["sources", "add", str(data / "sales.csv"), *args])
    assert f"Already authorized by the folder {data.resolve()}" in res.output
    # The folder itself and a sibling folder are still handled as before.
    assert "Source added" in runner.invoke(app, ["sources", "add", str(data), *args]).output
    other = tmp_path / "data2"
    other.mkdir()
    assert "Source added" in runner.invoke(app, ["sources", "add", str(other), *args]).output
    assert list_sources(cfg) == [str(data.resolve()), str(other.resolve())]


def test_covering_folder_ignores_urls_and_files() -> None:
    from mide.connectors.sources import covering_folder

    assert covering_folder("sqlite:///x.db", ["/tmp"]) is None
    assert covering_folder("/tmp/a/b.csv", ["sqlite:///x.db"]) is None
    assert covering_folder("/tmp", ["/tmp"]) is None
