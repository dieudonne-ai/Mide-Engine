"""Tests for the vector store and incremental indexing (FakeEmbedder only)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from mide.rag.chunking import Chunk
from mide.rag.indexer import index_sources
from mide.rag.store import VectorStore


@pytest.fixture
def workspace(tmp_path: Path):
    docs = tmp_path / "data"
    docs.mkdir()
    (docs / "notes.md").write_text("Meeting notes about the marketing budget.\n" * 5)
    (docs / "sales.csv").write_text("date,amount\n2024-01-01,10\n2024-01-02,20\n")
    store = VectorStore(tmp_path / "index")
    return docs, store, tmp_path / "index" / "manifest.json"


def test_store_add_query_and_filter(tmp_path, fake_embedder):
    store = VectorStore(tmp_path / "idx")
    store.add_document("a", [Chunk("sales forecast for march", {"source": "s1"})], fake_embedder)
    store.add_document("b", [Chunk("customer churn risk", {"source": "s2", "page": None})],
                       fake_embedder)
    assert store.count() == 2
    hits = store.query("sales forecast", fake_embedder, k=1)
    assert hits[0].metadata["source"] == "s1"
    only_s2 = store.query("sales forecast", fake_embedder, k=5, source="s2")
    assert [h.metadata["source"] for h in only_s2] == ["s2"]


def test_store_persists_and_replaces(tmp_path, fake_embedder):
    store = VectorStore(tmp_path / "idx")
    store.add_document("a", [Chunk("one", {}), Chunk("two", {})], fake_embedder)
    store.add_document("a", [Chunk("three", {})], fake_embedder)
    assert VectorStore(tmp_path / "idx").count() == 1


def test_reindex_without_change_adds_nothing(workspace, fake_embedder):
    docs, store, manifest = workspace
    first = index_sources([str(docs)], store, fake_embedder, manifest)
    assert first.new_chunks > 0 and not first.errors
    count = store.count()
    second = index_sources([str(docs)], store, fake_embedder, manifest)
    assert second.new_chunks == 0
    assert not second.indexed_items
    assert len(second.skipped_items) == 2
    assert store.count() == count


def test_modified_file_is_reindexed_only(workspace, fake_embedder):
    docs, store, manifest = workspace
    index_sources([str(docs)], store, fake_embedder, manifest)
    (docs / "notes.md").write_text("Completely different content about suppliers.")
    report = index_sources([str(docs)], store, fake_embedder, manifest)
    assert [Path(i).name for i in report.indexed_items] == ["notes.md"]
    assert len(report.skipped_items) == 1


def test_touched_but_identical_file_is_skipped(workspace, fake_embedder):
    docs, store, manifest = workspace
    index_sources([str(docs)], store, fake_embedder, manifest)
    path = docs / "notes.md"
    os.utime(path, (1, 1))
    report = index_sources([str(docs)], store, fake_embedder, manifest)
    assert report.new_chunks == 0


def test_deleted_file_leaves_index(workspace, fake_embedder):
    docs, store, manifest = workspace
    index_sources([str(docs)], store, fake_embedder, manifest)
    (docs / "notes.md").unlink()
    report = index_sources([str(docs)], store, fake_embedder, manifest)
    assert [Path(i).name for i in report.removed_items] == ["notes.md"]
    assert all("notes.md" not in h.metadata["item"]
               for h in store.query("budget", fake_embedder, k=10))


def test_revoked_source_is_purged(workspace, fake_embedder, tmp_path):
    docs, store, manifest = workspace
    other = tmp_path / "other"
    shutil.copytree(docs, other)
    index_sources([str(docs), str(other)], store, fake_embedder, manifest)
    report = index_sources([str(docs)], store, fake_embedder, manifest)
    assert report.removed_items
    assert all(h.metadata["source"] == str(docs)
               for h in store.query("notes", fake_embedder, k=20))


def test_unlisted_folder_is_never_read(workspace, fake_embedder, tmp_path):
    docs, store, manifest = workspace
    secret = tmp_path / "secret"
    secret.mkdir()
    (secret / "private.txt").write_text("do not read me")
    index_sources([str(docs)], store, fake_embedder, manifest)
    assert all("private" not in h.text for h in store.query("read me", fake_embedder, k=20))
