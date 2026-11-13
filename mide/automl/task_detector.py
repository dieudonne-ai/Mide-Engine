"""Detect the ML task (regression / classification / time series) for a target column."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from mide.ingestion.profiling import profile_dataframe

REGRESSION = "regression"
CLASSIFICATION = "classification"
TIMESERIES = "timeseries"

MAX_CLASSES = 20  # an integer target with more distinct values is a quantity, not a class
CLASS_RATIO = 0.05  # ... unless distinct values are rare relative to the row count
UNIQUE_DATE_RATIO = 0.8  # share of distinct dates above which rows look like a series


@dataclass(frozen=True)
class TaskInfo:
    """Result of task detection."""

    task: str
    target: str
    date_column: str | None
    reason: str


def _is_discrete(series: pd.Series) -> bool:
    """True if a column looks like class labels rather than a continuous measure."""
    non_null = series.dropna()
    if non_null.empty:
        return False
    if pd.api.types.is_bool_dtype(series) or not pd.api.types.is_numeric_dtype(series):
        return True
    n_unique = non_null.nunique()
    is_integer = bool((non_null == non_null.round()).all())
    if n_unique <= 2:
        return True
    return is_integer and n_unique <= MAX_CLASSES and n_unique / len(non_null) <= CLASS_RATIO


def _detect_date_column(df: pd.DataFrame, target: str) -> str | None:
    profile = profile_dataframe(df)
    candidates = [c for c in profile.date_columns if c != target]
    return candidates[0] if candidates else None


def _dates_look_like_series(df: pd.DataFrame, date_column: str) -> bool:
    dates = pd.to_datetime(df[date_column], errors="coerce", format="mixed").dropna()
    if len(dates) < 3:
        return False
    return dates.nunique() / len(dates) >= UNIQUE_DATE_RATIO


def detect_task(df: pd.DataFrame, target: str, date_column: str | None = None) -> TaskInfo:
    """Decide which kind of model fits `target` in `df`.

    - classification: non-numeric/boolean target, or few discrete values;
    - timeseries: numeric target with a date column (given, or detected) where rows are
      roughly one per period (aggregate transactional data by date first);
    - regression: any other numeric target.
    """
    if target not in df.columns:
        raise ValueError(f"Target column '{target}' not found. Columns: {list(df.columns)}")
    if date_column is not None and date_column not in df.columns:
        raise ValueError(f"Date column '{date_column}' not found.")
    series = df[target]
    if series.dropna().empty:
        raise ValueError(f"Target column '{target}' has no values.")
    if _is_discrete(series):
        return TaskInfo(CLASSIFICATION, target, None, "target has discrete values")
    explicit = date_column is not None
    date_col = date_column or _detect_date_column(df, target)
    if date_col is not None and (explicit or _dates_look_like_series(df, date_col)):
        return TaskInfo(TIMESERIES, target, date_col, f"numeric target indexed by '{date_col}'")
    return TaskInfo(REGRESSION, target, None, "continuous numeric target")
