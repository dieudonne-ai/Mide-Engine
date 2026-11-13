"""Persistent vector store (ChromaDB) living in ``~/.mide/index/``."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from mide.rag.chunking import Chunk

COLLECTION_NAME = "mide_chunks"


@dataclass
class SearchHit:
    """One retrieved chunk with its distance (lower is closer)."""

    text: str
    metadata: dict[str, Any]
    distance: float


def item_key(item: str) -> str:
    """Stable short key of an indexed item (used in chunk ids)."""
    return hashlib.sha1(item.encode("utf-8")).hexdigest()[:16]


class VectorStore:
    """Thin wrapper around a persistent Chroma collection. Telemetry is disabled."""

    def __init__(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(path), settings=Settings(anonymized_telemetry=False)
        )
        self._collection = self._client.get_or_create_collection(
            COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )

    def count(self) -> int:
        return int(self._collection.count())

    def add(self, item: str, chunks: Sequence[Chunk], embeddings: Sequence[Sequence[float]]) -> None:
        """Store the chunks of one item (``item`` is recorded in the metadata)."""
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        if not chunks:
            return
        key = item_key(item)
        self._collection.add(
            ids=[f"{key}:{i}" for i in range(len(chunks))],
            documents=[c.text for c in chunks],
            embeddings=[list(e) for e in embeddings],
            metadatas=[{**c.metadata, "item": item} for c in chunks],
        )

    def delete_item(self, item: str) -> None:
        """Remove every chunk of an item."""
        self._collection.delete(where={"item": item})

    def query(
        self, embedding: Sequence[float], k: int = 5, source: str | None = None
    ) -> list[SearchHit]:
        """Return the ``k`` nearest chunks, optionally restricted to one item."""
        total = self.count()
        if total == 0:
            return []
        result = self._collection.query(
            query_embeddings=[list(embedding)],
            n_results=min(k, total),
            where={"item": source} if source else None,
        )
        docs = (result["documents"] or [[]])[0]
        metas = (result["metadatas"] or [[]])[0]
        dists = (result["distances"] or [[]])[0]
        return [
            SearchHit(text=d, metadata=dict(m or {}), distance=float(x))
            for d, m, x in zip(docs, metas, dists, strict=True)
        ]
