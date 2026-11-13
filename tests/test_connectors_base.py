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


def test_cli_sources_roundtrip(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg"
    data = tmp_path / "data"
    data.mkdir()
    args = ["--config-dir", str(cfg)]
    assert "No authorized" in runner.invoke(app, ["sources", "list", *args]).output
    res = runner.invoke(app, ["sources", "add", str(data), *args])
    assert res.exit_code == 0
    assert str(data.resolve()) in runner.invoke(app, ["sources", "list", *args]).output
    assert runner.invoke(app, ["sources", "remove", str(data), *args]).exit_code == 0
    assert runner.invoke(app, ["sources", "remove", str(data), *args]).exit_code == 1
    assert runner.invoke(app, ["sources", "add", str(tmp_path / "x"), *args]).exit_code == 1
