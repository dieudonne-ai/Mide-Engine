"""Persistent local vector store (ChromaDB) living in ``~/.mide/index/``."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mide.rag.chunking import Chunk
from mide.rag.embeddings import Embedder

COLLECTION_NAME = "mide_chunks"


@dataclass
class SearchHit:
    """One retrieved chunk with its distance (lower = closer)."""

    text: str
    metadata: dict[str, Any]
    distance: float


def doc_id(item: str) -> str:
    """Stable short identifier of an indexed item (file, sheet or table)."""
    return hashlib.sha1(item.encode("utf-8")).hexdigest()[:16]


def _clean_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """Chroma only accepts scalar metadata values: drop ``None``, stringify the rest."""
    out: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        out[key] = value if isinstance(value, (str, int, float, bool)) else str(value)
    return out


class VectorStore:
    """Thin wrapper over a persistent ChromaDB collection (embeddings are supplied by us)."""

    def __init__(self, path: Path) -> None:
        import chromadb
        from chromadb.config import Settings

        Path(path).mkdir(parents=True, exist_ok=True)
        # Telemetry is disabled: nothing may leave the machine.
        self._client = chromadb.PersistentClient(
            path=str(path), settings=Settings(anonymized_telemetry=False)
        )
        self._collection = self._client.get_or_create_collection(
            COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )

    def count(self) -> int:
        return int(self._collection.count())

    def add_document(self, item: str, chunks: Sequence[Chunk], embedder: Embedder) -> int:
        """Replace everything indexed for ``item`` by ``chunks``; return the chunk count."""
        self.delete_document(item)
        if not chunks:
            return 0
        did = doc_id(item)
        metadatas = []
        for chunk in chunks:
            meta = dict(chunk.metadata)
            meta["item"] = item
            metadatas.append(_clean_metadata(meta))
        self._collection.add(
            ids=[f"{did}:{i}" for i in range(len(chunks))],
            documents=[c.text for c in chunks],
            embeddings=embedder.embed([c.text for c in chunks]),  # type: ignore[arg-type]
            metadatas=metadatas,  # type: ignore[arg-type]
        )
        return len(chunks)

    def delete_document(self, item: str) -> None:
        self._collection.delete(where={"item": item})

    def query(
        self, text: str, embedder: Embedder, k: int = 5, source: str | None = None
    ) -> list[SearchHit]:
        """Return the ``k`` closest chunks, optionally restricted to one source."""
        total = self.count()
        if total == 0:
            return []
        result = self._collection.query(
            query_embeddings=embedder.embed([text]),  # type: ignore[arg-type]
            n_results=min(k, total),
            where={"source": source} if source else None,
        )
        docs = result["documents"] or [[]]
        metas = result["metadatas"] or [[]]
        dists = result["distances"] or [[]]
        return [
            SearchHit(d, dict(m), float(dist))
            for d, m, dist in zip(docs[0], metas[0], dists[0], strict=True)
        ]
