"""Read-only connector for SQL databases (SQLite, PostgreSQL, MySQL, SQL Server)."""

from __future__ import annotations

import os
import re
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Self

import pandas as pd
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine, make_url

from mide.connectors.base import BaseConnector

_ENV_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|replace|merge|grant|revoke|"
    r"attach|detach|pragma|vacuum|call|exec|execute|copy|into)\b",
    re.IGNORECASE,
)


class WriteQueryBlockedError(PermissionError):
    """Raised when a statement could modify the database."""


def expand_env(url: str) -> str:
    """Replace ``${VAR}`` with the environment variable value (credentials stay out of config)."""

    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in os.environ:
            raise KeyError(f"Environment variable not set: {name}")
        return os.environ[name]

    return _ENV_VAR.sub(repl, url)


def sqlite_file(url: str) -> Path | None:
    """Return the database file of a SQLite URL, or ``None`` (other dialect, memory, URI mode).

    The URL is parsed without expanding environment variables, so ``${VAR}`` stays as is.
    """
    try:
        parsed = make_url(url)
    except Exception:  # noqa: BLE001 - not a valid SQLAlchemy URL
        return None
    if parsed.get_backend_name() != "sqlite":
        return None
    database = parsed.database or ""
    if database in ("", ":memory:") or parsed.query.get("uri") or database.startswith("file:"):
        return None
    return Path(database).expanduser()


def _strip_comments_and_strings(sql: str) -> str:
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"'(?:[^']|'')*'", "''", sql)


def ensure_read_only(sql: str) -> None:
    """Raise :class:`WriteQueryBlockedError` unless ``sql`` is a single SELECT/WITH query."""
    cleaned = _strip_comments_and_strings(sql).strip().rstrip(";").strip()
    if ";" in cleaned:
        raise WriteQueryBlockedError("Multiple statements are not allowed.")
    if not re.match(r"(select|with)\b", cleaned, re.IGNORECASE):
        raise WriteQueryBlockedError("Only SELECT queries are allowed (read-only).")
    if _FORBIDDEN.search(cleaned):
        raise WriteQueryBlockedError("Write or administrative statements are blocked.")


def _quote(engine: Engine, name: str) -> str:
    return engine.dialect.identifier_preparer.quote(name)


class SQLConnector(BaseConnector):
    """Reads tables of an authorized database URL. Never writes."""

    def __init__(self, source: str, authorized_sources: list[str]) -> None:
        super().__init__(source, authorized_sources)
        self._engine: Engine | None = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            url = expand_env(self.source)
            db_file = sqlite_file(url)
            if db_file is not None:
                # Open the file read-only: a missing database raises instead of being
                # created as an empty file (sources are never written, CLAUDE.md §2.3).
                if not db_file.is_file():
                    raise FileNotFoundError(f"SQLite database not found: {db_file}")
                uri = f"{db_file.resolve().as_uri()}?mode=ro"
                engine = create_engine(
                    "sqlite://",
                    creator=lambda: sqlite3.connect(uri, uri=True, check_same_thread=False),
                )
            else:
                engine = create_engine(url)
            if engine.dialect.name == "sqlite":

                @event.listens_for(engine, "connect")
                def _read_only(dbapi_conn: Any, _rec: Any) -> None:
                    dbapi_conn.execute("PRAGMA query_only = ON")

            self._engine = engine
        return self._engine

    def close(self) -> None:
        """Release every pooled database connection (safe to call twice)."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def discover(self) -> list[str]:
        return sorted(inspect(self.engine).get_table_names())

    def _check_table(self, table: str) -> None:
        if table not in self.discover():
            raise KeyError(f"Unknown table: {table}")

    def query(self, sql: str, nrows: int | None = None) -> pd.DataFrame:
        """Run a read-only SELECT and return a DataFrame."""
        ensure_read_only(sql)
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchmany(nrows) if nrows is not None else result.fetchall()
            return pd.DataFrame(rows, columns=list(result.keys()))

    def read(self, item: str, nrows: int | None = None) -> pd.DataFrame:
        self._check_table(item)
        return self.query(f"SELECT * FROM {_quote(self.engine, item)}", nrows)

    def sample(self, item: str, n: int = 100) -> pd.DataFrame:
        """Return the first ``n`` rows of a table."""
        return self.read(item, nrows=n)

    def read_chunks(self, item: str, chunksize: int = 10_000) -> Iterator[pd.DataFrame]:
        """Yield the table in chunks of ``chunksize`` rows (bounded memory)."""
        self._check_table(item)
        sql = f"SELECT * FROM {_quote(self.engine, item)}"
        ensure_read_only(sql)
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            cols = list(result.keys())
            while True:
                rows = result.fetchmany(chunksize)
                if not rows:
                    break
                yield pd.DataFrame(rows, columns=cols)

    def metadata(self, item: str) -> dict[str, Any]:
        self._check_table(item)
        columns = inspect(self.engine).get_columns(item)
        with self.engine.connect() as conn:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {_quote(self.engine, item)}")).scalar()
        return {
            "type": "sql",
            "dialect": self.engine.dialect.name,
            "table": item,
            "rows": int(count or 0),
            "columns": [c["name"] for c in columns],
            "dtypes": {c["name"]: str(c["type"]) for c in columns},
        }
