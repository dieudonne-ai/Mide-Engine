"""Incremental indexing: only new or modified items are (re)embedded.

Only authorized sources are read (see ``mide.connectors``). Change detection uses
size + modification time first, then a content hash to avoid needless re-embedding.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from mide.connectors.base import is_url
from mide.connectors.files import DocumentConnector, DocumentReadError
from mide.connectors.sql import SQLConnector
from mide.connectors.tabular import TabularConnector, split_item
from mide.rag.chunking import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    Chunk,
    chunk_text,
    summarize_table,
)
from mide.rag.embeddings import Embedder
from mide.rag.store import VectorStore

logger = logging.getLogger("mide.rag.indexer")

MANIFEST_NAME = "manifest.json"


@dataclass
class IndexReport:
    """What an indexing run did."""

    new_chunks: int = 0
    indexed_items: list[str] = field(default_factory=list)
    skipped_items: list[str] = field(default_factory=list)
    removed_items: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class Manifest:
    """JSON record of what is indexed: ``item -> {source, size, mtime, hash}``."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.entries: dict[str, dict[str, object]] = {}
        if path.exists():
            try:
                self.entries = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                logger.warning("Corrupted index manifest, everything will be re-indexed")

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.entries, indent=1), encoding="utf-8")


def _fingerprint(item: str, previous: dict[str, object] | None) -> dict[str, object]:
    """Return ``{size, mtime, hash}`` for a file-backed item (hash reused if unchanged)."""
    path = Path(split_item(item)[0])
    stat = path.stat()
    size, mtime = stat.st_size, stat.st_mtime_ns
    if previous and previous.get("size") == size and previous.get("mtime") == mtime:
        return dict(previous)
    return {"size": size, "mtime": mtime, "hash": _file_hash(path)}


def _is_unchanged(old: dict[str, object] | None, new: dict[str, object]) -> bool:
    return bool(old) and old is not None and old.get("hash") == new.get("hash")


def _table_label(item: str) -> str:
    path, sheet = split_item(item)
    return Path(path).name + (f"::{sheet}" if sheet else "")


def _doc_chunks(conn: DocumentConnector, item: str, size: int, overlap: int) -> list[Chunk]:
    return chunk_text(conn.read(item), source=item, chunk_size=size, overlap=overlap)


def index_sources(
    sources: list[str],
    store: VectorStore,
    embedder: Embedder,
    manifest_path: Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    max_file_size_mb: float = 50,
) -> IndexReport:
    """Index every authorized source, skipping items whose content did not change."""
    manifest = Manifest(manifest_path)
    report = IndexReport()
    seen: set[str] = set()

    def process(item: str, source: str, fingerprint: dict[str, object], build) -> None:
        seen.add(item)
        old = manifest.entries.get(item)
        if _is_unchanged(old, fingerprint) and old is not None:
            manifest.entries[item] = {**fingerprint, "source": source}
            report.skipped_items.append(item)
            return
        try:
            chunks = build()
            for chunk in chunks:
                chunk.metadata["source"] = source
            report.new_chunks += store.add_document(item, chunks, embedder)
        except Exception as exc:  # noqa: BLE001 - one bad item must not stop indexing
            logger.warning("Cannot index %s: %s", item, exc)
            report.errors[item] = str(exc)
            return
        manifest.entries[item] = {**fingerprint, "source": source}
        report.indexed_items.append(item)

    for source in sources:
        try:
            if is_url(source):
                sql = SQLConnector(source, sources)
                for table in sql.discover():
                    meta = sql.metadata(table)
                    digest = hashlib.sha256(
                        json.dumps([meta["rows"], meta["columns"]], default=str).encode()
                    ).hexdigest()
                    item = f"{source}#{table}"
                    process(item, source, {"hash": digest},
                            lambda c=sql, t=table, i=item: summarize_table(c.read(t), i, t))
                continue
            if not Path(source).expanduser().exists():
                logger.warning("Source not found: %s", source)
                continue
            tab = TabularConnector(source, sources)
            for item in tab.discover():
                fp = _fingerprint(item, manifest.entries.get(item))
                process(item, source, fp,
                        lambda c=tab, i=item: summarize_table(c.read(i), i, _table_label(i)))
            docs = DocumentConnector(source, sources, max_file_size_mb=max_file_size_mb)
            for item in docs.discover():
                fp = _fingerprint(item, manifest.entries.get(item))
                process(item, source, fp,
                        lambda c=docs, i=item: _doc_chunks(c, i, chunk_size, chunk_overlap))
        except (DocumentReadError, OSError) as exc:
            logger.warning("Cannot index source %s: %s", source, exc)
            report.errors[source] = str(exc)

    # Drop items that vanished from a scanned source, and everything from revoked
    # sources (consent withdrawn). Sources that failed to scan this time are kept.
    scanned = {s for s in sources if s not in report.errors}
    for item in [i for i in manifest.entries if i not in seen]:
        origin = manifest.entries[item].get("source")
        if origin in scanned or origin not in sources:
            store.delete_document(item)
            del manifest.entries[item]
            report.removed_items.append(item)
    manifest.save()
    return report
