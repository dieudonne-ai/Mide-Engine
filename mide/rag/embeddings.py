"""Embeddings: multilingual sentence-transformers wrapper, batching, and a fake for tests."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Sequence
from typing import Any, Protocol

from mide.config import Config
from mide.hardware.profiler import Profile

DEFAULT_BATCH_SIZE = 32

# Batch size per hardware profile (smaller batches on small machines).
BATCH_BY_PROFILE: dict[Profile, int] = {"tiny": 8, "small": 16, "medium": 32, "large": 64}


class EmbeddingError(Exception):
    """Raised when the embedding model cannot be loaded or used."""


class Embedder(Protocol):
    """Interface the RAG layer depends on."""

    dimension: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


def batched(items: Sequence[str], size: int) -> list[Sequence[str]]:
    """Split ``items`` into consecutive batches of at most ``size``."""
    if size <= 0:
        raise ValueError("batch size must be positive")
    return [items[i : i + size] for i in range(0, len(items), size)]


def embedding_model_for_profile(config: Config, profile: Profile) -> str:
    """Return the embedding model name configured for ``profile``."""
    spec = config.models.profiles.get(profile)
    if spec is None:
        raise EmbeddingError(f"No embedding model configured for profile '{profile}'.")
    return spec.embeddings


class SentenceTransformerEmbedder:
    """Wrapper around ``sentence-transformers`` (imported lazily, optional dependency)."""

    def __init__(
        self,
        model_name: str,
        batch_size: int = DEFAULT_BATCH_SIZE,
        loader: Callable[[str], Any] | None = None,
    ) -> None:
        if loader is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise EmbeddingError(
                    "sentence-transformers is not installed. Install it with "
                    "`pip install mide-engine[rag]`."
                ) from exc
            loader = SentenceTransformer
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = loader(model_name)
        self.dimension = int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in batched(list(texts), self.batch_size):
            encoded = self._model.encode(list(batch), normalize_embeddings=True)
            vectors.extend([float(x) for x in row] for row in encoded)
        return vectors


class FakeEmbedder:
    """Deterministic, offline embedder: hashes tokens into a normalised vector."""

    def __init__(self, dimension: int = 64) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self.dimension = dimension

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dimension
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]


def load_embedder(config: Config, profile: Profile) -> SentenceTransformerEmbedder:
    """Load the profile's embedding model with a batch size adapted to the hardware."""
    return SentenceTransformerEmbedder(
        embedding_model_for_profile(config, profile), batch_size=BATCH_BY_PROFILE[profile]
    )
