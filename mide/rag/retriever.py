"""Top-k retrieval with optional source filtering and citations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mide.rag.embeddings import Embedder
from mide.rag.store import SearchHit, VectorStore


@dataclass
class Passage:
    """A retrieved chunk numbered for citation."""

    number: int
    text: str
    metadata: dict[str, Any]
    distance: float

    @property
    def source(self) -> str:
        return str(self.metadata.get("source", "?"))

    @property
    def citation(self) -> str:
        """Human-readable origin: file name plus page / lines / table when known."""
        src = self.source
        label = src if src.startswith(("http", "sqlite", "postgres", "mysql", "mssql")) else Path(src).name
        meta = self.metadata
        if meta.get("table"):
            label += f" (table {meta['table']})"
        if meta.get("page"):
            label += f", page {meta['page']}"
        if meta.get("line_start") and not meta.get("table"):
            label += f", lines {meta['line_start']}-{meta.get('line_end', meta['line_start'])}"
        return label


class Retriever:
    """Embeds a question and returns the nearest indexed chunks."""

    def __init__(self, store: VectorStore, embedder: Embedder, k: int = 5) -> None:
        self._store = store
        self._embedder = embedder
        self._k = k

    def retrieve(self, question: str, k: int | None = None, source: str | None = None) -> list[Passage]:
        """Top-k passages, optionally restricted to one indexed item (``source``)."""
        embedding = self._embedder.embed([question])[0]
        hits: list[SearchHit] = self._store.query(embedding, k or self._k, source=source)
        return [
            Passage(i, h.text, h.metadata, h.distance) for i, h in enumerate(hits, start=1)
        ]
