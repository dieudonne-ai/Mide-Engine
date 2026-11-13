"""Read-only connector for CSV and Excel files (all sheets)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pandas as pd

from mide.connectors.base import BaseConnector, ensure_authorized

CSV_EXTENSIONS = {".csv", ".tsv", ".txt"}
EXCEL_EXTENSIONS = {".xlsx", ".xlsm"}
SUPPORTED_EXTENSIONS = CSV_EXTENSIONS | EXCEL_EXTENSIONS
SEPARATORS = [",", ";", "\t", "|"]
SHEET_SEP = "::"
_SAMPLE_BYTES = 64 * 1024


def detect_encoding(path: Path) -> str:
    """Return ``utf-8-sig`` if the file decodes as UTF-8 (BOM-safe), else ``latin-1``."""
    raw = path.read_bytes()[:_SAMPLE_BYTES]
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        # A multibyte char cut at the sample boundary is not a real decoding error.
        if exc.start < len(raw) - 4:
            return "latin-1"
    return "utf-8-sig"


def detect_separator(path: Path, encoding: str) -> str:
    """Guess the CSV delimiter from the first lines of the file."""
    with path.open("r", encoding=encoding, errors="replace", newline="") as fh:
        lines = [fh.readline() for _ in range(10)]
    sample = "".join(line for line in lines if line)
    if not sample.strip():
        return ","
    try:
        return csv.Sniffer().sniff(sample, delimiters="".join(SEPARATORS)).delimiter
    except csv.Error:
        header = lines[0]
        return max(SEPARATORS, key=header.count)


def split_item(item: str) -> tuple[str, str | None]:
    """Split ``path`` or ``path::sheet`` into its parts."""
    path, sep, sheet = item.rpartition(SHEET_SEP)
    return (path, sheet) if sep else (item, None)


class TabularConnector(BaseConnector):
    """Reads CSV (separator/encoding auto-detected) and XLSX (every sheet)."""

    def _files(self) -> list[Path]:
        root = Path(self.source).expanduser().resolve()
        if root.is_file():
            files = [root]
        elif root.is_dir():
            files = sorted(p for p in root.rglob("*") if p.is_file())
        else:
            raise FileNotFoundError(f"Source not found: {self.source}")
        return [p for p in files if p.suffix.lower() in SUPPORTED_EXTENSIONS]

    def discover(self) -> list[str]:
        items: list[str] = []
        for path in self._files():
            if path.suffix.lower() in EXCEL_EXTENSIONS:
                with pd.ExcelFile(path, engine="openpyxl") as xls:
                    items.extend(f"{path}{SHEET_SEP}{name}" for name in xls.sheet_names)
            else:
                items.append(str(path))
        return items

    def read(self, item: str, nrows: int | None = None) -> pd.DataFrame:
        path_s, sheet = split_item(item)
        ensure_authorized(path_s, self.authorized_sources)
        path = Path(path_s).resolve()
        if path.suffix.lower() in EXCEL_EXTENSIONS:
            return pd.read_excel(
                path, sheet_name=sheet if sheet is not None else 0, nrows=nrows, engine="openpyxl"
            )
        encoding = detect_encoding(path)
        sep = "\t" if path.suffix.lower() == ".tsv" else detect_separator(path, encoding)
        return pd.read_csv(path, sep=sep, encoding=encoding, nrows=nrows)

    def metadata(self, item: str) -> dict[str, Any]:
        path_s, sheet = split_item(item)
        ensure_authorized(path_s, self.authorized_sources)
        path = Path(path_s).resolve()
        df = self.read(item)
        meta: dict[str, Any] = {
            "type": "excel" if path.suffix.lower() in EXCEL_EXTENSIONS else "csv",
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "rows": len(df),
            "columns": [str(c) for c in df.columns],
            "dtypes": {str(c): str(t) for c, t in df.dtypes.items()},
        }
        if sheet is not None:
            meta["sheet"] = sheet
        else:
            meta["encoding"] = detect_encoding(path)
            meta["separator"] = (
                "\t" if path.suffix.lower() == ".tsv" else detect_separator(path, meta["encoding"])
            )
        return meta
