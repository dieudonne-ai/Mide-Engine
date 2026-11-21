"""Management of the authorized sources stored in ``sources.yaml``."""

from __future__ import annotations

from pathlib import Path

import yaml

from mide.config import DEFAULT_CONFIG_DIR, ConfigError, SourcesConfig, seed_default_config
from mide.connectors.base import is_url, normalize_source


class SourceCovered(Exception):
    """The path is already inside an authorized folder; nothing to add."""

    def __init__(self, path: str, folder: str) -> None:
        super().__init__(f"{path} is already covered by the authorized folder {folder}")
        self.path = path
        self.folder = folder


class EmptySource(ValueError):
    """The source is blank; it would otherwise resolve to the current folder."""

    def __init__(self) -> None:
        super().__init__("The source is empty: give a folder, a file or a SQL URL.")


def _clean_source(source: str) -> str:
    """Return ``source`` without stray surrounding spaces (copy-paste).

    The exact value wins when it names an existing path, so a real path that
    starts or ends with a space still works. A blank value raises ``EmptySource``:
    ``Path("")`` is the current folder, which the user never chose to authorize.
    """
    stripped = source.strip()
    if not stripped:
        raise EmptySource()
    if stripped == source or Path(source).expanduser().exists():
        return source
    return stripped


HEADER = "# Authorized data sources. Nothing outside this list is ever read.\n"


def _sources_file(config_dir: Path | None) -> Path:
    cdir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
    seed_default_config(cdir)
    return cdir / "sources.yaml"


def list_sources(config_dir: Path | None = None) -> list[str]:
    """Return the authorized sources."""
    path = _sources_file(config_dir)
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return SourcesConfig.model_validate(data).sources
    except Exception as exc:  # invalid yaml / schema
        raise ConfigError(
            f"Invalid sources file {path}: {exc}", "invalid_sources", path, str(exc)
        ) from exc


def _save(sources: list[str], config_dir: Path | None) -> None:
    path = _sources_file(config_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump({"sources": sources}, allow_unicode=True, sort_keys=False)
    path.write_text(HEADER + body, encoding="utf-8")


def add_source(source: str, config_dir: Path | None = None) -> str:
    """Authorize a path or SQL URL. Returns the stored (normalized) value."""
    source = _clean_source(source)
    if is_url(source):
        from urllib.parse import urlsplit

        if urlsplit(source).password:
            raise ValueError(
                "Do not put a password in the URL; use an environment variable "
                "(e.g. ${DB_PASSWORD})."
            )
        from mide.connectors.sql import sqlite_file

        db_file = sqlite_file(source)
        if db_file is not None and not db_file.is_file():
            raise FileNotFoundError(f"SQLite database does not exist: {db_file}")
    elif not Path(source).expanduser().exists():
        raise FileNotFoundError(f"Path does not exist: {source}")
    value = normalize_source(source)
    sources = list_sources(config_dir)
    folder = covering_folder(value, sources)
    if folder is not None:
        raise SourceCovered(value, folder)
    if value not in sources:
        sources.append(value)
        _save(sources, config_dir)
    return value


def remove_source(source: str, config_dir: Path | None = None) -> bool:
    """Revoke a source. Returns False if it was not listed.

    The exact value is tried first, then the value without surrounding spaces.
    A blank value never matches (it would resolve to the current folder).
    """
    if not source.strip():
        return False
    sources = list_sources(config_dir)
    candidates = (normalize_source(source), normalize_source(source.strip()))
    value = next((c for c in candidates if c in sources), None)
    if value is None:
        return False
    sources.remove(value)
    _save(sources, config_dir)
    return True


def source_missing(source: str) -> bool:
    """True if a folder/file source or a SQLite database file no longer exists on disk.

    Server databases (PostgreSQL, MySQL, SQL Server) are never reported missing here.
    """
    if is_url(source):
        from mide.connectors.sql import sqlite_file

        db_file = sqlite_file(source)
        return db_file is not None and not db_file.is_file()
    return not Path(source).expanduser().exists()


def source_owning(path: Path, sources: list[str]) -> str | None:
    """Return the authorized source that holds the existing file ``path``, if any.

    Used before MIDE writes a file, so it never overwrites the user's data
    (sources are read-only). SQL URLs hold no local file and are skipped.
    """
    target = Path(path).expanduser()
    if not target.exists():
        return None
    target = target.resolve()
    for src in sources:
        if is_url(src):
            continue
        root = Path(src).expanduser().resolve()
        if target == root or root in target.parents:
            return src
    return None


def covering_folder(value: str, sources: list[str]) -> str | None:
    """Return the authorized folder that already contains the path ``value``, if any.

    Adding such a path would make the same files appear (and be indexed) twice.
    SQL URLs and the path itself (an exact match) are never "covering".
    """
    if is_url(value):
        return None
    target = Path(value).expanduser().resolve()
    for src in sources:
        if is_url(src):
            continue
        root = Path(src).expanduser().resolve()
        if root in target.parents and root.is_dir():
            return src
    return None
