from itertools import pairwise

import pandas as pd
import pytest

from mide.config import GeneralConfig
from mide.rag.chunking import chunk_pages, chunk_text, summarize_table

LONG = "\n".join(f"Line {i}: the quick brown fox jumps over the lazy dog." for i in range(1, 41))


def test_chunk_lengths_and_overlap() -> None:
    chunks = chunk_text(LONG, "notes.txt", chunk_size=200, overlap=40)
    assert len(chunks) > 3
    assert all(len(c.text) <= 200 for c in chunks)
    for a, b in pairwise(chunks):
        assert a.text[-15:] in b.text or b.text[:15] in a.text


def test_chunk_metadata_source_and_lines() -> None:
    chunks = chunk_text(LONG, "notes.txt", chunk_size=200, overlap=40)
    assert [c.metadata["chunk_index"] for c in chunks] == list(range(len(chunks)))
    assert all(c.metadata["source"] == "notes.txt" for c in chunks)
    assert chunks[0].metadata["line_start"] == 1
    assert chunks[-1].metadata["line_end"] == 40
    for c in chunks:
        assert c.metadata["line_start"] <= c.metadata["line_end"]


def test_all_text_is_covered() -> None:
    chunks = chunk_text(LONG, "n.txt", chunk_size=150, overlap=30)
    for i in range(1, 41):
        assert any(f"Line {i}:" in c.text for c in chunks)


def test_short_and_empty_text() -> None:
    assert chunk_text("", "e.txt") == []
    assert chunk_text("   \n ", "e.txt") == []
    only = chunk_text("hello", "h.txt")
    assert len(only) == 1 and only[0].text == "hello"


def test_invalid_parameters() -> None:
    with pytest.raises(ValueError):
        chunk_text("abc", "x", chunk_size=0)
    with pytest.raises(ValueError):
        chunk_text("abc", "x", chunk_size=10, overlap=10)


def test_chunk_pages_keeps_page_numbers() -> None:
    chunks = chunk_pages(["page one text", LONG], "doc.pdf", chunk_size=200, overlap=20)
    assert chunks[0].metadata["page"] == 1
    assert {c.metadata["page"] for c in chunks} == {1, 2}
    assert [c.metadata["chunk_index"] for c in chunks] == list(range(len(chunks)))


def test_config_defaults() -> None:
    cfg = GeneralConfig()
    assert cfg.chunk_size == 800 and cfg.chunk_overlap == 100


def test_summarize_table_on_demo_data(demo_data) -> None:
    df = pd.read_csv(demo_data["sales"])
    chunks = summarize_table(df, source=str(demo_data["sales"]), name="sales")
    kinds = [c.metadata["kind"] for c in chunks]
    assert kinds == ["table_schema", "table_stats"]
    assert f"{len(df)} rows" in chunks[0].text
    for column in df.columns:
        assert column in chunks[0].text
    assert "mean=" in chunks[1].text and "from " in chunks[1].text
    assert all(c.metadata["source"] == str(demo_data["sales"]) for c in chunks)


def test_summarize_table_is_deterministic() -> None:
    df = pd.DataFrame({"montant": [1.0, 2.0, 3.0], "canal": ["a", "b", "a"]})
    first = summarize_table(df, "t.csv")
    second = summarize_table(df, "t.csv")
    assert [c.text for c in first] == [c.text for c in second]
    assert "a (2)" in first[1].text
