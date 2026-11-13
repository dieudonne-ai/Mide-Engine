import math

import numpy as np
import pytest

from mide.config import Config, ModelsConfig
from mide.rag.embeddings import (
    BATCH_BY_PROFILE,
    EmbeddingError,
    FakeEmbedder,
    SentenceTransformerEmbedder,
    batched,
    embedding_model_for_profile,
)


def test_fake_dimension(fake_embedder):
    vecs = fake_embedder.embed(["hello world", "bonjour"])
    assert len(vecs) == 2
    assert all(len(v) == fake_embedder.dimension for v in vecs)


def test_fake_deterministic_and_normalised():
    a = FakeEmbedder(32).embed(["ventes du mois"])[0]
    b = FakeEmbedder(32).embed(["ventes du mois"])[0]
    assert a == b
    assert math.isclose(sum(x * x for x in a), 1.0, rel_tol=1e-9)


def test_fake_different_texts_differ(fake_embedder):
    a, b = fake_embedder.embed(["sales growth", "customer churn"])
    assert a != b


def test_fake_empty_text_is_zero_vector(fake_embedder):
    assert set(fake_embedder.embed([""])[0]) == {0.0}


def test_fake_invalid_dimension():
    with pytest.raises(ValueError):
        FakeEmbedder(0)


def test_batched():
    assert batched(["a", "b", "c"], 2) == [["a", "b"], ["c"]]
    assert batched([], 2) == []
    with pytest.raises(ValueError):
        batched(["a"], 0)


class _StubModel:
    def __init__(self):
        self.calls: list[int] = []

    def get_sentence_embedding_dimension(self):
        return 4

    def encode(self, texts, normalize_embeddings=True):
        self.calls.append(len(texts))
        return np.ones((len(texts), 4), dtype=np.float32)


def test_sentence_transformer_batches_and_dimension():
    stub = _StubModel()
    emb = SentenceTransformerEmbedder("any-model", batch_size=2, loader=lambda name: stub)
    out = emb.embed(["a", "b", "c", "d", "e"])
    assert emb.dimension == 4
    assert len(out) == 5 and all(len(v) == 4 for v in out)
    assert stub.calls == [2, 2, 1]


def test_missing_dependency_message(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "sentence_transformers":
            raise ImportError("nope")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(EmbeddingError, match="mide-engine\\[rag\\]"):
        SentenceTransformerEmbedder("m")


def test_model_selected_per_profile():
    from mide.config import load_config

    cfg = load_config(create_app_dir=False)
    assert "MiniLM" in embedding_model_for_profile(cfg, "tiny")
    assert "e5-large" in embedding_model_for_profile(cfg, "large")


def test_missing_profile_raises(tmp_path):
    cfg = Config(models=ModelsConfig(profiles={}), app_dir=tmp_path)
    with pytest.raises(EmbeddingError):
        embedding_model_for_profile(cfg, "tiny")


def test_batch_size_shrinks_on_small_profiles():
    assert BATCH_BY_PROFILE["tiny"] < BATCH_BY_PROFILE["large"]
