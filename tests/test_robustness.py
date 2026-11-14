"""Tests for W4-04: robustness (clear errors) and performance (chunked reading, memory)."""

from __future__ import annotations

import pandas as pd
import pandas.errors as pde
import pytest

from mide.connectors.tabular import TabularConnector
from mide.ingestion.catalog import build_catalog
from mide.utils.errors import classify, friendly_message, run_safely
from mide.utils.perf import measure


@pytest.mark.parametrize(
    ("exc", "key"),
    [
        (FileNotFoundError("x"), "not_found"),
        (PermissionError("x"), "permission"),
        (UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad"), "encoding"),
        (pde.EmptyDataError("x"), "empty"),
        (pde.ParserError("x"), "parse"),
        (MemoryError(), "memory"),
        (ConnectionError("x"), "network"),
        (RuntimeError("boom"), "unknown"),
    ],
)
def test_classify(exc, key):
    assert classify(exc) == key


def test_messages_are_bilingual():
    exc = FileNotFoundError("data.csv")
    assert "introuvable" in friendly_message(exc, "fr")
    assert "not found" in friendly_message(exc, "en")
    assert "introuvable" in friendly_message(exc, "zz")  # falls back to French


def test_run_safely_reports_clean_error(capsys):
    def boom() -> None:
        raise MemoryError

    assert run_safely(boom, "en") == 1
    assert "Not enough memory" in capsys.readouterr().err
    assert run_safely(lambda: None) == 0


def test_run_safely_lets_exit_through():
    def leave() -> None:
        raise SystemExit(2)

    with pytest.raises(SystemExit):
        run_safely(leave)


def _big_csv(tmp_path, rows: int = 120_000):
    path = tmp_path / "big.csv"
    pd.DataFrame({"id": range(rows), "amount": [1.5] * rows, "label": ["a"] * rows}).to_csv(
        path, index=False
    )
    return path


def test_read_chunks_covers_all_rows(tmp_path):
    path = _big_csv(tmp_path, 25_000)
    conn = TabularConnector(str(path), [str(path)])
    chunks = list(conn.read_chunks(str(path), chunksize=10_000))
    assert [len(c) for c in chunks] == [10_000, 10_000, 5_000]


def test_metadata_counts_rows_in_chunks(tmp_path):
    path = _big_csv(tmp_path)
    conn = TabularConnector(str(path), [str(path)])
    meta = conn.metadata(str(path))
    assert meta["rows"] == 120_000
    assert meta["columns"] == ["id", "amount", "label"]


def test_chunked_metadata_uses_less_memory_than_full_read(tmp_path):
    path = _big_csv(tmp_path)
    conn = TabularConnector(str(path), [str(path)])
    chunked = measure(lambda: conn.metadata(str(path)))
    full = measure(lambda: conn.read(str(path)))
    assert chunked.peak_mb < full.peak_mb


def test_demo_dataset_processed_within_memory_budget(demo_data):
    root = str(next(iter(demo_data.values())).parent)
    result = measure(lambda: build_catalog([root]))
    assert len(result.result) > 0
    assert result.peak_mb < 4096  # CLAUDE.md budget for the tiny profile (without LLM)
    assert result.peak_mb < 500  # in practice far below
