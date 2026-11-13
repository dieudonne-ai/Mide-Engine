import sqlite3
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from mide import cli
from mide.rag.chunking import Chunk
from mide.rag.indexer import index_sources
from mide.rag.store import VectorStore


def _make_source(tmp_path: Path) -> Path:
    src = tmp_path / "data"
    src.mkdir()
    (src / "notes.txt").write_text("Marketing meeting: increase radio budget in Goma. " * 40)
    (src / "report.md").write_text("# Report\nSales grew in Q3 thanks to the new product.")
    pd.DataFrame({"date": ["2024-01-01", "2024-01-02"], "amount": [10.0, 20.0]}).to_csv(
        src / "sales.csv", index=False
    )
    return src


def test_store_add_query_delete(tmp_path, fake_embedder):
    store = VectorStore(tmp_path / "idx")
    chunks = [Chunk("sales of coffee", {"source": "a"}), Chunk("weather report", {"source": "a"})]
    store.add("a", chunks, fake_embedder.embed([c.text for c in chunks]))
    assert store.count() == 2
    hits = store.query(fake_embedder.embed(["coffee sales"])[0], k=1)
    assert hits[0].text == "sales of coffee"
    assert hits[0].metadata["item"] == "a"
    assert store.query(fake_embedder.embed(["x"])[0], source="other") == []
    store.delete_item("a")
    assert store.count() == 0


def test_store_persists(tmp_path, fake_embedder):
    chunk = Chunk("hello world", {"source": "a"})
    VectorStore(tmp_path / "idx").add("a", [chunk], fake_embedder.embed(["hello world"]))
    assert VectorStore(tmp_path / "idx").count() == 1


def test_reindex_without_change_adds_nothing(tmp_path, fake_embedder):
    src = _make_source(tmp_path)
    idx = tmp_path / "idx"
    first = index_sources([str(src)], idx, fake_embedder)
    assert first.new_chunks > 0
    assert len(first.new_items) == 3
    total = VectorStore(idx).count()
    second = index_sources([str(src)], idx, fake_embedder)
    assert second.new_chunks == 0
    assert second.new_items == [] and second.updated_items == []
    assert len(second.unchanged_items) == 3
    assert VectorStore(idx).count() == total


def test_modified_file_is_reindexed_and_removed_file_pruned(tmp_path, fake_embedder):
    src = _make_source(tmp_path)
    idx = tmp_path / "idx"
    index_sources([str(src)], idx, fake_embedder)
    (src / "report.md").write_text("Completely different content about churn.")
    (src / "notes.txt").unlink()
    report = index_sources([str(src)], idx, fake_embedder)
    assert [Path(i).name for i in report.updated_items] == ["report.md"]
    assert [Path(i).name for i in report.removed_items] == ["notes.txt"]
    hits = VectorStore(idx).query(fake_embedder.embed(["churn"])[0], k=10)
    assert all("notes.txt" not in h.metadata["item"] for h in hits)
    assert any("different content" in h.text for h in hits)


def test_touched_file_with_same_content_is_unchanged(tmp_path, fake_embedder):
    src = _make_source(tmp_path)
    idx = tmp_path / "idx"
    index_sources([str(src)], idx, fake_embedder)
    path = src / "report.md"
    path.write_text(path.read_text())  # new mtime, same content
    report = index_sources([str(src)], idx, fake_embedder)
    assert report.new_chunks == 0 and not report.updated_items


def test_revoked_source_is_removed_from_index(tmp_path, fake_embedder):
    src = _make_source(tmp_path)
    idx = tmp_path / "idx"
    index_sources([str(src)], idx, fake_embedder)
    report = index_sources([], idx, fake_embedder)
    assert len(report.removed_items) == 3
    assert VectorStore(idx).count() == 0


def test_sql_source_indexed(tmp_path, fake_embedder):
    db = tmp_path / "shop.db"
    con = sqlite3.connect(db)
    con.execute("create table orders (id integer, amount real)")
    con.executemany("insert into orders values (?, ?)", [(1, 5.0), (2, 7.5)])
    con.commit()
    con.close()
    url = f"sqlite:///{db}"
    idx = tmp_path / "idx"
    assert index_sources([url], idx, fake_embedder).new_chunks > 0
    assert index_sources([url], idx, fake_embedder).new_chunks == 0


def test_embedding_failure_is_reported_not_raised(tmp_path):
    class Broken:
        def embed(self, texts):
            raise RuntimeError("boom")

    src = _make_source(tmp_path)
    report = index_sources([str(src)], tmp_path / "idx", Broken())
    assert len(report.errors) == 3 and report.new_chunks == 0


def test_cli_index(tmp_path, monkeypatch, fake_embedder):
    src = _make_source(tmp_path)
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(cli, "_get_embedder", lambda cfg: fake_embedder)
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    (cfg_dir / "sources.yaml").write_text(f"sources:\n  - {src}\n")
    runner = CliRunner()
    first = runner.invoke(cli.app, ["index", "--config-dir", str(cfg_dir)])
    assert first.exit_code == 0, first.output
    assert "3 new" in first.output
    second = runner.invoke(cli.app, ["index", "--config-dir", str(cfg_dir)])
    assert "0 new" in second.output and "0 new chunks" in second.output
