"""Inventory of every dataset reachable through the authorized sources."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from mide.connectors.base import is_url
from mide.connectors.files import DocumentConnector
from mide.connectors.sources import source_missing
from mide.connectors.sql import SQLConnector
from mide.connectors.tabular import EXCEL_EXTENSIONS, TabularConnector, split_item
from mide.ingestion.profiling import DatasetProfile, profile_dataframe

logger = logging.getLogger("mide.ingestion.catalog")

PROFILE_SAMPLE_ROWS = 5000


@dataclass
class CatalogEntry:
    """One dataset (table, sheet, CSV) or document."""

    source: str
    item: str
    kind: str  # csv | excel | sql | document
    rows: int | None = None
    n_columns: int | None = None
    profile: DatasetProfile | None = None
    error: str | None = None


def _tabular_entries(source: str, authorized: list[str]) -> list[CatalogEntry]:
    conn = TabularConnector(source, authorized)
    entries: list[CatalogEntry] = []
    for item in conn.discover():
        try:
            meta = conn.metadata(item)
            profile = profile_dataframe(conn.read(item, nrows=PROFILE_SAMPLE_ROWS))
            entries.append(
                CatalogEntry(source, item, meta["type"], meta["rows"], len(meta["columns"]), profile)
            )
        except Exception as exc:  # noqa: BLE001 - unreadable file: report it, keep scanning
            logger.warning("Cannot profile %s: %s", item, exc)
            kind = "excel" if Path(split_item(item)[0]).suffix.lower() in EXCEL_EXTENSIONS else "csv"
            entries.append(CatalogEntry(source, item, kind, error=str(exc)))
    return entries


def _sql_entries(source: str, authorized: list[str]) -> list[CatalogEntry]:
    entries: list[CatalogEntry] = []
    with SQLConnector(source, authorized) as conn:
        for table in conn.discover():
            try:
                meta = conn.metadata(table)
                profile = profile_dataframe(conn.sample(table, PROFILE_SAMPLE_ROWS))
            except Exception as exc:  # noqa: BLE001 - e.g. no SELECT right: report, keep scanning
                logger.warning("Cannot profile table %s: %s", table, type(exc).__name__)
                entries.append(CatalogEntry(source, table, "sql", error=type(exc).__name__))
                continue
            entries.append(
                CatalogEntry(source, table, "sql", meta["rows"], len(meta["columns"]), profile)
            )
    return entries


def _document_entries(source: str, authorized: list[str]) -> list[CatalogEntry]:
    conn = DocumentConnector(source, authorized)
    return [CatalogEntry(source, item, "document") for item in conn.discover()]


def build_catalog(sources: list[str]) -> list[CatalogEntry]:
    """Inventory every authorized source. Nothing outside ``sources`` is touched."""
    entries: list[CatalogEntry] = []
    for source in sources:
        try:
            if source_missing(source):
                logger.debug("Source not found: %s", source)
                continue
            if is_url(source):
                entries.extend(_sql_entries(source, sources))
                continue
            entries.extend(_tabular_entries(source, sources))
            entries.extend(_document_entries(source, sources))
        except Exception as exc:  # noqa: BLE001 - one bad source must not stop the scan
            logger.warning("Cannot scan source %s: %s", source, exc)
            entries.append(CatalogEntry(source, source, "error", error=str(exc)))
    return _unique_entries(entries)


def _unique_entries(entries: list[CatalogEntry]) -> list[CatalogEntry]:
    """Drop files listed twice because two authorized sources overlap (folder + file inside).

    SQL tables are keyed by their source too: two databases may hold tables with the same name.
    """
    seen: set[tuple[str, str]] = set()
    unique: list[CatalogEntry] = []
    for entry in entries:
        key = (entry.source if entry.kind in ("sql", "error") else "", entry.item)
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)
    return unique
