"""Tests for the read-only SQL connector."""

import sqlite3
from pathlib import Path

import pytest

from mide.connectors.base import SourceNotAuthorizedError
from mide.connectors.sql import SQLConnector, WriteQueryBlockedError, expand_env


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    path = tmp_path / "shop.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE ventes (id INTEGER, produit TEXT, montant REAL)")
    con.executemany(
        "INSERT INTO ventes VALUES (?, ?, ?)", [(i, f"p{i % 3}", i * 1.5) for i in range(25)]
    )
    con.execute("CREATE TABLE clients (id INTEGER, nom TEXT)")
    con.execute("INSERT INTO clients VALUES (1, 'Awa')")
    con.commit()
    con.close()
    return f"sqlite:///{path}"


def test_discover_and_metadata(db_url: str) -> None:
    c = SQLConnector(db_url, [db_url])
    assert c.discover() == ["clients", "ventes"]
    meta = c.metadata("ventes")
    assert meta["rows"] == 25 and meta["columns"] == ["id", "produit", "montant"]
    assert meta["dialect"] == "sqlite"


def test_read_sample_and_chunks(db_url: str) -> None:
    c = SQLConnector(db_url, [db_url])
    assert len(c.read("ventes")) == 25
    assert len(c.sample("ventes", 5)) == 5
    sizes = [len(ch) for ch in c.read_chunks("ventes", chunksize=10)]
    assert sizes == [10, 10, 5]


def test_unauthorized_url_refused(db_url: str) -> None:
    with pytest.raises(SourceNotAuthorizedError):
        SQLConnector(db_url, ["sqlite:///other.db"])


def test_unknown_table_refused(db_url: str) -> None:
    with pytest.raises(KeyError):
        SQLConnector(db_url, [db_url]).read("nope; DROP TABLE ventes")


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM ventes",
        "UPDATE ventes SET montant = 0",
        "INSERT INTO clients VALUES (2, 'x')",
        "DROP TABLE ventes",
        "SELECT * FROM ventes; DROP TABLE ventes",
        "WITH x AS (SELECT 1) DELETE FROM ventes",
        "PRAGMA writable_schema = 1",
        "CREATE TABLE t AS SELECT 1",
    ],
)
def test_write_queries_blocked(db_url: str, sql: str) -> None:
    c = SQLConnector(db_url, [db_url])
    with pytest.raises(WriteQueryBlockedError):
        c.query(sql)
    assert len(c.read("ventes")) == 25


def test_select_allowed_and_string_literals_ignored(db_url: str) -> None:
    c = SQLConnector(db_url, [db_url])
    df = c.query("SELECT 'delete me' AS x, COUNT(*) AS n FROM ventes -- drop")
    assert df["n"][0] == 25


def test_database_itself_read_only(db_url: str) -> None:
    from sqlalchemy import text

    c = SQLConnector(db_url, [db_url])
    with pytest.raises(Exception, match="readonly|read-only"), c.engine.begin() as conn:
        conn.execute(text("DELETE FROM ventes"))


def test_credentials_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_PASS", "s3cret")
    assert expand_env("postgresql://u:${DB_PASS}@h/db") == "postgresql://u:s3cret@h/db"
    monkeypatch.delenv("DB_PASS")
    with pytest.raises(KeyError):
        expand_env("postgresql://u:${DB_PASS}@h/db")
