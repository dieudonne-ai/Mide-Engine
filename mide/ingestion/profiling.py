"""Column profiling: types, missing values, date columns and target candidates."""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field

import pandas as pd

# Name fragments (EN + FR) that suggest a business measure worth predicting.
TARGET_KEYWORDS = (
    "sale", "vente", "amount", "montant", "revenue", "revenu", "turnover", "chiffre",
    "quantity", "quantite", "quantité", "qty", "qte", "price", "prix", "total", "profit",
    "cost", "cout", "coût", "conversion", "spend", "budget",
)  # fmt: skip
ID_PATTERN = re.compile(r"(^id$|_id$|^id_|identifier|^code$|_code$|uuid)", re.IGNORECASE)
DATE_PARSE_THRESHOLD = 0.9


@dataclass
class ColumnProfile:
    """Profile of a single column."""

    name: str
    kind: str  # numeric | date | boolean | categorical | text
    dtype: str
    missing_pct: float
    n_unique: int
    is_target_candidate: bool = False


@dataclass
class DatasetProfile:
    """Profile of a whole table."""

    rows: int
    columns: list[ColumnProfile] = field(default_factory=list)

    @property
    def date_columns(self) -> list[str]:
        return [c.name for c in self.columns if c.kind == "date"]

    @property
    def target_candidates(self) -> list[str]:
        return [c.name for c in self.columns if c.is_target_candidate]


def _looks_like_date(series: pd.Series) -> bool:
    """True if an object/string column is mostly parseable as dates."""
    values = series.dropna().astype(str)
    if values.empty:
        return False
    # Pure numbers (e.g. "1500") must never be read as dates.
    if values.str.fullmatch(r"-?\d+(\.\d+)?").mean() > 0.5:
        return False
    sample = values.head(200)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    return bool(parsed.notna().mean() >= DATE_PARSE_THRESHOLD)


def _column_kind(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if _looks_like_date(series):
        return "date"
    non_null = series.dropna()
    if non_null.empty:
        return "categorical"
    unique_ratio = non_null.nunique() / len(non_null)
    avg_len = non_null.astype(str).str.len().mean()
    if avg_len > 50 or (unique_ratio > 0.9 and len(non_null) > 20):
        return "text"
    return "categorical"


def _is_target_candidate(name: str, series: pd.Series, kind: str) -> bool:
    if kind != "numeric" or ID_PATTERN.search(name):
        return False
    if series.dropna().nunique() < 2:
        return False
    lowered = name.lower()
    return any(k in lowered for k in TARGET_KEYWORDS)


def profile_column(name: str, series: pd.Series) -> ColumnProfile:
    """Profile one column."""
    kind = _column_kind(series)
    missing = float(series.isna().mean() * 100) if len(series) else 0.0
    return ColumnProfile(
        name=str(name),
        kind=kind,
        dtype=str(series.dtype),
        missing_pct=round(missing, 2),
        n_unique=int(series.nunique(dropna=True)),
        is_target_candidate=_is_target_candidate(str(name), series, kind),
    )


def profile_dataframe(df: pd.DataFrame) -> DatasetProfile:
    """Profile every column of a DataFrame."""
    return DatasetProfile(
        rows=len(df), columns=[profile_column(str(c), df[c]) for c in df.columns]
    )
