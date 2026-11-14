"""Incremental indexing: only new or modified items are (re)embedded."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from mide.connectors.base import is_url
from mide.connectors.files import DocumentConnector
from mide.connectors.sql import SQLConnector
from mide.connectors.tabular import TabularConnector, split_item
from mide.rag.chunking import Chunk, chunk_text, summarize_table
from mide.rag.embeddings import Embedder
from mide.rag.store import VectorStore

logger = logging.getLogger("mide.rag.indexer")

MANIFEST_NAME = "manifest.json"
SQL_FINGERPRINT_ROWS = 1000


@dataclass
class IndexReport:
    """Outcome of one indexing run."""

    new_items: list[str] = field(default_factory=list)
    updated_items: list[str] = field(default_factory=list)
    unchanged_items: list[str] = field(default_factory=list)
    removed_items: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)
    new_chunks: int = 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_manifest(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Index manifest unreadable, everything will be reindexed.")
        return {}


def _save_manifest(path: Path, manifest: dict[str, dict]) -> None:
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _file_state(path: Path, previous: dict | None) -> dict:
    """Fingerprint a file; the hash is recomputed only if size or mtime changed."""
    stat = path.stat()
    state = {"mtime": stat.st_mtime_ns, "size": stat.st_size}
    if previous and previous.get("mtime") == state["mtime"] and previous.get("size") == state["size"]:
        state["hash"] = previous["hash"]
    else:
        state["hash"] = _sha256(path)
    return state


def _sql_hash(conn: SQLConnector, table: str) -> str:
    meta = conn.metadata(table)
    sample = conn.sample(table, SQL_FINGERPRINT_ROWS)
    payload = json.dumps([meta["columns"], meta["rows"]], default=str)
    payload += pd.util.hash_pandas_object(sample, index=False).to_numpy().tobytes().hex()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _embed_chunks(chunks: list[Chunk], embedder: Embedder) -> list[list[float]]:
    return embedder.embed([c.text for c in chunks]) if chunks else []


def index_sources(
    sources: list[str],
    index_dir: Path,
    embedder: Embedder,
    chunk_size: int = 800,
    overlap: int = 100,
    max_file_size_mb: float = 50,
) -> IndexReport:
    """Index the authorized ``sources``; unchanged items are skipped.

    Items that disappeared (or whose source was revoked) are removed from the index.
    """
    store = VectorStore(index_dir)
    manifest_path = index_dir / MANIFEST_NAME
    old = _load_manifest(manifest_path)
    new_manifest: dict[str, dict] = {}
    report = IndexReport()
    seen: set[str] = set()

    def process(item: str, state: dict, build) -> None:  # type: ignore[no-untyped-def]
        seen.add(item)
        previous = old.get(item)
        if previous and previous.get("hash") == state["hash"]:
            new_manifest[item] = state | {"chunks": previous.get("chunks", 0)}
            report.unchanged_items.append(item)
            return
        try:
            chunks: list[Chunk] = build()
            vectors = _embed_chunks(chunks, embedder)
        except Exception as exc:  # noqa: BLE001 - one bad item must not stop indexing
            logger.warning("Cannot index %s: %s", item, type(exc).__name__)
            report.errors[item] = str(exc)
            if previous:
                new_manifest[item] = previous
            return
        if previous:
            store.delete_item(item)
        store.add(item, chunks, vectors)
        new_manifest[item] = state | {"chunks": len(chunks)}
        (report.updated_items if previous else report.new_items).append(item)
        report.new_chunks += len(chunks)

    for source in sources:
        try:
            _scan_source(source, sources, old, process, chunk_size, overlap, max_file_size_mb)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cannot index source %s: %s", source, exc)
            report.errors[source] = str(exc)
            for item, state in old.items():  # keep what we could not re-check
                if state.get("source") == source:
                    seen.add(item)
                    new_manifest[item] = state

    for item in old:
        if item not in seen:
            store.delete_item(item)
            report.removed_items.append(item)
    _save_manifest(manifest_path, new_manifest)
    return report


def _scan_source(source, sources, old, process, chunk_size, overlap, max_mb) -> None:  # type: ignore[no-untyped-def]
    if is_url(source):
        conn = SQLConnector(source, sources)
        for table in conn.discover():
            item = f"{source}#{table}"
            state = {"hash": _sql_hash(conn, table), "source": source}
            process(item, state, lambda t=table: summarize_table(conn.read(t), source, t))
        return
    if not Path(source).expanduser().exists():
        logger.warning("Source not found: %s", source)
        return
    tab = TabularConnector(source, sources)
    for item in tab.discover():
        path = Path(split_item(item)[0])
        state = _file_state(path, old.get(item)) | {"source": source}
        process(item, state, lambda i=item: summarize_table(tab.read(i), i))
    docs = DocumentConnector(source, sources, max_file_size_mb=max_mb)
    for item in docs.discover():
        state = _file_state(Path(item), old.get(item)) | {"source": source}
        process(item, state, lambda i=item: chunk_text(docs.read(i), i, chunk_size, overlap))
