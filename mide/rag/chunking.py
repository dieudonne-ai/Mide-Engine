"""Document chunking and textual summaries of tables, ready for indexing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from mide.ingestion.profiling import profile_dataframe

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 100
MAX_SUMMARY_COLUMNS = 30
TOP_VALUES = 3


@dataclass
class Chunk:
    """A piece of text plus the metadata needed to cite its origin."""

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _validate(chunk_size: int, overlap: int) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")


def _split_spans(text: str, chunk_size: int, overlap: int) -> list[tuple[int, int]]:
    """Return (start, end) character spans, preferring to cut on whitespace."""
    spans: list[tuple[int, int]] = []
    n = len(text)
    start = 0
    while start < n:
        end = min(start + chunk_size, n)
        if end < n:
            cut = max(text.rfind("\n", start, end), text.rfind(" ", start, end))
            if cut > start + overlap:
                end = cut
        if text[start:end].strip():
            spans.append((start, end))
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return spans


def chunk_text(
    text: str,
    source: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    page: int | None = None,
) -> list[Chunk]:
    """Split ``text`` into overlapping chunks with source/page/line metadata."""
    _validate(chunk_size, overlap)
    chunks: list[Chunk] = []
    for index, (start, end) in enumerate(_split_spans(text, chunk_size, overlap)):
        piece = text[start:end]
        lead = len(piece) - len(piece.lstrip())
        line_start = text.count("\n", 0, start + lead) + 1
        line_end = text.count("\n", 0, start + len(piece.rstrip())) + 1
        meta: dict[str, Any] = {
            "source": source,
            "kind": "text",
            "chunk_index": index,
            "line_start": line_start,
            "line_end": line_end,
        }
        if page is not None:
            meta["page"] = page
        chunks.append(Chunk(text=piece.strip(), metadata=meta))
    return chunks


def chunk_pages(
    pages: list[str],
    source: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Chunk]:
    """Chunk a paginated document (1-based page numbers in metadata)."""
    chunks: list[Chunk] = []
    for number, content in enumerate(pages, start=1):
        chunks.extend(chunk_text(content, source, chunk_size, overlap, page=number))
    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = index
    return chunks


def _numeric_line(name: str, series: pd.Series) -> str:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return f"- {name} (numeric): no values"
    return (
        f"- {name} (numeric): min={values.min():.2f}, max={values.max():.2f}, "
        f"mean={values.mean():.2f}, median={values.median():.2f}, sum={values.sum():.2f}"
    )


def _date_line(name: str, series: pd.Series) -> str:
    parsed = pd.to_datetime(series, errors="coerce", format="mixed").dropna()
    if parsed.empty:
        return f"- {name} (date): no values"
    return f"- {name} (date): from {parsed.min().date()} to {parsed.max().date()}"


def _categorical_line(name: str, series: pd.Series) -> str:
    counts = series.dropna().astype(str).value_counts().head(TOP_VALUES)
    top = ", ".join(f"{k} ({v})" for k, v in counts.items())
    return f"- {name} (categorical, {series.nunique()} values): top {top}"


def summarize_table(df: pd.DataFrame, source: str, name: str | None = None) -> list[Chunk]:
    """Build indexable textual summaries (schema + statistics) of a table."""
    label = name or source
    profile = profile_dataframe(df)
    shown = profile.columns[:MAX_SUMMARY_COLUMNS]
    schema_lines = [
        f"Table {label}: {profile.rows} rows, {len(profile.columns)} columns.",
        "Columns: "
        + ", ".join(f"{c.name} ({c.kind}, {c.missing_pct}% missing)" for c in shown),
    ]
    if len(profile.columns) > len(shown):
        schema_lines.append(f"... and {len(profile.columns) - len(shown)} more columns.")
    base: dict[str, Any] = {"source": source, "table": label, "rows": profile.rows}
    chunks = [Chunk("\n".join(schema_lines), {**base, "kind": "table_schema"})]

    stat_lines: list[str] = []
    for col in shown:
        series = df[col.name]
        if col.kind == "numeric":
            stat_lines.append(_numeric_line(col.name, series))
        elif col.kind == "date":
            stat_lines.append(_date_line(col.name, series))
        elif col.kind in ("categorical", "boolean"):
            stat_lines.append(_categorical_line(col.name, series))
    if stat_lines:
        text = f"Statistics of table {label}:\n" + "\n".join(stat_lines)
        chunks.append(Chunk(text, {**base, "kind": "table_stats"}))
    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = index
    return chunks
