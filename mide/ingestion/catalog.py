"""Inventory of every dataset reachable through the authorized sources."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from mide.connectors.base import is_url
from mide.connectors.files import DocumentConnector
from mide.connectors.sql import SQLConnector
from mide.connectors.tabular import TabularConnector
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
            entries.append(CatalogEntry(source, item, "csv", error=str(exc)))
    return entries


def _sql_entries(source: str, authorized: list[str]) -> list[CatalogEntry]:
    conn = SQLConnector(source, authorized)
    entries: list[CatalogEntry] = []
    for table in conn.discover():
        meta = conn.metadata(table)
        profile = profile_dataframe(conn.sample(table, PROFILE_SAMPLE_ROWS))
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
            if is_url(source):
                entries.extend(_sql_entries(source, sources))
                continue
            if not Path(source).expanduser().exists():
                logger.warning("Source not found: %s", source)
                continue
            entries.extend(_tabular_entries(source, sources))
            entries.extend(_document_entries(source, sources))
        except Exception as exc:  # noqa: BLE001 - one bad source must not stop the scan
            logger.warning("Cannot scan source %s: %s", source, exc)
            entries.append(CatalogEntry(source, source, "error", error=str(exc)))
    return entries
